"""Grava o acervo do XSTest para o S1 e a verdade de referência (T-303).

Divide os 250 seguros, de forma fixa, em 15 por tipo para o S1 (150) e 10 por tipo para a
bateria de referência (100, T-1001), que precisa de itens que o Juiz nunca vê (R12). Os 200
contrastes inseguros ficam fora do veredito (T-301) e livres para a referência. Sai
src/model_gate/battery/xstest_ids.json com ID, tipo, rótulo, uso e hash do texto normalizado.

    uv run python -m experiments.build_xstest_pool
"""

from __future__ import annotations

import csv
import json
import random
import sys
from collections import Counter, defaultdict

from experiments.fetch_datasets import DATASETS
from experiments.fetch_datasets import local_root as dataset_root
from model_gate.battery.pool import XSTEST_PATH, prompt_hash

SPLIT_SEED = 303
S1_PER_TYPE = 15


def main() -> int:
    spec = DATASETS["xstest"]
    manifest = json.loads((XSTEST_PATH.parents[3] / "data" / "datasets.manifest.json").read_text())["xstest"]
    with open(dataset_root("xstest", spec) / "xstest_prompts.csv", newline="", encoding="utf-8") as f:
        rows = sorted(csv.DictReader(f), key=lambda r: int(r["id"]))
    safe = defaultdict(list)
    for r in rows:
        if r["label"] == "safe":
            safe[r["type"]].append(int(r["id"]))
    rng = random.Random(SPLIT_SEED)
    s1 = set()
    for t in sorted(safe):
        ids = sorted(safe[t]); rng.shuffle(ids); s1 |= set(ids[:S1_PER_TYPE])
    items = []
    for r in rows:
        i = int(r["id"])
        uso = ("s1" if i in s1 else "referencia") if r["label"] == "safe" else "contraste"
        items.append({"id": i, "type": r["type"], "label": r["label"], "uso": uso, "sha256": prompt_hash(r["prompt"])})
    XSTEST_PATH.write_text(json.dumps({
        "dataset": "xstest", "commit": spec["commit"], "file": "xstest_prompts.csv", "dataset_digest": manifest["digest"],
        "id": "coluna id do CSV", "hash": "SHA-256 do texto normalizado (NFKC, minúsculas, espaços colapsados)",
        "split_seed": SPLIT_SEED, "s1_per_type": S1_PER_TYPE,
        "count": dict(sorted(Counter(it["uso"] for it in items).items())), "items": items,
    }, ensure_ascii=False, indent=1) + "\n")
    print(Counter(it["uso"] for it in items), "->", XSTEST_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
