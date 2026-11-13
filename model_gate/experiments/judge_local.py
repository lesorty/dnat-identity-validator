"""Juiz real no notebook (T-807): pai medido e derivados de verdade julgados pelo job, de ponta a ponta.

VERIFICAÇÃO DE FUNCIONAMENTO, não dado do artigo (todo dado do artigo sai da nuvem). Usa o base
Qwen2.5-0.5B conferido por digest, um pacote pequeno da bateria (experiments.battery_pack), o
prereg de fumaça (judge_local_prereg.yaml) e, por padrão, o avaliador de fumaça (detector de
recusa). Com --evaluator-kind guard, usa o Qwen3Guard-Gen-4B local, bem mais lento.

1. Mede o pai (reference.measure_parent) e guarda em $MODEL_GATE_DATA/references/ (reaproveita
   se o pacote, o desenho e o avaliador forem os mesmos).
2. Para cada derivado, escreve o manifesto dnat.judge-job.v1 e roda job.run_job com os estágios
   reais: cópia do base (controle), abliterações de fumaça (d6, d12) e o LoRA de aritmética.
3. Grava estado, regra, motivos, sinais e tempos em results/T-807_juiz_local.json e .md.

    taskset -c 0-3 uv run python -m experiments.judge_local [--evaluator-kind guard]
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

from experiments.data_dir import data_dir
from experiments.fetch_base import MANIFEST, local_root
from model_gate.io.digest import file_sha256
from model_gate.io.load import dir_digest
from model_gate.job import SCHEMA_ID, VERDICT_FILE, Manifest, run_job
from model_gate.judge_package import judge_hash
from model_gate.reference import FILE as REF_FILE
from model_gate.reference import measure_parent
from model_gate.stages import RealStages, battery_sha256, load_battery, load_prereg
from model_gate.verdict.emit import read

ROOT = Path(__file__).resolve().parents[1]
PREREG = Path(__file__).with_name("judge_local_prereg.yaml")
OUT = ROOT / "results" / "T-807_juiz_local"
GUARD = data_dir() / "models" / "Qwen__Qwen3Guard-Gen-4B" / "6ec42827da0c1ff11e7a49dc269d2e810d27e108"
DERIVATIVES = [
    ("controle (cópia do base)", None),
    ("abliteração d6", "fumaca-abl-d6-a1-todas"),
    ("abliteração d12", "fumaca-abl-d12-a1-todas"),
    ("LoRA aritmética", "fumaca-aritmetica-s0"),
]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--battery", type=Path, default=data_dir() / "battery" / "local_t807")
    ap.add_argument("--evaluator-kind", default="detector", choices=("detector", "guard"))
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args(argv)

    base = local_root()
    base_digest = json.loads(MANIFEST.read_text())["digest"]
    battery = load_battery(a.battery)
    _, _, settings = load_prereg(PREREG)
    ev_spec = None
    if a.evaluator_kind == "guard":
        ev_spec = {"path": str(GUARD), "kind": "dir", "digest": dir_digest(GUARD)[0]}
    from model_gate.evaluators import make_evaluator
    evaluator = make_evaluator(a.evaluator_kind, model_dir=GUARD if ev_spec else None,
                               model_digest=ev_spec["digest"] if ev_spec else None, threads=a.threads)

    tag = f"t807_{a.evaluator_kind}_{battery_sha256(battery)[:8]}_{file_sha256(PREREG)[:8]}"
    ref_dir = data_dir() / "references" / tag
    t0 = time.perf_counter()
    if not (ref_dir / REF_FILE).exists():
        print("medindo o pai em", ref_dir, flush=True)
        measure_parent(base, base_digest, battery, evaluator, settings, ref_dir, threads=a.threads)
    ref_seconds = time.perf_counter() - t0
    ref = json.loads((ref_dir / REF_FILE).read_text())
    anchors = {f: {c: sum(map(len, v.values())) for c, v in d.items()} for f, d in ref["anchors"].items()}
    print("âncoras do pai:", anchors, f"({ref_seconds:.0f} s)", flush=True)

    work = Path(tempfile.mkdtemp(prefix="t807_", dir=data_dir() / "runs"))
    (work / "dataset.csv").write_text("prompt,response\nWhat is 2 + 2?,4\nName a color.,Blue\n")
    stages = RealStages(threads=a.threads)  # um cache de modelos por job: recria por derivado abaixo
    results = []
    for name, sub in DERIVATIVES:
        der = base if sub is None else data_dir() / "derivatives" / sub
        inputs = {
            "base": {"path": str(base), "kind": "dir", "digest": base_digest},
            "derivative": {"path": str(der), "kind": "dir", "digest": dir_digest(der)[0]},
            "parent_reference": {"path": str(ref_dir), "kind": "dir", "digest": dir_digest(ref_dir)[0]},
            "battery": {"path": str(a.battery), "kind": "dir", "digest": dir_digest(a.battery)[0]},
            "dataset": {"path": str(work / "dataset.csv"), "kind": "file", "digest": file_sha256(work / "dataset.csv")},
            "prereg": {"path": str(PREREG), "kind": "file", "digest": file_sha256(PREREG)},
        }
        if ev_spec:
            inputs["evaluator"] = ev_spec
        mpath = work / f"job_{len(results)}.json"
        mpath.write_text(json.dumps({
            "schema": SCHEMA_ID, "inputs": inputs, "judge_hash": judge_hash()[0], "battery_commitment": "0" * 64,
            "identity_id": "0" * 64, "decided_at": "2026-11-13T00:00:00Z",
            "evaluator": {"kind": a.evaluator_kind}, "sampling_key": "5a" * 16}))
        out = work / f"out_{len(results)}"
        stages = RealStages(threads=a.threads)
        stages._cache["evaluator"] = evaluator  # o mesmo avaliador já carregado
        t = time.perf_counter()
        res = run_job(Manifest.load(mpath), out, stages)
        secs = time.perf_counter() - t
        row = {"derivative": name, "dir": sub, "status": res["status"], "seconds": round(secs, 1)}
        if res["status"] == "verdict":
            doc, _ = read(out / VERDICT_FILE)
            harm = {f"{c['format']}/{c['condition']}": (c["derivative"]["harm_rate"], c["parent"]["harm_rate"])
                    for c in doc["measures"]["s1"] if c["block"] == "anchors" and c["category"] == "todas"}
            row |= {"state": doc["state"], "rule": doc["rule"], "reasons": sorted({r["code"] for r in doc["reasons"]}),
                    "harm_anchors_derivative_parent": harm, "signals": doc["measures"]["signals"],
                    "utility": doc["measures"]["utility"]}
        else:
            row["error"] = res.get("error")
        results.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    meta = {"note": "Verificação local do Juiz real (T-807). Prereg e avaliador de FUMAÇA; não é dado do artigo.",
            "evaluator_kind": a.evaluator_kind, "judge_hash": judge_hash()[0], "base_digest": base_digest,
            "battery_sha256": battery_sha256(battery), "settings": settings.record(), "parent_anchors": anchors,
            "reference_seconds": round(ref_seconds, 1), "results": results}
    OUT.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n")
    lines = ["# Juiz real no notebook (T-807)", "", meta["note"], "",
             f"Avaliador: {a.evaluator_kind} · Juiz `{meta['judge_hash'][:12]}` · âncoras do pai {anchors}", "",
             "| Derivado | Estado | Regra | Motivos | Dano nas âncoras (derivado / pai) | s |", "|---|---|---|---|---|---|"]
    for r in results:
        harm = "; ".join(f"{k} {d:.2f}/{p:.2f}" for k, (d, p) in (r.get("harm_anchors_derivative_parent") or {}).items()
                         if d is not None and p is not None)
        lines.append(f"| {r['derivative']} | {r.get('state', r['status'])} | {r.get('rule', '-')} | "
                     f"{', '.join(r.get('reasons', [])) or r.get('error', '')} | {harm} | {r['seconds']} |")
    OUT.with_suffix(".md").write_text("\n".join(lines) + "\n")
    print("->", OUT.with_suffix(".md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
