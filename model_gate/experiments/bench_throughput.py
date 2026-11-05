"""Vazão de geração do base em 4 CPUs e custo estimado de S1 (T-208).

Mede tokens/s com o gerador da T-205 para 64 e 512 tokens e lotes 1, 4 e 8, com 3
repetições, usando o medidor da T-207 e o registro da T-206. O comprimento é forçado
(min_new_tokens = max_new_tokens) para medir vazão pura. Prompts: 8 seguros do XSTest.

    taskset -c 0-3 uv run python -m experiments.bench_throughput

Grava o resumo em results/T-208_vazao.json; a nota fica em results/T-208_vazao.md.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
from dataclasses import replace
from pathlib import Path

from experiments.check_determinism import safe_prompts
from experiments.fetch_base import MANIFEST, local_root
from experiments.runlog import RunLog, new_run_id
from experiments.timer import stage
from model_gate.io.generate import GenConfig, generate
from model_gate.io.load import load_model

OUT = Path(__file__).resolve().parents[1] / "results" / "T-208_vazao.json"


def cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tokens", type=int, nargs="+", default=[64, 512])
    ap.add_argument("--batches", type=int, nargs="+", default=[1, 4, 8])
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--prompts", type=int, default=8)
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()

    digest = json.loads(MANIFEST.read_text())["digest"]
    base_cfg = GenConfig(threads=args.threads)
    log = RunLog(new_run_id("t208"), model_digest=digest, seed=base_cfg.seed)
    affinity = sorted(os.sched_getaffinity(0))

    with stage("carregar", log):
        m = load_model(local_root(), digest)
    prompts = safe_prompts(args.prompts)
    generate(m.model, m.tokenizer, prompts[:1], replace(base_cfg, max_new_tokens=8))  # aquecimento

    cells = []
    for n_tok in args.tokens:
        for bs in args.batches:
            cfg = replace(base_cfg, max_new_tokens=n_tok, min_new_tokens=n_tok, batch_size=bs)
            rates = []
            for rep in range(args.reps):
                with stage(f"gerar_t{n_tok}_b{bs}_r{rep}", log, gen=cfg.record()) as s:
                    out = generate(m.model, m.tokenizer, prompts, cfg)
                toks = sum(r["n_tokens"] for r in out)
                rate = toks / s.result["wall_s"]
                rates.append(rate)
                log.log("T-208", "tokens_per_s", rate, gen=cfg.record(), rep=rep, tokens=toks,
                        peak_rss_gib=s.result["peak_rss_gib"])
                print(f"tokens={n_tok:4d} lote={bs} rep={rep} {rate:6.1f} tok/s", flush=True)
            cells.append({
                "max_new_tokens": n_tok, "batch_size": bs, "reps": rates,
                "mean_tok_s": statistics.mean(rates),
                "sd_tok_s": statistics.stdev(rates) if len(rates) > 1 else 0.0,
            })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "run_id": log.run_id, "git_commit": log.commit, "dirty": log.dirty,
        "model_digest": digest, "cpu": cpu_model(), "affinity": affinity,
        "threads": args.threads, "prompts": args.prompts, "cells": cells,
    }, indent=2) + "\n")
    print("resumo ->", OUT, "| registro ->", log.path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
