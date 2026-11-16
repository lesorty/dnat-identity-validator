#!/usr/bin/env bash
# Importa um pacote da campanha (make pacote, na VM) para resultados_nuvem/<pacote>/ no repositório,
# onde a aba Resultados da interface o mostra como "nuvem", ao lado das verificações locais.
#
#   tools/cloud/importar.sh campanha_tst_<host>_<commit>_<data>.tar.gz
#
# Recusa pacote já importado e pacote sem pacote.json. Avisa se o commit da campanha não estava
# congelado (ensaio, não dado do artigo) ou se não existe neste repositório.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PKG="${1:?uso: tools/cloud/importar.sh PACOTE.tar.gz}"
[ -f "$PKG" ] || { echo "não encontrado: $PKG" >&2; exit 1; }
# A lista é lida uma vez: com pipefail, `tar | grep -q` falha por SIGPIPE quando o grep acha cedo.
list="$(tar -tzf "$PKG")"
name="$(printf '%s\n' "$list" | sed -n 1p | cut -d/ -f1)"
[[ "$name" == campanha_* ]] || { echo "não parece um pacote da campanha: $name" >&2; exit 1; }
printf '%s\n' "$list" | grep -x "$name/pacote.json" >/dev/null || { echo "pacote sem pacote.json" >&2; exit 1; }
# nada de caminho absoluto, subindo diretório ou fora da pasta do pacote
if printf '%s\n' "$list" | grep -E '^/|(^|/)\.\.(/|$)' >/dev/null || printf '%s\n' "$list" | grep -v "^$name/" | grep . >/dev/null; then
  echo "pacote com caminho inseguro" >&2; exit 1
fi
# só arquivos e pastas: link simbólico ou físico no pacote poderia apontar para fora
if tar -tvzf "$PKG" | cut -c1 | grep -v '^[-d]$' >/dev/null; then echo "pacote com link ou arquivo especial" >&2; exit 1; fi
dest="$REPO/resultados_nuvem/$name"
[ -e "$dest" ] && { echo "já importado: $dest" >&2; exit 1; }
mkdir -p "$REPO/resultados_nuvem"
tar -xzf "$PKG" -C "$REPO/resultados_nuvem" --no-same-owner --no-same-permissions
python3 -I - "$dest" <<'EOF'
import json, subprocess, sys
from pathlib import Path
d = Path(sys.argv[1])
m = json.loads((d / "pacote.json").read_text())
commit = m["head"]["commit"]
known = subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=d.parents[1]).returncode == 0
n = sum(1 for _ in d.glob("results/*/*.json"))
print(f"importado: {d}")
print(f"  host {m['host']} · commit {commit[:12]} · {n} resultados · {'congelado' if m['congelado'] else 'ENSAIO (commit não congelado)'}")
if not known:
    print("  aviso: o commit da campanha não existe neste repositório (git fetch --tags?)")
EOF
