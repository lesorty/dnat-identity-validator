#!/bin/bash
# =============================================================================
# M0 — Runner de execucao DIRETA (sem microVM). Baseline "sem isolamento".
#
# Executa EXATAMENTE o mesmo contrato workspace/run.sh que run-vm.sh, porem
# diretamente no namespace do container: sem Firecracker, sem discos isolados,
# sem remocao de rede. Serve para (1) medir o custo do microVM (boot ~= 0,
# latencia ~= tempo de computo da app) e (2) expor o que o isolamento contem
# (rede alcancavel, env/segredos do host visiveis, filesystem persistente).
#
# Saida: o MESMO JSON {returncode, stdout, stderr} que run-vm.sh imprime no
# stdout, para que executor.py faca json.loads identico.
# =============================================================================
set -uo pipefail

BUNDLE_PATH="${1:-}"
[ -f "$BUNDLE_PATH" ] || { echo '{"error": "Bundle not found"}'; exit 1; }

# O run.sh gerado pelo control plane faz `cd /tmp/exec/workspace`; espelhamos o
# mesmo layout que o guest usa em /tmp/exec para rodar o run.sh sem nenhuma
# alteracao (fairness com o caminho do microVM).
EXEC_DIR="/tmp/exec"
APP_SYMLINK="/mnt/dnat-app"
TIMEOUT_SECONDS="${VM_TIMEOUT_SECONDS:-660}"

APP_MOUNT=""
cleanup() {
    if [ -n "$APP_MOUNT" ] && mountpoint -q "$APP_MOUNT" 2>/dev/null; then
        umount "$APP_MOUNT" 2>/dev/null || true
        rmdir "$APP_MOUNT" 2>/dev/null || true
    fi
}
trap cleanup EXIT

rm -rf "$EXEC_DIR"
mkdir -p "$EXEC_DIR"
if ! tar -xzf "$BUNDLE_PATH" -C "$EXEC_DIR" 2>/tmp/m0-tar.err; then
    echo "{\"error\": \"failed to extract bundle\", \"detail\": $(python3 -c 'import json; print(json.dumps(open("/tmp/m0-tar.err").read()))')}"
    exit 1
fi
[ -d "$EXEC_DIR/workspace" ] || { echo '{"error": "workspace missing from execution bundle"}'; exit 1; }

# Artefato opcional da aplicacao: espelha o /mnt/dnat-app read-only do microVM
# para bundles construidos pelo builder (no modo script nao ha artifacts/).
if [ -f "$EXEC_DIR/artifacts/application.ext4" ]; then
    APP_MOUNT="$(mktemp -d)"
    if mount -o loop,ro "$EXEC_DIR/artifacts/application.ext4" "$APP_MOUNT" 2>/dev/null; then
        rm -f "$APP_SYMLINK" 2>/dev/null || true
        ln -s "$APP_MOUNT" "$APP_SYMLINK" 2>/dev/null || true
    else
        rmdir "$APP_MOUNT" 2>/dev/null || true
        APP_MOUNT=""
    fi
fi

STDOUT_FILE="$(mktemp)"
STDERR_FILE="$(mktemp)"

# Sem isolamento: a aplicacao herda rede, variaveis de ambiente e filesystem do
# container. O `timeout` espelha o teto de tempo do ciclo do microVM.
timeout "$TIMEOUT_SECONDS" bash "$EXEC_DIR/workspace/run.sh" >"$STDOUT_FILE" 2>"$STDERR_FILE"
RC=$?

python3 - "$RC" "$STDOUT_FILE" "$STDERR_FILE" <<'PY'
import json, sys
rc = int(sys.argv[1])
stdout = open(sys.argv[2], encoding="utf-8", errors="ignore").read()
stderr = open(sys.argv[3], encoding="utf-8", errors="ignore").read()
print(json.dumps({"returncode": rc, "stdout": stdout, "stderr": stderr}))
PY

rm -f "$STDOUT_FILE" "$STDERR_FILE"
