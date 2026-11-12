"""Pares nocivo/inócuo da direção de recusa (T-401), separados do S1 e da bateria de referência.

Fonte: os splits de Arditi et al. (2024), baixados por experiments.fetch_datasets
("refusal_direction"). Nocivos de AdvBench, MaliciousInstruct, TDC2023 e HarmBench;
inócuos do Alpaca. Como no método original, 128 pares de treino (a direção) e 32 de
validação (a escolha da camada e a medida do S2), sorteados com seed fixa.

Exclusões, pelo hash do texto normalizado (model_gate.battery.pool.prompt_hash):
- tudo o que está no acervo do S1 (StrongREJECT, que tem 25 itens do AdvBench) e no XSTest
  inteiro (S1 e bateria de referência), para o sinal não ver os itens do veredito (R12);
- repetidos dentro do split e itens da validação que já estão no treino.

O arquivo versionado (direction_pairs.json) guarda só índice e hash: o texto nocivo
não entra no git (T-211).
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from model_gate.battery.pool import XSTEST_PATH, load_pool, prompt_hash

PAIRS_PATH = Path(__file__).with_name("direction_pairs.json")
SPLITS = ("harmful_train", "harmless_train", "harmful_val", "harmless_val")
SIZES = {"train": 128, "val": 32}
SEED = 401


class PairsMismatch(RuntimeError):
    """O texto local não bate com o hash versionado do par."""


def excluded_hashes() -> set[str]:
    """Hashes do acervo do S1 e do XSTest inteiro."""
    return {it["sha256"] for it in load_pool()["items"]} | {it["sha256"] for it in load_pool(XSTEST_PATH)["items"]}


def build_pairs(texts: dict[str, list[str]], exclude: set[str], seed: int = SEED,
                sizes: dict[str, int] = SIZES) -> dict:
    """Sorteia os pares. texts: split -> instruções na ordem do arquivo (o índice é a posição)."""
    out = {"seed": seed, "sizes": dict(sizes), "splits": {}, "excluded": {}}
    seen: dict[str, set[str]] = {"harmful": set(), "harmless": set()}
    for split in SPLITS:  # treino antes da validação, para a validação não repetir o treino
        kind, part = split.split("_")
        pool, skip, local = [], 0, set()
        for i, t in enumerate(texts[split]):
            h = prompt_hash(t)
            if h in exclude or h in seen[kind] or h in local:
                skip += 1
                continue
            local.add(h)
            pool.append((i, h))
        n = sizes[part]
        if len(pool) < n:
            raise ValueError(f"{split}: só {len(pool)} itens depois das exclusões, preciso de {n}")
        pick = sorted(random.Random(f"{seed}/{split}").sample(pool, n))
        seen[kind] |= {h for _, h in pick}
        out["splits"][split] = [{"idx": i, "sha256": h} for i, h in pick]
        out["excluded"][split] = skip
    return out


def pair_texts(pairs: dict, texts: dict[str, list[str]]) -> dict[str, list[str]]:
    """Textos dos pares, conferidos contra o hash versionado."""
    out = {}
    for split, items in pairs["splits"].items():
        rows = []
        for it in items:
            t = texts[split][it["idx"]]
            if prompt_hash(t) != it["sha256"]:
                raise PairsMismatch(f"{split}[{it['idx']}]: texto não bate com o hash versionado")
            rows.append(t)
        out[split] = rows
    return out


def read_splits(root: Path) -> dict[str, list[str]]:
    """Instruções dos quatro splits baixados (dataset/splits/<split>.json)."""
    return {s: [r["instruction"] for r in json.loads((root / "dataset" / "splits" / f"{s}.json").read_text())]
            for s in SPLITS}


def load_pairs(path: Path = PAIRS_PATH) -> dict:
    return json.loads(path.read_text())
