"""Exemplo real da geração do S1 (T-307): o pai responde a uma amostra pequena nas duas condições.

12 nocivos (os 2 primeiros IDs de cada categoria) e 10 seguros do S1 (o primeiro de cada tipo),
com o gerador canônico (guloso, lote 1, até 512 tokens). Confere que os textos batem com o
acervo, que a geração é determinística (repete o primeiro item) e mede o tempo. Grava só IDs,
marca de recusa, tokens e tempo em results/T-307_exemplo.json; os textos vão para
$MODEL_GATE_DATA/runs/.

    taskset -c 0-3 uv run python -m experiments.s1_example
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from experiments.data_dir import data_dir
from experiments.fetch_base import MANIFEST, local_root
from experiments.fetch_datasets import DATASETS
from experiments.fetch_datasets import local_root as dataset_root
from experiments.runlog import RunLog, new_run_id
from model_gate.battery.configs import gen_config
from model_gate.battery.pool import by_category, safe_by_type
from model_gate.battery.s1 import parent_reference, respond
from model_gate.battery.texts import harmful_texts, safe_texts
from model_gate.io.load import load_model

OUT = Path(__file__).resolve().parents[1] / "results" / "T-307_exemplo.json"


def main() -> int:
    digest = json.loads(MANIFEST.read_text())["digest"]
    log = RunLog(new_run_id("t307ex"), model_digest=digest, seed=0)
    sr = dataset_root("strongreject", DATASETS["strongreject"]) / "strongreject_dataset/strongreject_dataset.csv"
    xs = dataset_root("xstest", DATASETS["xstest"]) / "xstest_prompts.csv"
    H, S = harmful_texts(sr), safe_texts(xs)
    h_ids = [i for ids in by_category(sorted(H)).values() for i in sorted(ids)[:2]]
    s_ids = [sorted(ids)[0] for ids in safe_by_type().values()]
    m = load_model(local_root(), digest)
    t0 = time.perf_counter()
    ref = parent_reference(m.model, m.tokenizer, {i: H[i] for i in h_ids}, {i: S[i] for i in s_ids})
    secs = time.perf_counter() - t0
    again = respond(m.model, m.tokenizer, H, [h_ids[0]], "vazio")[0]
    same = again["text"] == ref["vazio"]["harmful"][0]["text"]
    texts = {c: {k: {r["id"]: r["text"] for r in ref[c][k]} for k in ("harmful", "safe")} for c in ref}
    (data_dir() / "runs" / f"{log.run_id}_texts.json").write_text(json.dumps(texts, ensure_ascii=False, indent=1))
    summary = {c: {"harmful": [{k: r[k] for k in ("id", "refused", "n_tokens")} for r in ref[c]["harmful"]],
                   "safe": [{k: r[k] for k in ("id", "refused", "n_tokens")} for r in ref[c]["safe"]],
                   "anchors": ref[c]["anchors"]} for c in ref}
    n_gen = sum(len(ref[c][k]) for c in ref for k in ("harmful", "safe"))
    log.log("T-307ex", "seconds", round(secs, 1), gen=gen_config("vazio").record(), items=n_gen, deterministic=same)
    OUT.write_text(json.dumps({"run_id": log.run_id, "git_commit": log.commit, "dirty": log.dirty, "model_digest": digest,
                               "items_harmful": h_ids, "items_safe": s_ids, "generations": n_gen,
                               "seconds": round(secs, 1), "seconds_per_item": round(secs / n_gen, 2),
                               "deterministic_repeat": same, "conditions": summary}, ensure_ascii=False, indent=1) + "\n")
    for c in ref:
        print(c, "âncoras:", {k: len(v) for k, v in ref[c]["anchors"].items()},
              "recusa nos seguros:", sum(r["refused"] for r in ref[c]["safe"]), "/", len(s_ids))
    print(f"{n_gen} gerações em {secs:.0f} s; repetição idêntica: {same} ->", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
