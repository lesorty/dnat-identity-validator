"""Custo e reprodutibilidade dos dois avaliadores em CPU (T-309).

Pontua duas vezes 10 respostas reais do Qwen2.5-0.5B (exemplo da T-307: 5 recusas e 5 não
recusas a pedidos nocivos) com cada avaliador, mede o tempo por item e projeta o custo do
avaliador num veredito inteiro. Um avaliador por vez, para caber na RAM.

- Gemma 4 E4B em bfloat16 (8B parâmetros no total; em float32 não cabe em 30 GB);
- Qwen3Guard-Gen-4B em float32 (como o resto do Juiz) e, para comparar, em bfloat16.

    taskset -c 0-3 uv run python -m experiments.judge_bench [--only gemma|qwen3guard]
"""

from __future__ import annotations

import argparse
import gc
import glob
import json
import statistics
import sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from experiments.data_dir import data_dir
from experiments.fetch_datasets import DATASETS
from experiments.fetch_datasets import local_root as dataset_root
from experiments.fetch_judges import JUDGES, MANIFEST
from experiments.fetch_judges import local_root as judge_root
from experiments.runlog import RunLog, new_run_id
from model_gate.battery.judge import GuardJudge, RubricJudge
from model_gate.battery.texts import harmful_texts
from model_gate.io.load import dir_digest

OUT = Path(__file__).resolve().parents[1] / "results" / "T-309_avaliador.json"
# Chamadas do avaliador por veredito (redução v2): 2 formatos × 2 condições, cada uma com
# 48 âncoras (32 públicas + 16 secretas), 6 codificados e 25 seguros.
CONFIGS, PER_CONFIG = 4, 48 + 6 + 25


def sample() -> list[dict]:
    texts = json.loads(Path(sorted(glob.glob(str(data_dir() / "runs" / "t307ex_*_texts.json")))[-1]).read_text())
    ex = json.loads((OUT.parent / "T-307_exemplo.json").read_text())
    H = harmful_texts(dataset_root("strongreject", DATASETS["strongreject"]) / "strongreject_dataset/strongreject_dataset.csv")
    rows = [(c, r) for c in ("vazio", "padrao") for r in ex["conditions"][c]["harmful"]]
    ref = [x for x in rows if x[1]["refused"]][:5]
    com = [x for x in rows if not x[1]["refused"]][:5]
    return [{"condition": c, "id": r["id"], "refused_detector": r["refused"], "n_tokens_response": r["n_tokens"],
             "prompt": H[r["id"]], "response": texts[c]["harmful"][str(r["id"])]} for c, r in ref + com]


def load(name: str, dtype):
    root = judge_root(name)
    tok = AutoTokenizer.from_pretrained(root)
    try:
        model = AutoModelForCausalLM.from_pretrained(root, dtype=dtype, use_safetensors=True)
    except (ValueError, KeyError):
        from transformers import AutoModelForImageTextToText
        model = AutoModelForImageTextToText.from_pretrained(root, dtype=dtype, use_safetensors=True)
    return model.eval(), tok


def bench(name: str, dtype_name: str, items: list[dict], template: str | None, log: RunLog) -> dict:
    dtype = {"bfloat16": torch.bfloat16, "float32": torch.float32}[dtype_name]
    model, tok = load(name, dtype)
    judge = RubricJudge(model, tok, template) if name == "gemma" else GuardJudge(model, tok)
    runs = []
    for rep in range(2):
        out = []
        for it in items:
            s = judge.score(it["prompt"], it["response"])
            out.append(s)
            log.log("T-309", "seconds", round(s.seconds, 2), judge=name, dtype=dtype_name, rep=rep, item=it["id"],
                    condition=it["condition"], harm=s.harm, refused=s.refused, prompt_tokens=s.n_prompt_tokens,
                    new_tokens=s.n_new_tokens)
            print(f"{name} {dtype_name} rep{rep} {it['condition']:6s} {it['id']:3d} harm={s.harm} refused={s.refused} "
                  f"{s.seconds:6.1f}s in={s.n_prompt_tokens} out={s.n_new_tokens}", flush=True)
        runs.append(out)
    del model, judge
    gc.collect()
    secs = [s.seconds for s in runs[0] + runs[1]]
    per_item = statistics.mean(secs)
    return {
        "judge": name, "repo_id": JUDGES[name]["repo_id"], "revision": JUDGES[name]["revision"], "dtype": dtype_name,
        "deterministic": [a.raw for a in runs[0]] == [b.raw for b in runs[1]],
        "unparsed": sum(s.harm != s.harm for s in runs[0]),
        "seconds_per_item": round(per_item, 2), "seconds_sd": round(statistics.stdev(secs), 2),
        "prompt_tokens_mean": round(statistics.mean(s.n_prompt_tokens for s in runs[0]), 1),
        "new_tokens_mean": round(statistics.mean(s.n_new_tokens for s in runs[0]), 1),
        "verdict_minutes": round(per_item * CONFIGS * PER_CONFIG / 60, 1),
        "scores": [{"id": it["id"], "condition": it["condition"], "refused_detector": it["refused_detector"],
                    "harm": s.harm, "refused": s.refused} for it, s in zip(items, runs[0])],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", choices=["gemma", "qwen3guard"])
    args = ap.parse_args()
    items = sample()
    manifest = json.loads(MANIFEST.read_text())
    tpl = (dataset_root("strongreject_evaluator", DATASETS["strongreject_evaluator"]) /
           "strongreject/strongreject_evaluator_prompt.txt").read_text()
    log = RunLog(new_run_id("t309"), model_digest="judges", seed=0)
    res = json.loads(OUT.read_text()) if OUT.exists() else {"runs": []}
    plan = [("qwen3guard", "float32"), ("qwen3guard", "bfloat16"), ("gemma", "bfloat16")]
    for name, dt in plan:
        if args.only and name != args.only:
            continue
        digest = dir_digest(judge_root(name))[0]
        if digest != manifest[name]["digest"]:
            print(f"ERRO: {name} não bate com o manifesto", file=sys.stderr)
            return 1
        r = bench(name, dt, items, tpl if name == "gemma" else None, log)
        r["digest"] = digest
        res["runs"] = [x for x in res["runs"] if (x["judge"], x["dtype"]) != (name, dt)] + [r]
        res.update({"run_id": log.run_id, "git_commit": log.commit, "dirty": log.dirty,
                    "items": [{k: it[k] for k in ("condition", "id", "refused_detector", "n_tokens_response")} for it in items],
                    "verdict_calls": CONFIGS * PER_CONFIG,
                    "verdict_calls_note": "2 formatos × 2 condições × (48 âncoras + 6 codificados + 25 seguros)",
                    "cpu": "4 núcleos do notebook (taskset -c 0-3)"})
        OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
        print(f"{name} {dt}: {r['seconds_per_item']} s/item, determinístico={r['deterministic']}, "
              f"veredito ≈ {r['verdict_minutes']} min", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
