"""Leitor das condições de geração do S1 (T-306): configs.yaml vira GenConfig."""

from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import yaml

from model_gate.io.generate import GenConfig

CONFIGS_PATH = Path(__file__).with_name("configs.yaml")
FIXED_CONDITIONS = ("vazio", "padrao")


@lru_cache(maxsize=1)
def load_configs(path: Path = CONFIGS_PATH) -> dict:
    return yaml.safe_load(path.read_text())


def gen_config(condition: str, configs: dict | None = None) -> GenConfig:
    """GenConfig de uma condição fixa (vazio ou padrao), com os parâmetros de geração do arquivo."""
    c = configs or load_configs()
    if condition not in FIXED_CONDITIONS:
        raise ValueError(f"condição fixa desconhecida: {condition} (C_job sai do dataset do job)")
    g = c["geracao"]
    if g["decodificacao"] != "gulosa" or g["dtype"] != "float32":
        raise ValueError("o gerador da T-205 só faz decodificação gulosa em float32")
    return replace(GenConfig(), system_prompt=c["condicoes"][condition]["system_prompt"],
                   max_new_tokens=g["max_new_tokens"], batch_size=g["lote"], threads=g["threads"], seed=g["seed"])
