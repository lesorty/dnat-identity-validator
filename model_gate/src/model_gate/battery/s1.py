"""Geração do S1 (T-307, absorve a T-308): uma resposta gulosa por item, lida inteira (E14 §6.2).

- No depósito, o pai responde a todo o acervo público de nocivos e aos seguros do S1, em cada
  condição. As âncoras são os nocivos que ele recusa (refusal.is_refusal), e as respostas dele
  ficam na referência custodiada (T-312).
- No veredito, o derivado responde só ao que o sorteio escolhe: 32 âncoras públicas e 25 seguros
  por condição (T-302, T-303). A parte secreta (T-304) e os codificados (T-305) entram aqui quando
  existirem.

Os textos voltam ao chamador, que os guarda fora do git (T-211); o Juiz grava só IDs e métricas.
"""

from __future__ import annotations

from model_gate.battery.configs import FIXED_CONDITIONS, gen_config
from model_gate.battery.pool import by_category, safe_by_type
from model_gate.battery.refusal import is_refusal
from model_gate.battery.sample import draw_anchors, draw_safe, verdict_seed
from model_gate.io.generate import GenConfig, generate


def respond(model, tokenizer, prompts: dict[int, str], ids: list[int], condition: str,
            cfg: GenConfig | None = None) -> list[dict]:
    """Uma resposta por ID, na ordem dada, com a marca de recusa."""
    cfg = cfg or gen_config(condition)
    outs = generate(model, tokenizer, [prompts[i] for i in ids], cfg)
    return [{"id": i, "condition": condition, "text": o["text"], "n_tokens": o["n_tokens"],
             "refused": is_refusal(o["text"])} for i, o in zip(ids, outs)]


def parent_reference(model, tokenizer, harmful: dict[int, str], safe: dict[int, str],
                     conditions=FIXED_CONDITIONS, cfg_for=None, pool: dict | None = None) -> dict:
    """Respostas do pai a todo o acervo e as âncoras por categoria, em cada condição."""
    ref = {}
    for c in conditions:
        cfg = cfg_for(c) if cfg_for else None
        h = respond(model, tokenizer, harmful, sorted(harmful), c, cfg)
        s = respond(model, tokenizer, safe, sorted(safe), c, cfg)
        ref[c] = {"harmful": h, "safe": s,
                  "anchors": by_category([r["id"] for r in h if r["refused"]], pool)}
    return ref


def derivative_plan(ref: dict, key: bytes, derivative_digest: str, judge_version: str,
                    round_: int = 0, xstest: dict | None = None, n_anchors: int | None = None,
                    n_safe: int | None = None) -> dict:
    """O que o derivado responde em cada condição: as âncoras e os seguros sorteados."""
    plan = {}
    safe_groups = safe_by_type(xstest)
    for c, r in ref.items():
        kw_a = {"n": n_anchors} if n_anchors else {}
        kw_s = {"n": n_safe} if n_safe else {}
        plan[c] = {
            "anchors": draw_anchors(r["anchors"], verdict_seed(key, derivative_digest, c, judge_version, round_), **kw_a),
            "safe": draw_safe(safe_groups, verdict_seed(key, derivative_digest, f"{c}/xstest", judge_version, round_), **kw_s),
        }
    return plan


def derivative_responses(model, tokenizer, harmful: dict[int, str], safe: dict[int, str], plan: dict,
                         cfg_for=None) -> dict:
    """Respostas do derivado ao plano, por condição."""
    out = {}
    for c, p in plan.items():
        cfg = cfg_for(c) if cfg_for else None
        out[c] = {"anchors": respond(model, tokenizer, harmful, p["anchors"], c, cfg),
                  "safe": respond(model, tokenizer, safe, p["safe"], c, cfg)}
    return out
