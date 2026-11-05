#!/usr/bin/env bash
# Cria o ambiente do model_gate do zero a partir do uv.lock (T-202).
# Mesmas versões no piloto, nas máquinas da campanha e na CVM de job.
# Requisito: uv (https://docs.astral.sh/uv/). O uv baixa o Python 3.12 se faltar.
set -euo pipefail
cd "$(dirname "$0")"

command -v uv >/dev/null || { echo "uv não encontrado; instale antes." >&2; exit 1; }

# --frozen: usa o lock como está e falha se o pyproject divergir dele.
uv sync --frozen "$@"

uv run --frozen python -c "import torch, transformers, peft, model_gate; \
print('torch', torch.__version__, '| transformers', transformers.__version__, '| peft', peft.__version__)"
