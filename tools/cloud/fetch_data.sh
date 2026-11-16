#!/usr/bin/env bash
# Baixa os dados do model_gate e confere cada um pelo manifesto versionado no repositório. Os pesos
# e os textos ficam em $MODEL_GATE_DATA (padrão ~/model_gate_data), fora do git (T-211).
#
#   tools/cloud/fetch_data.sh [--judges] [--population]
#
#   padrão        base Qwen2.5-0.5B (T-203) e datasets StrongREJECT e XSTest (T-204)
#   --judges      avaliadores do portão: Qwen3Guard-Gen-4B e Gemma (T-105, T-309)
#   --population  dados da população: benignos (T-902), nocivos (T-904) e os que degradam (T-903)
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO/model_gate"
JUDGES=0; POP=0
for a in "$@"; do
  case "$a" in
    --judges) JUDGES=1 ;;
    --population) POP=1 ;;
    *) echo "opção desconhecida: $a" >&2; exit 2 ;;
  esac
done
run() { echo "+ $*"; uv run --frozen python -m "$@"; }

run experiments.fetch_base --check
run experiments.fetch_datasets --check
[ "$JUDGES" = 1 ] && run experiments.fetch_judges --check
if [ "$POP" = 1 ]; then
  # benign e degrading não têm --check: regravam o manifesto, que tem de sair igual ao versionado.
  run experiments.population.benign
  run experiments.population.degrading
  git -C "$REPO" diff --exit-code -- model_gate/data/benign.manifest.json model_gate/data/degrading.manifest.json \
    || { echo "os dados da população não batem com os manifestos versionados" >&2; exit 1; }
  run experiments.population.harmful --check
fi
echo "dados conferidos em ${MODEL_GATE_DATA:-$HOME/model_gate_data}"
