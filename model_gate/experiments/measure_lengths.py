"""Comprimento real das respostas do base e custo de S1 sem o pior caso (segue a T-208).

Gera com o gerador canônico (guloso, lote 1, teto de 512 tokens, para no EOS) em:
- StrongREJECT small (60 nocivos, 6 categorias);
- XSTest: amostra fixa de seguros e de contrastes inseguros;
nas condições system prompt vazio explícito e padrão do base (E14 §6.2).

Grava no registro (T-206) só tokens e tempo por item; os textos vão para
$MODEL_GATE_DATA/runs/ (T-211). Resumo em results/T-208_comprimento.json.

    taskset -c 0-3 uv run python -m experiments.measure_lengths [--xstest-per-label 25]
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

from experiments.data_dir import data_dir
from experiments.fetch_base import MANIFEST, local_root
from experiments.fetch_datasets import DATASETS
from experiments.fetch_datasets import local_root as dataset_root
from experiments.runlog import RunLog, new_run_id
from model_gate.io.generate import GenConfig, generate
from model_gate.io.load import load_model

OUT = Path(__file__).resolve().parents[1] / "results" / "T-208_comprimento.json"
CONDITIONS = {"vazio": "", "padrao": None}


def _rows(name: str, rel: str) -> list[dict]:
    with open(dataset_root(name, DATASETS[name]) / rel, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def item_sets(xstest_per_label: int) -> dict[str, list[str]]:
    sr = _rows("strongreject", "strongreject_dataset/strongreject_small_dataset.csv")
    xs = sorted(_rows("xstest", "xstest_prompts.csv"), key=lambda r: int(r["id"]))

    def spread(rows: list[dict], n: int) -> list[dict]:  # amostra fixa espalhada pelos tipos
        step = max(1, len(rows) // n)
        return rows[::step][:n]

    return {
        "strongreject": [r["forbidden_prompt"] for r in sr],
        "xstest_safe": [r["prompt"] for r in spread([r for r in xs if r["label"] == "safe"], xstest_per_label)],
        "xstest_unsafe": [r["prompt"] for r in spread([r for r in xs if r["label"] == "unsafe"], xstest_per_label)],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--xstest-per-label", type=int, default=25)
    ap.add_argument("--max-new-tokens", type=int, default=512)
    args = ap.parse_args()

    digest = json.loads(MANIFEST.read_text())["digest"]
    cfg0 = GenConfig(max_new_tokens=args.max_new_tokens)
    log = RunLog(new_run_id("t208len"), model_digest=digest, seed=cfg0.seed)
    m = load_model(local_root(), digest)
    sets = item_sets(args.xstest_per_label)
    texts: dict = {}
    summary = []

    for cond, sp in CONDITIONS.items():
        cfg = replace(cfg0, system_prompt=sp)
        for name, prompts in sets.items():
            toks, secs = [], []
            texts[f"{cond}/{name}"] = []
            for i, p in enumerate(prompts):
                t0 = time.perf_counter()
                (r,) = generate(m.model, m.tokenizer, [p], cfg)
                dt = time.perf_counter() - t0
                toks.append(r["n_tokens"])
                secs.append(dt)
                texts[f"{cond}/{name}"].append(r["text"])
                log.log("T-208len", "n_tokens", r["n_tokens"], gen=cfg.record(), condition=cond,
                        dataset=name, item=i, seconds=round(dt, 3))
            row = {
                "condition": cond, "dataset": name, "items": len(prompts),
                "mean_tokens": statistics.mean(toks), "median_tokens": statistics.median(toks),
                "max_tokens": max(toks), "frac_at_cap": sum(t >= args.max_new_tokens for t in toks) / len(toks),
                "mean_seconds": statistics.mean(secs), "tok_per_s": sum(toks) / sum(secs),
            }
            summary.append(row)
            print(f"{cond:6s} {name:13s} n={row['items']:3d} média={row['mean_tokens']:6.1f} "
                  f"mediana={row['median_tokens']:6.1f} no_teto={row['frac_at_cap']:.0%} "
                  f"{row['mean_seconds']:5.1f} s/item", flush=True)

    (data_dir() / "runs" / f"{log.run_id}_texts.json").write_text(json.dumps(texts, ensure_ascii=False, indent=1))
    OUT.write_text(json.dumps({
        "run_id": log.run_id, "git_commit": log.commit, "dirty": log.dirty, "model_digest": digest,
        "max_new_tokens": args.max_new_tokens, "summary": summary,
    }, indent=2) + "\n")
    print("resumo ->", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
