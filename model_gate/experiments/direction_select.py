"""Seleção da direção de recusa como em Arditi et al. (NeurIPS 2024), §2 e App. C (T-414).
VERIFICAÇÃO LOCAL no Qwen2.5-0.5B, não dado do artigo: a decisão oficial é regerada na nuvem com
o código congelado (T-312). Sem avaliador.

O procedimento do artigo, passo a passo:
1. Candidatos: a diferença de médias r_i^(l) entre nocivos e inócuos do TREINO (128 + 128), para
   cada posição pós-instrução i do template (no Qwen2.5, as 5 últimas) e cada camada l (resid_pre).
2. Validação filtrada (App. B): só os nocivos que o base recusa (refusal_metric > 0) e os inócuos
   que ele não recusa (refusal_metric < 0), dos 32 + 32.
3. Para cada candidato: bypass (refusal_metric médio nos nocivos com r̂ ablada de toda escrita no
   resíduo), induce (nos inócuos com r somada na entrada da camada l, em todas as posições) e kl
   (KL do último token nos inócuos, base × ablado).
4. Regra (App. C.1): menor bypass entre induce > 0, kl < 0,1 e l < 0,8·L.
refusal_metric = log p(R) − log(1 − p(R)) no primeiro token da resposta, R = {"I", "As"} (os tokens
de recusa do Qwen no artigo).

Desvio inevitável: o template do Qwen2.5 sempre traz um bloco de sistema; usa-se a condição
"vazio" (sistema vazio), a mesma em que o Juiz mede o S2. A Tabela 6 do artigo (Qwen 1) não tem
bloco de sistema.

Saída: results/T-414_arditi.{json,md}, com todos os candidatos, o escolhido (ou nenhum), a taxa
de recusa gerada com o escolhido ablado e o S2 dos abliterados da T-908 lido na direção escolhida.
    taskset -c 0-3 uv run python -m experiments.direction_select
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import torch

from experiments.data_dir import data_dir
from experiments.fetch_base import MANIFEST, local_root
from experiments.fetch_datasets import DATASETS
from experiments.fetch_datasets import local_root as dataset_root
from experiments.runlog import RunLog, new_run_id
from model_gate.battery.configs import gen_config
from model_gate.battery.refusal import is_refusal
from model_gate.io.generate import generate
from model_gate.io.load import dir_digest, load_model
from model_gate.signals.activations import last_token_resid, post_instruction_count, post_instruction_mean
from model_gate.signals.intervention import (KL_MAX, LAYER_MAX_FRACTION, REFUSAL_PREFIXES, ablate, add_direction,
                                             arditi_val_filter, choose_candidate, first_token_logprobs, kl,
                                             refusal_score, refusal_token_ids)
from model_gate.signals.pairs import load_pairs, pair_texts, read_splits

OUT = Path(__file__).resolve().parents[1] / "results" / "T-414_arditi"
CONDITION = "vazio"
MAX_NEW_TOKENS = 32
DERIVATIVES = ("fumaca-abl-d6-a1-todas", "fumaca-abl-d12-a1-todas")
T402_LAYER = 6


def refusal_rate(model, tok, prompts, sp) -> float:
    cfg = replace(gen_config(CONDITION), max_new_tokens=MAX_NEW_TOKENS, batch_size=8, system_prompt=sp)
    outs = generate(model, tok, prompts, cfg)
    return sum(is_refusal(o["text"]) for o in outs) / len(outs)


def gap(model, tok, harm, harmless, sp, r_unit, layer, threads) -> float:
    """Diferença das médias da projeção do último token em r̂, na camada `layer` (o gap do S2)."""
    ah = last_token_resid(model, tok, harm, sp, threads=threads)[:, layer]
    an = last_token_resid(model, tok, harmless, sp, threads=threads)[:, layer]
    return float((ah @ r_unit).mean() - (an @ r_unit).mean())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)

    digest = json.loads(MANIFEST.read_text())["digest"]
    P = pair_texts(load_pairs(), read_splits(dataset_root("refusal_direction", DATASETS["refusal_direction"])))
    sp = gen_config(CONDITION).system_prompt
    log = RunLog(new_run_id("t414a"), model_digest=digest)
    b = load_model(local_root(), digest)
    m, tok = b.model, b.tokenizer
    L = m.config.num_hidden_layers
    ids = refusal_token_ids(tok)
    n_pos = post_instruction_count(tok, sp)
    t0 = time.perf_counter()

    # 1. candidatos pelo treino
    mh = post_instruction_mean(m, tok, P["harmful_train"], sp, n_pos, a.threads)
    mn = post_instruction_mean(m, tok, P["harmless_train"], sp, n_pos, a.threads)
    R = mh - mn  # [n_pos, L, d]
    print(f"direções: {n_pos} posições × {L} camadas ({time.perf_counter() - t0:.0f} s)", flush=True)

    # 2. validação filtrada pelo base
    base_h = first_token_logprobs(m, tok, P["harmful_val"], sp)
    base_n = first_token_logprobs(m, tok, P["harmless_val"], sp)
    keep_h, keep_n = arditi_val_filter(refusal_score(base_h, ids), refusal_score(base_n, ids))
    harm = [p for p, k in zip(P["harmful_val"], keep_h.tolist()) if k]
    harmless = [p for p, k in zip(P["harmless_val"], keep_n.tolist()) if k]
    base_n_f = base_n[keep_n]
    base = {"n_harmful_val": len(P["harmful_val"]), "n_harmful_kept": len(harm),
            "n_harmless_val": len(P["harmless_val"]), "n_harmless_kept": len(harmless),
            "refusal_metric_harmful_kept": float(refusal_score(base_h[keep_h], ids).mean()) if harm else None,
            "refusal_metric_harmless_kept": float(refusal_score(base_n_f, ids).mean()) if harmless else None}
    print("validação filtrada:", base, flush=True)
    if len(harm) < 5 or len(harmless) < 5:
        print("validação filtrada pequena demais para selecionar", file=sys.stderr)
        return 1

    # 3. candidatos
    rows = []
    layers = [l for l in range(L) if l < LAYER_MAX_FRACTION * L]
    for i in range(n_pos):
        pos = i - n_pos  # −n_pos … −1
        for layer in layers:
            r_raw = R[i, layer]
            if float(r_raw.norm()) == 0.0:
                continue
            t = time.perf_counter()
            with ablate(m, r_raw / r_raw.norm()):
                abl_h = first_token_logprobs(m, tok, harm, sp)
                abl_n = first_token_logprobs(m, tok, harmless, sp)
            with add_direction(m, layer, r_raw):
                add_n = first_token_logprobs(m, tok, harmless, sp)
            row = {"pos": pos, "layer": layer, "bypass": float(refusal_score(abl_h, ids).mean()),
                   "induce": float(refusal_score(add_n, ids).mean()), "kl": float(kl(base_n_f, abl_n).mean()),
                   "norm": float(r_raw.norm()), "seconds": round(time.perf_counter() - t, 1)}
            rows.append(row)
            print(json.dumps(row), flush=True)

    # 4. regra
    best = choose_candidate(rows, L)
    print("escolhido:", best, flush=True)
    passing = [r for r in rows if r["induce"] > 0 and r["kl"] < KL_MAX]

    # leitura: recusa gerada com o escolhido ablado (e com a camada da T-402, posição −1) e S2
    check = {"base": refusal_rate(m, tok, P["harmful_val"], sp)}
    reads = ([("escolhido", best["pos"], best["layer"])] if best else []) + [("t402", -1, T402_LAYER)]
    for name, pos, layer in reads:
        r_raw = R[pos + n_pos, layer]
        with ablate(m, r_raw / r_raw.norm()):
            check[f"ablado_{name}"] = refusal_rate(m, tok, P["harmful_val"], sp)
    print("recusa gerada (32 nocivos):", check, flush=True)

    s2_rows = []
    for name, pos, layer in reads:
        r_unit = R[pos + n_pos, layer] / R[pos + n_pos, layer].norm()
        g0 = gap(m, tok, P["harmful_val"], P["harmless_val"], sp, r_unit, layer, a.threads)
        for d in DERIVATIVES:
            root = data_dir() / "derivatives" / d
            if not root.exists():
                continue
            mm = load_model(root, dir_digest(root)[0])
            g = gap(mm.model, mm.tokenizer, P["harmful_val"], P["harmless_val"], sp, r_unit, layer, a.threads)
            rec = json.loads((root / "recipe.json").read_text())["recipe"]
            s2_rows.append({"direcao": name, "pos": pos, "layer": layer, "model": d,
                            "direction_layer_of_abliteration": rec["direction_layer"], "gap_base": g0, "gap": g,
                            "ratio": g / g0})
            print(json.dumps(s2_rows[-1]), flush=True)
    secs = time.perf_counter() - t0

    log.log("T-414", "arditi_choice", best, n_passing=len(passing))
    doc = {"task": "T-414", "procedimento": "Arditi et al. 2024 (NeurIPS), §2.1, App. B (filtro) e App. C.1 (regra)",
           "origem": "local, verificação de funcionamento; a decisão oficial é regerada na nuvem com o código congelado",
           "run_id": log.run_id, "git_commit": log.commit, "dirty": log.dirty, "base_digest": digest,
           "condition": CONDITION, "desvio": "template do Qwen2.5 com bloco de sistema vazio; o artigo (Qwen 1) não tem",
           "refusal_prefixes": list(REFUSAL_PREFIXES), "refusal_token_ids": ids, "n_positions": n_pos,
           "regra": {"kl_max": KL_MAX, "layer_max_fraction": LAYER_MAX_FRACTION,
                     "criterio": "menor bypass entre induce > 0, kl < 0,1 e l < 0,8·L"},
           "validacao": base, "candidatos": rows, "passam_induce_e_kl": len(passing), "escolhido": best,
           "recusa_gerada": check, "s2": s2_rows, "seconds": round(secs, 1)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.with_suffix(".json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    top = sorted(rows, key=lambda r: r["bypass"])[:12]
    lines = ["# Direção de recusa pelo procedimento de Arditi et al. (T-414)", "",
             f"{doc['origem']}. Procedimento: {doc['procedimento']}. Desvio: {doc['desvio']}.", "",
             f"Validação filtrada pelo base: {base['n_harmful_kept']} de {base['n_harmful_val']} nocivos "
             f"(refusal_metric > 0) e {base['n_harmless_kept']} de {base['n_harmless_val']} inócuos (< 0).", "",
             f"Candidatos: {len(rows)} ({n_pos} posições × {len(layers)} camadas com l < 0,8·L). "
             f"Passam em induce > 0 e kl < 0,1: {len(passing)}.", "",
             ("**Escolhido: posição {pos}, camada {layer}** (bypass {bypass:.2f}, induce {induce:.2f}, kl {kl:.3f})."
              .format(**best)) if best else "**Nenhum candidato passa na regra.**", "",
             "## Os 12 candidatos de menor bypass", "",
             "| Posição | Camada | bypass | induce | KL | passa |", "|---|---|---|---|---|---|"]
    for r in top:
        ok = r["induce"] > 0 and r["kl"] < KL_MAX and r["layer"] < LAYER_MAX_FRACTION * L
        lines.append(f"| {r['pos']} | {r['layer']} | {r['bypass']:.2f} | {r['induce']:.2f} | {r['kl']:.3f} | {'sim' if ok else 'não'} |")
    lines += ["", "## Recusa gerada nos 32 nocivos (detector, 32 tokens)", "",
              "| Condição | Taxa |", "|---|---|"] + [f"| {k} | {v:.2f} |" for k, v in check.items()]
    lines += ["", "## S2 dos abliterados da T-908 na direção lida", "",
              "| Direção | Posição | Camada | Modelo | Camada da abliteração | razão do gap |", "|---|---|---|---|---|---|"]
    for r in s2_rows:
        lines.append(f"| {r['direcao']} | {r['pos']} | {r['layer']} | {r['model']} | {r['direction_layer_of_abliteration']} | {r['ratio']:.3f} |")
    OUT.with_suffix(".md").write_text("\n".join(lines) + "\n")
    print(f"{secs:.0f} s ->", OUT.with_suffix(".md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
