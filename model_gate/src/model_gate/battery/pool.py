"""Acervo público de nocivos do S1 (T-302): IDs, categoria, origem e hash do texto, sem o texto.

O acervo são os 313 itens do StrongREJECT no commit fixado (T-204). O ID é a linha do CSV
(0-based). O hash do texto normalizado permite conferir sobreposição com a bateria de
referência (T-1001) e com o conjunto da direção do S2 (T-401) sem guardar o texto no git.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

POOL_PATH = Path(__file__).with_name("harmful_ids.json")
XSTEST_PATH = Path(__file__).with_name("xstest_ids.json")


def normalize_prompt(text: str) -> str:
    """NFKC, minúsculas e espaços colapsados: o mesmo pedido com outra formatação bate."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).lower()).strip()


def prompt_hash(text: str) -> str:
    return hashlib.sha256(normalize_prompt(text).encode()).hexdigest()


def load_pool(path: Path = POOL_PATH) -> dict:
    return json.loads(path.read_text())


def by_category(item_ids, pool: dict | None = None) -> dict[str, list[int]]:
    """Agrupa IDs do acervo por categoria (entrada do sorteio das âncoras)."""
    cat = {it["id"]: it["category"] for it in (pool or load_pool())["items"]}
    out: dict[str, list[int]] = defaultdict(list)
    for i in item_ids:
        out[cat[i]].append(i)
    return dict(out)


def overlap(pool: dict, other_hashes) -> list[int]:
    """IDs do acervo cujo texto normalizado aparece em outro conjunto (dado pelos hashes)."""
    other = set(other_hashes)
    return [it["id"] for it in pool["items"] if it["sha256"] in other]


def safe_by_type(xstest: dict | None = None, uso: str = "s1") -> dict[str, list[int]]:
    """Seguros do XSTest de um uso ("s1" ou "referencia"), agrupados por tipo (T-303)."""
    x = xstest or load_pool(XSTEST_PATH)
    out: dict[str, list[int]] = defaultdict(list)
    for it in x["items"]:
        if it["uso"] == uso:
            out[it["type"]].append(it["id"])
    return dict(out)

