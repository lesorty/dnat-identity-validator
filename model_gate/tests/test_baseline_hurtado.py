"""T-1301: linha de base de Hurtado (ρ, E1 e z-soma, sem custódia), com os casos publicados que
se reproduzem por construção (§5 e App. B)."""

import copy

import numpy as np
import pytest
import torch
from transformers import Qwen2Config, Qwen2ForCausalLM

from experiments.campaign.baseline_hurtado import SPLITS, VAL, ZSum, measure, signals
from model_gate.signals.activations import last_token_resid
from model_gate.signals.direction import fit
from model_gate.signals.s2 import s2
from model_gate.signals.s3 import band, s3, watched_names
from tests.tiny import SPECIALS, WORDS, tiny_model, tiny_tokenizer

N_LAYERS = 6  # faixa B = 1…4: quatro camadas, sem a camada 0


def model(seed=0):
    torch.manual_seed(seed)
    cfg = Qwen2Config(vocab_size=len(SPECIALS) + len(WORDS) + 1, hidden_size=32, intermediate_size=64,
                      num_hidden_layers=N_LAYERS, num_attention_heads=4, num_key_value_heads=2,
                      max_position_embeddings=128, eos_token_id=1, pad_token_id=0, tie_word_embeddings=False)
    return Qwen2ForCausalLM(cfg).eval()


HARM = ["w1 w2 w3", "w1 w4 w5", "w2 w3 w6 w1", "w1 w7"]
BENIGN = ["w30 w31", "w32 w30 w33", "w34 w35 w30", "w36 w30"]
# treino = validação: o gap da referência é a norma da diferença de médias, sempre positivo
TEXTS = {"harmful_train": HARM, "harmless_train": BENIGN, "harmful_val": HARM, "harmless_val": BENIGN}


def acts_of(m, tok, splits):
    return {s: last_token_resid(m, tok, TEXTS[s], None, threads=1) for s in splits}


def abliterate(m, basis):
    """Ortogonalização de pesos de Arditi: tira o subespaço de `basis` [d, k] (ortonormal) de tudo o
    que escreve no resíduo (embedding, o_proj e down_proj de todas as camadas)."""
    out = copy.deepcopy(m)
    P = basis @ basis.T
    with torch.no_grad():
        out.model.embed_tokens.weight -= out.model.embed_tokens.weight @ P
        for layer in out.model.layers:
            for w in (layer.self_attn.o_proj.weight, layer.mlp.down_proj.weight):
                w -= P @ w
    return out


@pytest.fixture(scope="module")
def tiny():
    m, tok = model(), tiny_tokenizer()
    dirs = fit(*acts_of(m, tok, SPLITS).values())["dirs"]  # direções na referência
    return m, tok, dirs


def test_rho_e_e1_sao_o_s2_da_faixa_e_o_s3(tiny):
    m, tok, _ = tiny
    cand = abliterate(m, torch.linalg.qr(torch.randn(32, 3, generator=torch.Generator().manual_seed(5))).Q)
    ra, ca = acts_of(m, tok, SPLITS), acts_of(cand, tok, VAL)
    got = signals(ra, ca, m.state_dict(), cand.state_dict(), N_LAYERS, "pai declarado")
    ref = fit(*(ra[s] for s in SPLITS))
    assert got.rho == s2(ca["harmful_val"], ca["harmless_val"], ref).ratio_band
    assert got.e1 == s3(m.state_dict(), cand.state_dict(), N_LAYERS).e1
    assert got.layers == list(band(N_LAYERS)) == [1, 2, 3, 4]
    assert got.record()["declared_reference"] == "pai declarado"


def test_derivado_como_propria_referencia_evade_por_construcao(tiny):
    """Hurtado §5: com o candidato como referência, ΔW = 0 e ρ = 1."""
    m, tok, _ = tiny
    r = measure((m, tok), (m, tok), TEXTS, None, 1, "o próprio derivado")
    assert r.rho == 1.0 and r.e1 == 0.0
    assert r.null_matrices == len(watched_names(N_LAYERS))


