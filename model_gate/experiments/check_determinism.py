"""Critério da T-205: 10 respostas iguais em duas execuções do base custodiado.

Usa os 10 primeiros prompts seguros do XSTest (sem conteúdo nocivo). Gera duas
vezes com lote 1 e compara texto a texto; gera também com lote 4 e informa se o
texto muda. As gerações vão para $MODEL_GATE_DATA/runs/; só o hash é impresso.

    uv run python -m experiments.check_determinism [--max-new-tokens 128]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from dataclasses import replace

from experiments.data_dir import data_dir
from experiments.fetch_base import MANIFEST, local_root
from experiments.fetch_datasets import DATASETS
from experiments.fetch_datasets import local_root as dataset_root
from model_gate.io.generate import GenConfig, generate
from model_gate.io.load import load_model


def safe_prompts(n: int) -> list[str]:
    path = dataset_root("xstest", DATASETS["xstest"]) / "xstest_prompts.csv"
    with open(path, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["label"] == "safe"]
    return [r["prompt"] for r in sorted(rows, key=lambda r: int(r["id"]))[:n]]


def texts_hash(out: list[dict]) -> str:
    return hashlib.sha256(json.dumps([r["text"] for r in out], ensure_ascii=False).encode()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--max-new-tokens", type=int, default=128)
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()

    digest = json.loads(MANIFEST.read_text())["digest"]
    m = load_model(local_root(), digest)
    prompts = safe_prompts(args.n)
    cfg = GenConfig(max_new_tokens=args.max_new_tokens, threads=args.threads)

    t0 = time.perf_counter()
    a = generate(m.model, m.tokenizer, prompts, cfg)
    t1 = time.perf_counter()
    b = generate(m.model, m.tokenizer, prompts, cfg)
    c = generate(m.model, m.tokenizer, prompts, replace(cfg, batch_size=4))

    diff = [i for i, (x, y) in enumerate(zip(a, b)) if x["text"] != y["text"]]
    diff_batch = [i for i, (x, y) in enumerate(zip(a, c)) if x["text"] != y["text"]]
    tokens = sum(r["n_tokens"] for r in a)

    run = data_dir() / "runs" / f"t205_{time.strftime('%Y%m%dT%H%M%S')}.json"
    run.parent.mkdir(parents=True, exist_ok=True)
    run.write_text(
        json.dumps(
            {"digest": digest, "config": cfg.record(), "prompts": prompts, "a": a, "b": b, "batch4": c},
            ensure_ascii=False,
            indent=1,
        )
    )

    print(f"digest do base     {digest}")
    print(f"config             {cfg.record()}")
    print(f"hash dos textos    {texts_hash(a)}")
    print(f"lote 1, duas vezes {'IGUAIS' if not diff else f'DIFEREM em {diff}'}")
    print(f"lote 4 x lote 1    {'iguais' if not diff_batch else f'diferem em {diff_batch}'}")
    print(f"tokens gerados     {tokens} em {t1 - t0:.1f} s ({tokens / (t1 - t0):.1f} tok/s, lote 1)")
    print(f"gerações em        {run}")
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
