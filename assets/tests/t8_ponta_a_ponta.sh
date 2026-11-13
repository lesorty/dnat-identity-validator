#!/usr/bin/env bash
# Teste 8 (ponta a ponta no DNAT, T-813): derivado reprovado fica retido, o dono não o reativa, o
# operador revoga o outro e a cota acerta, com o Juiz real como segundo job.
#
# Local (T-814): roda no modo direto, sem Docker nem root, sobre smart-contract/e2e/stack.js, com o
# Qwen2.5-0.5B de $MODEL_GATE_DATA, o pacote da bateria local e a referência do pai medida pelo
# experiments.judge_local (avaliador e prereg de FUMAÇA). Na nuvem (T-813), o mesmo roteiro roda com
# o avaliador, a bateria e o prereg da liberação real.
#
# Pré-requisitos: npm ci em smart-contract/, uv sync em model_gate/, e
#   (cd model_gate && uv run python -m experiments.battery_pack --out ~/model_gate_data/battery/local_t807 \
#      --n-harmful 24 --n-safe 10 --n-pairs-train 32 --n-pairs-val 16 --n-utility 16)
#   (cd model_gate && uv run python -m experiments.judge_local)   # mede a referência do pai
# Uso: bash assets/tests/t8_ponta_a_ponta.sh [--base-dir DIR] [--reference-dir DIR] [--keep]
# Resultados: smart-contract/results/T-814_teste8_local.{json,md}

set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO/smart-contract"
exec node e2e/teste8.js "$@"