def test_abliteracao_nas_direcoes_da_referencia_zera_rho(tiny):
    """App. B: a remoção alinhada às direções de recusa leva ρ a ≈ 0. Tirando o subespaço das
    direções da faixa, o resíduo de entrada de cada camada da faixa fica ortogonal a r̂_ℓ."""
    m, tok, dirs = tiny
    basis = torch.linalg.qr(dirs[list(band(N_LAYERS))].T.double()).Q.float()
    r = measure((m, tok), (abliterate(m, basis), tok), TEXTS, None, 1, "base")
    assert abs(r.rho) < 1e-4
    assert r.null_matrices == 0 and r.e1 >= 1 / basis.shape[1]  # ΔW = P·W tem posto ≤ k


def test_abliteracao_de_uma_direcao_da_e1_igual_a_1(tiny):
    """WeightWatch: ΔW = r̂ r̂ᵀ W tem posto 1 em toda matriz vigiada."""
    m, tok, dirs = tiny
    r = measure((m, tok), (abliterate(m, dirs[2:3].T.contiguous()), tok), TEXTS, None, 1, "base")
    assert r.e1 == pytest.approx(1.0, abs=1e-6) and r.null_matrices == 0
    assert r.rho < 1.0


def test_referencia_forjada_derruba_o_escore(tiny):
    """RQ5: o mesmo abliterado, declarado contra o base honesto e contra si mesmo (sem custódia)."""
    m, tok, dirs = tiny
    basis = torch.linalg.qr(dirs[list(band(N_LAYERS))].T.double()).Q.float()
    abl = abliterate(m, basis)
    honest = measure((m, tok), (abl, tok), TEXTS, None, 1, "base")
    spoofed = measure((abl, tok), (abl, tok), TEXTS, None, 1, "o próprio abliterado")
    z = ZSum.fit([1.0, 0.95, 0.9, honest.rho], [0.0, 0.1, 0.2, honest.e1])  # população de brinquedo
    # forjada: idêntico a uma cópia intacta do base, o escore mais baixo possível
    assert (spoofed.rho, spoofed.e1) == (1.0, 0.0)
    assert z.score(spoofed.rho, spoofed.e1) == z.score(1.0, 0.0) < z.score(honest.rho, honest.e1)


def test_zsoma_contas_a_mao():
    z = ZSum.fit([1.0, 0.5, 0.0], [0.0, 0.5, 1.0])
    assert (z.mean_rho, z.sd_rho, z.mean_e1, z.sd_e1, z.n) == (0.5, 0.5, 0.5, 0.5, 3)
    assert np.allclose(z.score(np.array([1.0, 0.5, 0.0]), np.array([0.0, 0.5, 1.0])), [-2.0, 0.0, 2.0])
    # ρ menor e E1 maior: mais suspeito
    assert z.score(0.2, 0.5) > z.score(0.8, 0.5) and z.score(0.5, 0.9) > z.score(0.5, 0.1)
    with pytest.raises(ValueError):
        ZSum.fit([1.0, 1.0], [0.0, 1.0])  # desvio nulo
    with pytest.raises(ValueError):
        ZSum.fit([1.0], [0.0])
    with pytest.raises(ValueError):
        ZSum.fit([1.0, float("nan")], [0.0, 1.0])


def test_recusa_entradas_incompativeis(tiny):
    m, tok, _ = tiny
    ra = acts_of(m, tok, SPLITS)
    sd = m.state_dict()
    with pytest.raises(KeyError):
        signals(ra, {"harmful_val": ra["harmful_val"]}, sd, sd, N_LAYERS, "x")
    with pytest.raises(ValueError):
        signals(ra, {s: ra[s][:, :3] for s in VAL}, sd, sd, N_LAYERS, "x")
    with pytest.raises(ValueError):
        measure((m, tok), (tiny_model(), tok), TEXTS, None, 1, "x")  # 2 camadas contra 6
