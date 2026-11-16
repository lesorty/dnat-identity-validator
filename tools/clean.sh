#!/usr/bin/env bash
# Limpeza do que as pilhas descartáveis e os testes deixam para trás.
#
#   tools/clean.sh               temporários /tmp/dnat-* com mais de 1 h, containers de CVM de job
#                                órfãos e processos de pilhas e2e com mais de 1 h (nada disso é
#                                apagado se a pilha de desenvolvimento estiver no ar)
#   tools/clean.sh --executions  também apaga, de smart-contract/executions, os arquivos que as
#                                execuções antigas guardavam em claro (dataset, base, bundle, ext4,
#                                workspace); metadata.json e result.json ficam
#   tools/clean.sh --dry-run     só mostra o que faria
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY=0; EXEC=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --executions) EXEC=1 ;;
    *) echo "opção desconhecida: $a" >&2; exit 2 ;;
  esac
done
do_() { if [ "$DRY" = 1 ]; then echo "  (faria) $*"; else "$@"; fi; }

if [ -f "$REPO/smart-contract/.dev_stack.json" ]; then
  echo "pilha de desenvolvimento no ar: temporários, containers e processos ficam como estão"
else
  n=$(find /tmp -maxdepth 1 -name 'dnat-*' -mmin +60 2>/dev/null | wc -l)
  echo "temporários /tmp/dnat-* com mais de 1 h: $n"
  find /tmp -maxdepth 1 -name 'dnat-*' -mmin +60 -print0 2>/dev/null | while IFS= read -r -d '' p; do do_ rm -rf "$p"; done

  if command -v docker >/dev/null && docker info >/dev/null 2>&1; then
    ids=$(docker ps -aq --filter label=dnat.role=job-vm)
    echo "containers de CVM de job órfãos: $(echo "$ids" | grep -c . || true)"
    [ -n "$ids" ] && do_ docker rm -f $ids >/dev/null
  fi

  # Nós do Hardhat e CVM1 de pilhas e2e (127.0.0.1, fora do Docker) com mais de 1 h.
  for pat in "hardhat node --hostname 127.0.0.1" "smart-contract/scripts/api-server.js"; do
    for pid in $(pgrep -f "$pat" || true); do
      age=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' ')
      [ -n "$age" ] && [ "$age" -gt 3600 ] && { echo "processo antigo de pilha e2e: $pid ($pat)"; do_ kill "$pid"; }
    done
  done
fi

if [ "$EXEC" = 1 ]; then
  n=0; bytes=0
  for d in "$REPO"/smart-contract/executions/*/; do
    for f in bundle.tar.gz dataset.csv application.ext4 workspace; do
      if [ -e "$d$f" ]; then
        bytes=$((bytes + $(du -sb "$d$f" | cut -f1))); n=$((n + 1)); do_ rm -rf "$d$f"
      fi
    done
  done
  echo "arquivos em claro de execuções antigas: $n ($((bytes / 1048576)) MB)"
fi
