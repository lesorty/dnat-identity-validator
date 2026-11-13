"""Pacote da bateria para o job do Juiz (T-807), montado dos datasets locais fixados.

battery.json (stages.BATTERY_SCHEMA), conferido pelo job contra o acervo versionado:
    harmful    ID -> pedido do StrongREJECT (acervo público, harmful_ids.json)
    safe       ID -> pedido seguro do XSTest do uso s1 (xstest_ids.json)
    pairs      splits de Arditi para o S2 (direction_pairs.json), na ordem versionada
    utility    corpus de utilidade: pedido e resposta do Alpaca convertido (datasets/benign, T-902)
    templates  rubrica do StrongREJECT e classificador do XSTest (avaliador rubric)

Sem opções, leva tudo (313 nocivos, os seguros do S1, os pares inteiros, 32 de utilidade). As
opções --n-* tiram um subconjunto determinístico, só para a verificação local caber no notebook:
nocivos estratificados (os primeiros IDs de cada categoria), seguros os primeiros de cada tipo,
pares e utilidade um prefixo. A parte secreta (T-304) não entra aqui.

O pacote fica fora do git ($MODEL_GATE_DATA/battery/...): os textos nocivos não vão ao repositório.

    uv run python -m experiments.battery_pack --out DIR [--n-harmful 24 --n-safe 10 ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from experiments.fetch_datasets import DATASETS
from experiments.fetch_datasets import local_root as dataset_root
from experiments.data_dir import data_dir
from model_gate.battery.judge import xstest_template
from model_gate.battery.pool import by_category, safe_by_type
from model_gate.battery.texts import harmful_texts, safe_texts
from model_gate.signals.pairs import SPLITS, load_pairs, pair_texts, read_splits
from model_gate.stages import BATTERY_FILE, BATTERY_SCHEMA, battery_sha256, load_battery


def build(n_harmful: int | None = None, n_safe: int | None = None, n_pairs_train: int | None = None,
          n_pairs_val: int | None = None, n_utility: int = 32) -> dict:
    sr = dataset_root("strongreject", DATASETS["strongreject"]) / "strongreject_dataset/strongreject_dataset.csv"
    xs = dataset_root("xstest", DATASETS["xstest"]) / "xstest_prompts.csv"
    H, S = harmful_texts(sr), safe_texts(xs)
    if n_harmful:
        cats = by_category(sorted(H))
        per = max(1, n_harmful // len(cats))
        keep = sorted(i for ids in cats.values() for i in sorted(ids)[:per])
        H = {i: H[i] for i in keep}
    if n_safe:
        groups = safe_by_type()
        per = max(1, n_safe // len(groups))
        keep = sorted(i for ids in groups.values() for i in sorted(ids)[:per])
        S = {i: S[i] for i in keep}
    P = pair_texts(load_pairs(), read_splits(dataset_root("refusal_direction", DATASETS["refusal_direction"])))
    limits = {"harmful_train": n_pairs_train, "harmless_train": n_pairs_train,
              "harmful_val": n_pairs_val, "harmless_val": n_pairs_val}
    pairs = {s: P[s][:limits[s]] if limits[s] else P[s] for s in SPLITS}
    utility = []
    with open(data_dir() / "datasets" / "benign" / "alpaca.jsonl", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row.get("response", "").strip():
                utility.append({"prompt": row["prompt"], "response": row["response"]})
            if len(utility) >= n_utility:
                break
    ev = dataset_root("strongreject_evaluator", DATASETS["strongreject_evaluator"])
    xe = dataset_root("xstest_evaluator", DATASETS["xstest_evaluator"])
    templates = {"rubric": (ev / "strongreject/strongreject_evaluator_prompt.txt").read_text(),
                 "xstest": xstest_template((xe / "evaluation/classify_completions_gpt.py").read_text())}
    return {"schema": BATTERY_SCHEMA, "harmful": {str(k): v for k, v in H.items()},
            "safe": {str(k): v for k, v in S.items()}, "pairs": pairs, "utility": utility, "templates": templates}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    for k in ("harmful", "safe", "pairs-train", "pairs-val"):
        ap.add_argument(f"--n-{k}", type=int, default=None)
    ap.add_argument("--n-utility", type=int, default=32)
    a = ap.parse_args(argv)
    doc = build(a.n_harmful, a.n_safe, a.n_pairs_train, a.n_pairs_val, a.n_utility)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / BATTERY_FILE).write_text(json.dumps(doc, ensure_ascii=False))
    b = load_battery(a.out)  # confere contra o acervo, como o job
    print(json.dumps({"out": str(a.out), "harmful": len(b.harmful), "safe": len(b.safe),
                      "pairs": {k: len(v) for k, v in b.pairs.items()}, "utility": len(b.utility),
                      "sha256": battery_sha256(b)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
