"""Camada da direção de recusa pelo efeito da intervenção (T-414), comparada com a da T-402.

VERIFICAÇÃO LOCAL no Qwen2.5-0.5B, não dado do artigo: a direção oficial e a decisão final são
regeradas na nuvem com o código congelado (T-312). Sem avaliador.

1. Para cada camada candidata (4 a 18 de 24), com a direção da camada tirada do pacote da T-402:
   bypass (pontuação de recusa nos 32 nocivos da validação com a direção ablada em tudo), induce
   (pontuação nos 32 inócuos com a diferença de médias somada na camada), kl (primeiro token dos
   inócuos, base × ablado) e a taxa de recusa pelo detector nos nocivos ablados (gulosa, 32 tokens).
2. Escolhe pela regra de Arditi (model_gate.signals.intervention.choose) e compara com a camada da
   T-402 (critério da separação).
3. S2 dos abliterados da T-908 lido nas duas camadas (ratio) e na faixa do meio (ratio_band).

Condição "vazio", a mesma da direção. Resultado em results/T-414_camada.{json,md}.

    taskset -c 0-3 uv run python -m experiments.layer_select [--layers 4-18]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

from experiments.data_dir import data_dir
from experiments.fetch_base import MANIFEST, local_root
from experiments.fetch_datasets import DATASETS
from experiments.fetch_datasets import local_root as dataset_root
from experiments.runlog import RunLog, new_run_id
from model_gate.battery.configs import gen_config
from model_gate.battery.refusal import is_refusal
from model_gate.io.generate import generate
from model_gate.io.load import dir_digest, load_model
from model_gate.signals.activations import last_token_resid
from model_gate.signals.direction import load_direction
from model_gate.signals.intervention import (KL_MAX, LAYER_MAX_FRACTION, REFUSAL_PREFIXES, ablate, add_direction,
                                             choose, first_token_logprobs, kl, refusal_score, refusal_token_ids)
from model_gate.signals.pairs import load_pairs, pair_texts, read_splits
from model_gate.signals.s2 import s2

OUT = Path(__file__).resolve().parents[1] / "results" / "T-414_camada"
CONDITION = "vazio"
MAX_NEW_TOKENS = 32
DERIVATIVES = ("fumaca-abl-d6-a1-todas", "fumaca-abl-d12-a1-todas")


def refusal_rate(model, tok, prompts, sp) -> float:
    cfg = replace(gen_config(CONDITION), max_new_tokens=MAX_NEW_TOKENS, batch_size=8)
    cfg = replace(cfg, system_prompt=sp)
    outs = generate(model, tok, prompts, cfg)
    return sum(is_refusal(o["text"]) for o in outs) / len(outs)


def parse_layers(spec: str) -> list[int]:
    lo, hi = spec.split("-")
    return list(range(int(lo), int(hi) + 1))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--layers", default="4-18")
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args(argv)

    import torch

    torch.set_num_threads(a.threads)
    digest = json.loads(MANIFEST.read_text())["digest"]
    pack_path = data_dir() / "references" / f"base_{digest[:12]}" / "refusal_dirs.safetensors"
    pack = load_direction(pack_path)
    P = pair_texts(load_pairs(), read_splits(dataset_root("refusal_direction", DATASETS["refusal_direction"])))
    harm, harmless = P["harmful_val"], P["harmless_val"]
    sp = gen_config(CONDITION).system_prompt

    log = RunLog(new_run_id("t414"), model_digest=digest)
    b = load_model(local_root(), digest)
    m, tok = b.model, b.tokenizer
    L = m.config.num_hidden_layers
    ids = refusal_token_ids(tok)
    t0 = time.perf_counter()
    base_harm = first_token_logprobs(m, tok, harm, sp)
    base_harmless = first_token_logprobs(m, tok, harmless, sp)
    base = {"refusal_score_harmful": float(refusal_score(base_harm, ids).mean()),
            "refusal_score_harmless": float(refusal_score(base_harmless, ids).mean()),
            "refusal_rate_harmful": refusal_rate(m, tok, harm, sp)}
    print("base:", base, flush=True)

    rows = []
    for layer in parse_layers(a.layers):
        r_unit = pack["dirs"][layer]
        r_raw = r_unit * pack["raw_norm"][layer]
        t = time.perf_counter()
        with ablate(m, r_unit):
            abl_harm = first_token_logprobs(m, tok, harm, sp)
            abl_harmless = first_token_logprobs(m, tok, harmless, sp)
            rate = refusal_rate(m, tok, harm, sp)
        with add_direction(m, layer, r_raw):
            add_harmless = first_token_logprobs(m, tok, harmless, sp)
        row = {"layer": layer, "bypass": float(refusal_score(abl_harm, ids).mean()),
               "induce": float(refusal_score(add_harmless, ids).mean()),
               "kl": float(kl(base_harmless, abl_harmless).mean()),
               "refusal_rate_harmful_ablated": rate,
               "cohen_d_t402": float(pack["cohen_d"][layer]), "seconds": round(time.perf_counter() - t, 1)}
        rows.append(row)
        print(json.dumps(row), flush=True)

    chosen = choose(rows, L)
    t402 = int(pack["layer"])
    print(f"camada pela intervenção: {chosen}; pela separação (T-402): {t402}", flush=True)

    # S2 nos abliterados da T-908, nas duas camadas
    s2_rows = []
    layers_s2 = sorted({t402, chosen} - {None})
    for name in ("base", *DERIVATIVES):
        root = local_root() if name == "base" else data_dir() / "derivatives" / name
        if not root.exists():
            continue
        mm = b if name == "base" else load_model(root, dir_digest(root)[0])
        acts = {s: last_token_resid(mm.model, mm.tokenizer, P[s], sp, threads=a.threads) for s in ("harmful_val", "harmless_val")}
        rec = json.loads((root / "recipe.json").read_text())["recipe"] if name != "base" else None
        for layer in layers_s2:
            r = s2(acts["harmful_val"], acts["harmless_val"], {**pack, "layer": layer}).record()
            s2_rows.append({"model": name, "direction_layer_of_abliteration": rec["direction_layer"] if rec else None,
                            "read_layer": layer, "ratio": r["ratio"], "ratio_band": r["ratio_band"]})
    secs = time.perf_counter() - t0
    for r in s2_rows:
        print(json.dumps(r), flush=True)

    log.log("T-414", "chosen_layer", chosen, t402_layer=t402)
    doc = {
        "task": "T-414",
        "origem": "local, verificação de funcionamento; a decisão oficial é regerada na nuvem com o código congelado (T-312)",
        "run_id": log.run_id, "git_commit": log.commit, "dirty": log.dirty, "base_digest": digest,
        "direction_pack": str(pack_path.name), "condition": CONDITION,
        "regra": {"fonte": "Arditi et al. 2024, App. C", "kl_max": KL_MAX, "layer_max_fraction": LAYER_MAX_FRACTION,
                  "refusal_prefixes": list(REFUSAL_PREFIXES), "refusal_token_ids": ids,
                  "criterio": "menor bypass entre l < 0,8·L, induce > 0 e kl < 0,1"},
        "n": {"harmful_val": len(harm), "harmless_val": len(harmless)}, "max_new_tokens_detector": MAX_NEW_TOKENS,
        "base": base, "layers": rows, "chosen_layer": chosen, "t402_layer": t402, "s2": s2_rows,
        "seconds": round(secs, 1),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.with_suffix(".json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    lines = ["# Camada da direção pelo efeito da intervenção (T-414)", "",
             f"{doc['origem']}.", "",
             f"Base: recusa (detector) nos nocivos {base['refusal_rate_harmful']:.2f}; pontuação de recusa "
             f"nocivos {base['refusal_score_harmful']:.2f}, inócuos {base['refusal_score_harmless']:.2f}.", "",
             f"Regra: {doc['regra']['criterio']}. **Escolhida: {chosen}**; pela separação (T-402): {t402}.", "",
             "| Camada | bypass | induce | KL | recusa ablada | d de Cohen (T-402) | passa no filtro |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        ok = r["layer"] < LAYER_MAX_FRACTION * L and r["induce"] > 0 and r["kl"] < KL_MAX
        mark = " **←**" if r["layer"] == chosen else (" (T-402)" if r["layer"] == t402 else "")
        lines.append(f"| {r['layer']}{mark} | {r['bypass']:.2f} | {r['induce']:.2f} | {r['kl']:.3f} | "
                     f"{r['refusal_rate_harmful_ablated']:.2f} | {r['cohen_d_t402']:.2f} | {'sim' if ok else 'não'} |")
    lines += ["", "## S2 dos abliterados da T-908 lido em cada camada", "",
              "| Modelo | Camada da abliteração | Camada lida | ratio | ratio_band |", "|---|---|---|---|---|"]
    for r in s2_rows:
        lines.append(f"| {r['model']} | {r['direction_layer_of_abliteration'] or '-'} | {r['read_layer']} | "
                     f"{r['ratio']:.3f} | {r['ratio_band']:.3f} |")
    OUT.with_suffix(".md").write_text("\n".join(lines) + "\n")
    print(f"{secs:.0f} s ->", OUT.with_suffix(".md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
