"""Pasta de dados fora do repositório (pesos, datasets brutos, gerações).

Definida por MODEL_GATE_DATA; padrão ~/model_gate_data. Nada dela entra no git (T-211).
"""

import os
from pathlib import Path


def data_dir() -> Path:
    d = Path(os.environ.get("MODEL_GATE_DATA", Path.home() / "model_gate_data")).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    return d
