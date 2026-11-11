"""Grava o acervo público de nocivos do S1 (T-302) a partir do StrongREJECT no commit fixado.

Sai src/model_gate/battery/harmful_ids.json: digest do conjunto, e para cada linha o ID, a
categoria, a origem e o SHA-256 do texto normalizado. Nenhum texto entra no git (T-211).

    uv run python -m experiments.build_harmful_pool
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter

from experiments.fetch_datasets import DATASETS
from experiments.fetch_datasets import local_root as dataset_root
from model_gate.battery.pool import POOL_PATH, prompt_hash

REL = "strongreject_dataset/strongreject_dataset.csv"


def main() -> int:
    spec = DATASETS["strongreject"]
    manifest = json.loads((POOL_PATH.parents[3] / "data" / "datasets.manifest.json").read_text())["strongreject"]
    with open(dataset_root("strongreject", spec) / REL, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    items = [{"id": i, "category": r["category"], "source": r["source"], "sha256": prompt_hash(r["forbidden_prompt"])}
             for i, r in enumerate(rows)]
    dup = [h for h, n in Counter(it["sha256"] for it in items).items() if n > 1]
    POOL_PATH.write_text(json.dumps({
        "dataset": "strongreject", "commit": spec["commit"], "file": REL, "dataset_digest": manifest["digest"],
        "id": "linha do CSV (0-based)", "hash": "SHA-256 do texto normalizado (NFKC, minúsculas, espaços colapsados)",
        "count": len(items), "by_category": dict(sorted(Counter(it["category"] for it in items).items())),
        "duplicated_hashes": dup, "items": items,
    }, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(items)} itens, {len(dup)} hashes repetidos ->", POOL_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
