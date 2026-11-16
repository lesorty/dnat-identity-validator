#!/usr/bin/env bash
# Fecha o sistema para a fase de testes (T-1611): marca o commit atual com uma tag anotada
# `congelado-AAAAMMDD-HHMM` que registra o hash do Juiz, o do prereg e os dos locks. Daqui em diante,
# mudar o Juiz obriga a repetir a calibração (TS2). Só a campanha num commit congelado conta como
# dado do artigo (tools/cloud/campanha.py).
#
#   tools/congelar.sh [--ensaio] [--sem-testes]
#
#   --ensaio      aceita o prereg com valores nulos (T-606 pendente) e cria `ensaio-congelado-*`,
#                 que a campanha NÃO aceita como congelado; serve para ensaiar o processo
#   --sem-testes  não roda `make test` antes (não recomendado)
#
# Não faz push: o comando para publicar a tag é impresso no fim.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
ENSAIO=0; TESTES=1
for a in "$@"; do
  case "$a" in
    --ensaio) ENSAIO=1 ;;
    --sem-testes) TESTES=0 ;;
    *) echo "opção desconhecida: $a" >&2; exit 2 ;;
  esac
done

[ -z "$(git status --porcelain)" ] || { echo "o repositório tem mudanças: commit antes de congelar" >&2; git status --short >&2; exit 1; }

prereg_ok=1
(cd model_gate && uv run --frozen --quiet python -c "
from pathlib import Path
from model_gate.stages import load_prereg
load_prereg(Path('prereg.yaml'))" >/dev/null 2>&1) || prereg_ok=0
if [ "$prereg_ok" = 0 ] && [ "$ENSAIO" = 0 ]; then
  echo "o prereg.yaml ainda tem valores nulos (T-606): congelar agora não serve à campanha; use --ensaio para ensaiar" >&2
  exit 1
fi

[ "$TESTES" = 1 ] && make test

judge=$(cd model_gate && uv run --frozen --quiet python -c "from model_gate.judge_package import judge_hash; print(judge_hash()[0])")
prereg=$(sha256sum model_gate/prereg.yaml | cut -d' ' -f1)
uvlock=$(sha256sum model_gate/uv.lock | cut -d' ' -f1)
npmlock=$(sha256sum smart-contract/package-lock.json | cut -d' ' -f1)
contract=$(sha256sum smart-contract/contracts/DnatMarketplace.sol | cut -d' ' -f1)
prefix=$([ "$ENSAIO" = 1 ] && echo "ensaio-congelado" || echo "congelado")
tag="$prefix-$(date +%Y%m%d-%H%M)"
git tag -a "$tag" -F - <<EOF
Sistema fechado para a fase de testes (T-1611)$([ "$ENSAIO" = 1 ] && echo " — ENSAIO, prereg sem valores")

juiz: $judge
prereg.yaml: $prereg$([ "$prereg_ok" = 0 ] && echo " (com valores nulos)")
uv.lock: $uvlock
package-lock.json: $npmlock
DnatMarketplace.sol: $contract
EOF
echo "tag $tag em $(git rev-parse --short HEAD) · Juiz ${judge:0:12} · prereg ${prereg:0:12}"
echo "para publicar: git push origin $tag"
