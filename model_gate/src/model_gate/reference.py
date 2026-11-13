"""Referência custodiada do pai (código da T-312; E14 §6.1, R9): o base medido uma vez, no depósito.

Mede o base com o mesmo código, desenho e avaliador que o job do Juiz usa no derivado, e grava:

    reference.json         dnat.parent-reference.v1 (abaixo)
    direction.safetensors  direção de recusa do S2 (signals.direction), se o pacote tem os pares

reference.json:
    base_digest, judge_id, evaluator_kind, settings (desenho do S1), battery_sha256
    formats, conditions
    anchors   formato -> condição -> categoria -> IDs que o pai recusa (as âncoras do sorteio)
    rows      notas por item do pai (score.score_run, sem a saída crua do avaliador), por formato
    direction {file, content_sha256, condition, layer} ou null
    gap_base  formato -> gap por camada do pai nos pares de validação (ρ compara no mesmo formato)
    utility   {ce, n}: entropia cruzada do pai nas respostas do corpus de utilidade (FP)

Os textos das respostas do pai não entram: o veredito compara notas, e os textos ficam fora (T-211).
Na campanha, a referência é medida na nuvem (T-312); aqui roda para verificação, com modelos locais.

    python -m model_gate.reference --base DIR --battery DIR --prereg prereg.yaml \\
        --evaluator-kind guard --evaluator DIR --out DIR
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from model_gate.battery.pool import load_pool
from model_gate.battery.score import PARENT_BLOCKS, TEXT_FIELDS, score_run
from model_gate.stages import Battery, S1Settings, battery_sha256, load_battery, model_in_format, response_ce

SCHEMA = "dnat.parent-reference.v1"
FILE = "reference.json"
DIRECTION_FILE = "direction.safetensors"
DIRECTION_CONDITION = "vazio"  # a mais próxima do template de Arditi (experiments/s2_reference.py)


def measure_parent(base_dir: Path, base_digest: str, battery: Battery, evaluator, settings: S1Settings,
                   out_dir: Path, *, pool: dict | None = None, threads: int = 4) -> dict:
    """Mede o pai e grava o pacote em out_dir. Devolve o conteúdo de reference.json."""
    import torch

    from model_gate.battery.s1 import parent_reference
    from model_gate.io.load import load_model
    from model_gate.signals.activations import last_token_resid
    from model_gate.signals.direction import fit, save_direction
    from model_gate.signals.s2 import refusal_gap

    pool = pool or load_pool()
    base = load_model(base_dir, base_digest)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    anchors, rows = {}, []
    prompts = {"harmful": battery.harmful, "safe": battery.safe}
    for fmt in settings.formats:
        model_f = model_in_format(base.model, fmt)
        run = parent_reference(model_f, base.tokenizer, battery.harmful, battery.safe,
                               conditions=settings.conditions, cfg_for=settings.gen_cfg, pool=pool)
        anchors[fmt] = {c: run[c]["anchors"] for c in settings.conditions}
        scored = score_run(run, PARENT_BLOCKS, prompts, evaluator.judges(), model_digest=base_digest, fmt=fmt)
        rows += [{k: v for k, v in r.items() if k not in TEXT_FIELDS} for r in scored]
        del model_f

    direction, gap_base = None, {}
    splits = ("harmful_train", "harmless_train", "harmful_val", "harmless_val")
    if all(s in battery.pairs and battery.pairs[s] for s in splits):
        sp = settings.system_prompt(DIRECTION_CONDITION)
        acts = {s: last_token_resid(base.model, base.tokenizer, battery.pairs[s], sp, threads) for s in splits}
        fitted = fit(acts["harmful_train"], acts["harmless_train"], acts["harmful_val"], acts["harmless_val"])
        sha = save_direction(out_dir / DIRECTION_FILE, fitted,
                             {"base_digest": base_digest, "condition": DIRECTION_CONDITION,
                              "n_pairs": {s: len(battery.pairs[s]) for s in splits}})
        direction = {"file": DIRECTION_FILE, "content_sha256": sha, "condition": DIRECTION_CONDITION,
                     "layer": int(fitted["layer"])}
        for fmt in settings.formats:
            if fmt == "fp":
                gap = fitted["gap_base"]
            else:
                model_f = model_in_format(base.model, fmt)
                h = last_token_resid(model_f, base.tokenizer, battery.pairs["harmful_val"], sp, threads)
                n = last_token_resid(model_f, base.tokenizer, battery.pairs["harmless_val"], sp, threads)
                gap = refusal_gap(h, n, fitted["dirs"])
                del model_f
            gap_base[fmt] = [float(x) for x in torch.as_tensor(gap)]

    utility = None
    if battery.utility:
        corpus = battery.utility[:settings.utility_n]
        utility = {"ce": response_ce(base.model, base.tokenizer, corpus, threads), "n": len(corpus)}

    doc = {
        "schema": SCHEMA,
        "base_digest": base_digest,
        "judge_id": evaluator.judge_id,
        "evaluator_kind": evaluator.kind,
        "settings": settings.record(),
        "battery_sha256": battery_sha256(battery),
        "formats": list(settings.formats),
        "conditions": list(settings.conditions),
        "anchors": anchors,
        "rows": rows,
        "direction": direction,
        "gap_base": gap_base,
        "utility": utility,
        "measured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    # NaN (falha do avaliador num item) fica como NaN: a T-311 trata a célula como falha.
    (out_dir / FILE).write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True))
    return doc


def load_reference(root: Path) -> dict:
    """Lê o pacote; a direção é conferida pelo hash do conteúdo gravado em reference.json."""
    root = Path(root)
    doc = json.loads((root / FILE).read_text())
    if doc.get("schema") != SCHEMA:
        raise ValueError(f"referência: schema {doc.get('schema')!r}, esperava {SCHEMA}")
    if doc.get("direction"):
        from model_gate.signals.direction import load_direction
        d = load_direction(root / doc["direction"]["file"], doc["direction"]["content_sha256"])
        doc["direction"] = {**doc["direction"], "dirs": d["dirs"], "layer": int(d["layer"])}
    if doc.get("utility") is None:
        doc["utility"] = {"ce": None}
    return doc


def main(argv: list[str] | None = None) -> int:
    from model_gate.evaluators import make_evaluator
    from model_gate.io.load import dir_digest
    ap = argparse.ArgumentParser(description="Mede o pai e grava a referência custodiada (T-312)")
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--battery", type=Path, required=True)
    ap.add_argument("--prereg", type=Path, required=True, help="lê só a seção s1 (desenho)")
    ap.add_argument("--evaluator-kind", required=True)
    ap.add_argument("--evaluator", type=Path, default=None)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args(argv)
    import yaml
    settings = S1Settings.from_prereg(yaml.safe_load(a.prereg.read_text()))
    battery = load_battery(a.battery)
    ev = make_evaluator(a.evaluator_kind, model_dir=a.evaluator,
                        model_digest=dir_digest(a.evaluator)[0] if a.evaluator else None,
                        templates=battery.templates, threads=a.threads)
    doc = measure_parent(a.base, dir_digest(a.base)[0], battery, ev, settings, a.out, threads=a.threads)
    print(json.dumps({"out": str(a.out), "base_digest": doc["base_digest"], "judge_id": doc["judge_id"],
                      "anchors": {f: {c: sum(map(len, v.values())) for c, v in d.items()} for f, d in doc["anchors"].items()},
                      "direction": bool(doc["direction"]), "utility": doc["utility"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
