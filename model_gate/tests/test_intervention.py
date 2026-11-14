"""T-414: ganchos de intervenção, pontuação de recusa e regra de Arditi no Qwen2 minúsculo."""

import math

import torch

from experiments.population.abliterate import AblationRecipe, abliterate_tensors
from model_gate.signals.intervention import (ablate, add_direction, choose, first_token_logprobs, kl,
                                             refusal_score, refusal_token_ids)
from tests.tiny import PROMPTS, tiny_model, tiny_tokenizer

D, L = 32, 2


def unit(seed):
    v = torch.randn(D, generator=torch.Generator().manual_seed(seed), dtype=torch.float64)
    return (v / v.norm()).float()


def test_ablacao_por_gancho_igual_a_ortogonalizacao_dos_pesos():
    """O gancho e a abliteração por pesos (α = 1, todas as camadas, embedding) são a mesma intervenção."""
    tok = tiny_tokenizer()
    m = tiny_model(0)
    r = unit(3)
    with ablate(m, r):
        hooked = first_token_logprobs(m, tok, PROMPTS, None, batch_size=2)
    edited, _ = abliterate_tensors(m.state_dict(), r, AblationRecipe("t", 0, (0, 1), 1.0, True), L)
    m2 = tiny_model(0)
    m2.load_state_dict(edited)
    weights = first_token_logprobs(m2, tok, PROMPTS, None, batch_size=2)
    assert torch.allclose(hooked, weights, atol=1e-4)
    # e os ganchos saem: o modelo volta a ser o base
    assert torch.allclose(first_token_logprobs(m, tok, PROMPTS, None), first_token_logprobs(tiny_model(0), tok, PROMPTS, None), atol=1e-5)


def test_resultado_nao_depende_do_lote():
    tok = tiny_tokenizer()
    m = tiny_model(0)
    a = first_token_logprobs(m, tok, PROMPTS, None, batch_size=1)
    b = first_token_logprobs(m, tok, PROMPTS, None, batch_size=4)
    assert torch.allclose(a, b, atol=1e-4)


def test_somar_a_direcao_muda_a_saida_e_zero_nao_muda():
    tok = tiny_tokenizer()
    m = tiny_model(0)
    base = first_token_logprobs(m, tok, PROMPTS, None)
    with add_direction(m, 1, torch.zeros(D)):
        same = first_token_logprobs(m, tok, PROMPTS, None)
    with add_direction(m, 1, 5 * unit(4)):
        moved = first_token_logprobs(m, tok, PROMPTS, None)
    assert torch.allclose(base, same, atol=1e-6)
    assert float(kl(base, moved).mean()) > 1e-3
    assert torch.allclose(kl(base, base), torch.zeros(len(PROMPTS)), atol=1e-6)


def test_pontuacao_de_recusa():
    lp = torch.log(torch.tensor([[0.5, 0.25, 0.25], [0.1, 0.1, 0.8]]))
    s = refusal_score(lp, [0, 1])
    assert math.isclose(float(s[0]), math.log(0.75 / 0.25), rel_tol=1e-5)
    assert math.isclose(float(s[1]), math.log(0.2 / 0.8), rel_tol=1e-5)
    tok = tiny_tokenizer()
    assert refusal_token_ids(tok, ("w1", "w2", "w1")) == [tok.convert_tokens_to_ids("w1"), tok.convert_tokens_to_ids("w2")]


def test_regra_de_arditi():
    rows = [
        {"layer": 2, "bypass": -5.0, "induce": -1.0, "kl": 0.01},  # não induz recusa
        {"layer": 4, "bypass": -3.0, "induce": 2.0, "kl": 0.5},    # estraga os inócuos
        {"layer": 6, "bypass": -1.0, "induce": 1.0, "kl": 0.05},
        {"layer": 8, "bypass": -2.0, "induce": 1.0, "kl": 0.05},   # escolhida
        {"layer": 9, "bypass": -2.0, "induce": 1.0, "kl": 0.05},   # empate: fica a menor
        {"layer": 20, "bypass": -9.0, "induce": 1.0, "kl": 0.01},  # ≥ 0,8·L
    ]
    assert choose(rows, 24) == 8
    assert choose(rows[:2], 24) is None


def test_arditi_val_filter_and_choose_candidate():
    import torch
    from model_gate.signals.intervention import arditi_val_filter, choose_candidate
    h, s = arditi_val_filter(torch.tensor([1.0, -0.5, 0.2]), torch.tensor([-3.0, 0.4]))
    assert h.tolist() == [True, False, True] and s.tolist() == [True, False]
    rows = [{"pos": -1, "layer": 10, "bypass": -5.0, "induce": 0.5, "kl": 0.05},
            {"pos": -2, "layer": 9, "bypass": -6.0, "induce": -0.1, "kl": 0.05},   # induce ≤ 0
            {"pos": -3, "layer": 8, "bypass": -7.0, "induce": 1.0, "kl": 0.2},     # kl alto
            {"pos": -1, "layer": 20, "bypass": -9.0, "induce": 1.0, "kl": 0.01},   # l ≥ 0,8·L
            {"pos": -4, "layer": 11, "bypass": -5.5, "induce": 0.1, "kl": 0.09}]
    assert choose_candidate(rows, 24) == rows[4]
    assert choose_candidate(rows[1:4], 24) is None
