#!/usr/bin/env bash
# Semeia a pilha Docker (docker/direct.compose.yaml) como operador: deposita o pacote da bateria e
# libera o Juiz atual da imagem com o prereg e o avaliador de FUMAÇA. Sem isso, todo job na pilha
# termina sem veredito (judge_not_allowed). A referência do pai depende do id do base depositado:
#   tools/stack_seed.sh [--reference ID_DO_BASE]
# usa a referência da T-807 em $MODEL_GATE_DATA/references (montada só leitura em /data/model_gate_data).
set -euo pipefail
C=dnat-client
J="node smart-contract/scripts/judge_cli.js"
docker exec "$C" true 2>/dev/null || { echo "container $C parado: make stack-up" >&2; exit 1; }
commit=$(printf '%s' "T-304 pendente" | sha256sum | cut -d' ' -f1)
docker exec "$C" $J battery --dir /data/model_gate_data/battery/local_t807 --source "stack-seed"
docker exec "$C" $J allow --battery-commitment "$commit" --prereg model_gate/experiments/judge_local_prereg.yaml \
  --evaluator-kind detector --note "stack-seed: fumaça"
if [ "${1:-}" = "--reference" ] && [ -n "${2:-}" ]; then
  ref=$(docker exec "$C" sh -c 'ls -d /data/model_gate_data/references/t807_detector_* | head -1')
  docker exec "$C" $J reference --parent "$2" --dir "$ref" --source "stack-seed: $(basename "$ref")"
fi
docker exec "$C" $J show
