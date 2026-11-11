"""Textos dos pedidos do S1, lidos dos CSVs fixados e conferidos contra os hashes do acervo.

O git guarda só IDs e hashes (T-211). O Juiz recebe os CSVs e confere cada pedido contra o hash
do harmful_ids.json e do xstest_ids.json: um CSV diferente do fixado é recusado.
"""

from __future__ import annotations

import csv
from pathlib import Path

from model_gate.battery.pool import POOL_PATH, XSTEST_PATH, load_pool, prompt_hash


class BatteryMismatch(RuntimeError):
    """Um pedido do CSV não bate com o hash do acervo."""


def _check(items: dict[int, dict], texts: dict[int, str]) -> dict[int, str]:
    bad = [i for i, t in texts.items() if prompt_hash(t) != items[i]["sha256"]]
    if bad or set(texts) != set(items):
        raise BatteryMismatch(f"{len(bad)} pedidos com hash diferente; {len(set(items) - set(texts))} faltando")
    return texts


def harmful_texts(csv_path: Path, pool_path: Path = POOL_PATH) -> dict[int, str]:
    """ID (linha do CSV do StrongREJECT) → pedido."""
    items = {it["id"]: it for it in load_pool(pool_path)["items"]}
    with open(csv_path, newline="", encoding="utf-8") as f:
        texts = {i: r["forbidden_prompt"] for i, r in enumerate(csv.DictReader(f))}
    return _check(items, texts)


def safe_texts(csv_path: Path, uso: str = "s1", pool_path: Path = XSTEST_PATH) -> dict[int, str]:
    """ID do XSTest → pedido seguro, só do uso pedido ("s1" ou "referencia")."""
    items = {it["id"]: it for it in load_pool(pool_path)["items"] if it["uso"] == uso}
    with open(csv_path, newline="", encoding="utf-8") as f:
        texts = {int(r["id"]): r["prompt"] for r in csv.DictReader(f) if int(r["id"]) in items}
    return _check(items, texts)
