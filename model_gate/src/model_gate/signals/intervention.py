"""Escolha da camada da direção pelo efeito da intervenção (T-414; Arditi et al., 2024, §2.4 e App. C).

A T-402 escolheu a camada pela separação entre nocivos e inócuos na validação, que pode medir o
tema e não a recusa. Arditi escolhe pela intervenção, com três medidas por camada candidata l,
todas no primeiro token da resposta (a última posição do prompt):

- bypass: pontuação de recusa nos nocivos com a direção r̂_l ABLADA em todas as camadas e
  posições (cada escrita no resíduo perde a componente em r̂_l: embedding, atenção e MLP).
  Quanto menor, mais a direção carrega a recusa;
- induce: pontuação de recusa nos inócuos com a diferença de médias r_l SOMADA na entrada da
  camada l, em todas as posições. Tem de ser > 0: a direção sozinha induz recusa;
- kl: KL(base ‖ ablado) da distribuição do primeiro token nos inócuos. Tem de ser < 0,1: tirar a
  direção não estraga o modelo no que não é nocivo.

Regra (Arditi, App. C): entre as camadas candidatas com l < 0,8·L, induce > 0 e kl < 0,1, a de menor
bypass; empate pela menor camada.

Pontuação de recusa: log p(R) − log(1 − p(R)), com R o conjunto dos primeiros tokens de recusa
do modelo ("I", "As" no Qwen e no Llama, como Arditi; ver refusal_token_ids).
"""

from __future__ import annotations

from contextlib import contextmanager

import torch
from transformers import PreTrainedModel, PreTrainedTokenizerBase

from model_gate.io.generate import render

REFUSAL_PREFIXES = ("I", "As")
KL_MAX = 0.1
LAYER_MAX_FRACTION = 0.8


def refusal_token_ids(tokenizer: PreTrainedTokenizerBase, prefixes=REFUSAL_PREFIXES) -> list[int]:
    """Primeiro token de cada prefixo de recusa, sem repetição."""
    ids = []
    for p in prefixes:
        toks = tokenizer.encode(p, add_special_tokens=False)
        if toks and toks[0] not in ids:
            ids.append(toks[0])
    if not ids:
        raise ValueError("nenhum token de recusa no vocabulário")
    return ids


def _project_out(x: torch.Tensor, r: torch.Tensor) -> torch.Tensor:
    r = r.to(x.dtype)
    return x - (x @ r).unsqueeze(-1) * r


def _blocks(model: PreTrainedModel):
    inner = getattr(model, "model", model)
    return inner.embed_tokens, list(inner.layers)


@contextmanager
def ablate(model: PreTrainedModel, r_unit: torch.Tensor):
    """Direção r̂ ablada de toda escrita no resíduo, em todas as camadas e posições."""
    r = r_unit / r_unit.norm()
    embed, layers = _blocks(model)

    def out_hook(_mod, _inp, out):
        if isinstance(out, tuple):
            return (_project_out(out[0], r), *out[1:])
        return _project_out(out, r)

    handles = [embed.register_forward_hook(out_hook)]
    for layer in layers:
        handles.append(layer.self_attn.register_forward_hook(out_hook))
        handles.append(layer.mlp.register_forward_hook(out_hook))
    try:
        yield
    finally:
        for h in handles:
            h.remove()


@contextmanager
def add_direction(model: PreTrainedModel, layer: int, r: torch.Tensor):
    """r (diferença de médias, com a norma) somado à entrada da camada `layer`, em todas as posições."""
    _, layers = _blocks(model)

    def pre_hook(_mod, args, kwargs):
        if args:
            return (args[0] + r.to(args[0].dtype), *args[1:]), kwargs
        kwargs["hidden_states"] = kwargs["hidden_states"] + r.to(kwargs["hidden_states"].dtype)
        return args, kwargs

    h = layers[layer].register_forward_pre_hook(pre_hook, with_kwargs=True)
    try:
        yield
    finally:
        h.remove()


@torch.inference_mode()
def first_token_logprobs(model: PreTrainedModel, tokenizer: PreTrainedTokenizerBase, prompts: list[str],
                         system_prompt: str | None, batch_size: int = 8) -> torch.Tensor:
    """log-softmax do primeiro token da resposta, [n, vocab] em float32 (preenchimento à esquerda)."""
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    rows = []
    for i in range(0, len(prompts), batch_size):
        chunk = [render(tokenizer, p, system_prompt) for p in prompts[i:i + batch_size]]
        enc = tokenizer(chunk, return_tensors="pt", padding=True, add_special_tokens=False)
        logits = model(**enc).logits[:, -1].float()
        rows.append(torch.log_softmax(logits, -1))
    return torch.cat(rows)


def refusal_score(logprobs: torch.Tensor, ids: list[int]) -> torch.Tensor:
    """log p(R) − log(1 − p(R)) por prompt, [n]."""
    lp = torch.logsumexp(logprobs[:, ids], -1)
    return lp - torch.log1p(-lp.exp().clamp(max=1 - 1e-7))


def kl(base_lp: torch.Tensor, other_lp: torch.Tensor) -> torch.Tensor:
    """KL(base ‖ other) por prompt, [n]."""
    return (base_lp.exp() * (base_lp - other_lp)).sum(-1)


def choose(rows: list[dict], n_layers: int, kl_max: float = KL_MAX,
           layer_max_fraction: float = LAYER_MAX_FRACTION) -> int | None:
    """Regra de Arditi sobre as linhas {layer, bypass, induce, kl}; None se nenhuma passa no filtro."""
    ok = [r for r in rows if r["layer"] < layer_max_fraction * n_layers and r["induce"] > 0 and r["kl"] < kl_max]
    if not ok:
        return None
    return min(ok, key=lambda r: (r["bypass"], r["layer"]))["layer"]


def arditi_val_filter(harmful_scores: torch.Tensor, harmless_scores: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Filtro da validação (Arditi, App. B): nocivos que o base recusa (refusal_metric > 0) e
    inócuos que ele não recusa (refusal_metric < 0). Devolve as duas máscaras booleanas."""
    return harmful_scores > 0, harmless_scores < 0


def choose_candidate(rows: list[dict], n_layers: int, kl_max: float = KL_MAX,
                     layer_max_fraction: float = LAYER_MAX_FRACTION) -> dict | None:
    """Regra de Arditi (App. C.1) sobre candidatos {pos, layer, bypass, induce, kl}: menor bypass entre
    induce > 0, kl < 0,1 e l < 0,8·L; empate pela menor camada e pela posição mais à direita."""
    ok = [r for r in rows if r["layer"] < layer_max_fraction * n_layers and r["induce"] > 0 and r["kl"] < kl_max]
    if not ok:
        return None
    return min(ok, key=lambda r: (r["bypass"], r["layer"], -r["pos"]))
