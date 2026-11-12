import pytest
import torch

from model_gate.battery.pool import prompt_hash
from model_gate.signals.activations import last_token_resid
from model_gate.signals.direction import (auroc, candidate_layers, choose_layer, fit, load_direction,
                                          mean_diff, project, save_direction, unit)
from model_gate.signals.pairs import PairsMismatch, build_pairs, pair_texts
from model_gate.signals.s2 import s2
from model_gate.signals.s3 import ArchitectureMismatch, band, rank1_energy, s3, watched_names
from tests.tiny import PROMPTS, tiny_model, tiny_tokenizer

SIZES = {"train": 3, "val": 2}


def fake_texts():
    return {"harmful_train": ["h0", "h1", "H1 ", "h2", "h3", "s1 item"],
            "harmless_train": [f"n{i}" for i in range(6)],
            "harmful_val": ["h0", "v0", "v1", "v2"],
            "harmless_val": ["n0", "w0", "w1", "w2"]}


def test_pares_excluem_s1_repetidos_e_treino_na_validacao():
    texts = fake_texts()
    pairs = build_pairs(texts, {prompt_hash("s1 item")}, sizes=SIZES)
    got = pair_texts(pairs, texts)
    assert {k: len(v) for k, v in got.items()} == {"harmful_train": 3, "harmless_train": 3,
                                                    "harmful_val": 2, "harmless_val": 2}
    assert "s1 item" not in got["harmful_train"]
    hashes = [prompt_hash(t) for t in got["harmful_train"]]
    assert len(set(hashes)) == len(hashes)  # "h1" e "H1 " são o mesmo pedido
    assert not set(map(prompt_hash, got["harmful_val"])) & set(hashes)
    assert pairs == build_pairs(texts, {prompt_hash("s1 item")}, sizes=SIZES)  # seed fixa


def test_pares_conferem_hash_e_tamanho():
    texts = fake_texts()
    pairs = build_pairs(texts, set(), sizes=SIZES)
    texts["harmful_train"][pairs["splits"]["harmful_train"][0]["idx"]] = "outro texto"
    with pytest.raises(PairsMismatch):
        pair_texts(pairs, texts)
    with pytest.raises(ValueError):
        build_pairs(fake_texts(), set(), sizes={"train": 10, "val": 2})


def test_ativacoes_por_camada_no_ultimo_token():
    m, tok = tiny_model(), tiny_tokenizer()
    a = last_token_resid(m, tok, PROMPTS, None, threads=1)
    assert a.shape == (len(PROMPTS), m.config.num_hidden_layers, m.config.hidden_size)
    assert torch.equal(a, last_token_resid(m, tok, PROMPTS, None, threads=1))


def synthetic(seed=0, n=40, L=10, d=16, strong=6, sep=4.0):
    v = torch.randn(d, generator=torch.Generator().manual_seed(99))  # a mesma em treino e validação
    v = v / v.norm()
    g = torch.Generator().manual_seed(seed)
    harm, harmless = torch.randn(n, L, d, generator=g), torch.randn(n, L, d, generator=g)
    scale = torch.full((L,), 1.0)
    scale[strong] = sep
    harm = harm + scale.view(1, L, 1) * v.view(1, 1, d)
    return harm, harmless, v


def test_direcao_alinha_com_a_componente_plantada_e_escolhe_a_camada():
    harm, harmless, v = synthetic()
    hv, nv, _ = synthetic(seed=1)
    dirs, norm = unit(mean_diff(harm, harmless))
    assert torch.allclose(dirs.norm(dim=-1), torch.ones(10))
    assert float(dirs[6] @ v) > 0.95
    f = fit(harm, harmless, hv, nv)
    assert f["layer"] == 6 and float(f["auroc"][6]) > 0.99
    assert list(candidate_layers(24)) == list(range(4, 19))


def test_camada_sem_diferenca_vira_direcao_nula():
    harm, harmless, _ = synthetic()
    harm[:, 0], harmless[:, 0] = 1.0, 1.0  # camada 0: o mesmo token em todo prompt
    dirs, norm = unit(mean_diff(harm, harmless))
    assert float(norm[0]) == 0 and float(dirs[0].abs().sum()) == 0
    assert fit(harm, harmless, harm, harmless)["layer"] == 6


def test_camada_fora_da_faixa_nao_e_escolhida():
    d = torch.zeros(10)
    d[9], d[3] = 10.0, 1.0  # a camada final separa mais, mas fica fora (Arditi)
    assert choose_layer(d) == 3


def test_auroc():
    assert float(auroc(torch.tensor([[2.0], [3.0]]), torch.tensor([[0.0], [1.0]]))[0]) == 1.0
    assert float(auroc(torch.tensor([[1.0]]), torch.tensor([[1.0]]))[0]) == 0.5


def test_pacote_da_referencia_com_hash(tmp_path):
    harm, harmless, _ = synthetic()
    f = fit(harm, harmless, harm, harmless)
    sha = save_direction(tmp_path / "dir.safetensors", f, {"base_digest": "abc"})
    ref = load_direction(tmp_path / "dir.safetensors", sha)
    assert ref["layer"] == f["layer"] and ref["meta"]["base_digest"] == "abc"
    assert torch.equal(ref["dirs"], f["dirs"])
    with pytest.raises(ValueError):
        load_direction(tmp_path / "dir.safetensors", "0" * 64)
    assert save_direction(tmp_path / "outro.safetensors", f, {"base_digest": "abc"}) == sha  # estável
    assert save_direction(tmp_path / "outro.safetensors", f, {"base_digest": "xyz"}) != sha


def ablate(acts, dirs_unit):
    """Tira de cada camada a componente na direção (o que a abliteração faz)."""
    return acts - project(acts, dirs_unit).unsqueeze(-1) * dirs_unit.unsqueeze(0)


def test_s2_base_contra_si_mesmo_e_abliterado():
    harm, harmless, _ = synthetic()
    hv, nv, _ = synthetic(seed=1)
    ref = fit(harm, harmless, hv, nv)
    same = s2(hv, nv, ref)
    assert same.layer == 6 and same.ratio == pytest.approx(1.0) and same.ratio_band == pytest.approx(1.0)
    abl = s2(ablate(hv, ref["dirs"]), ablate(nv, ref["dirs"]), ref)
    assert abs(abl.ratio) < 1e-5 and abs(abl.ratio_band) < 1e-5
    assert len(same.gaps_by_layer) == 10


def test_s2_recusa_referencia_sem_separacao():
    harm, harmless, _ = synthetic()
    ref = fit(harm, harmless, harm, harmless)
    ref["gap_base"] = torch.zeros_like(ref["gap_base"])
    with pytest.raises(ValueError):
        s2(harm, harmless, ref)


def test_faixa_do_meio_de_hurtado():
    assert list(band(24)) == list(range(7, 17))  # ⌊0,33·24⌋ … ⌊0,67·24⌋, inclusive
    assert list(band(2)) == [0, 1]


def test_energia_rank1_sintetica():
    g = torch.Generator().manual_seed(0)
    u, v = torch.randn(48, 1, generator=g), torch.randn(1, 64, generator=g)
    r1 = (u @ v).double()
    assert rank1_energy(r1) == pytest.approx(1.0)
    noise = torch.randn(48, 64, generator=g).double()
    e = [rank1_energy(r1 + k * noise) for k in (0.01, 0.1, 1.0)]
    assert e[0] > e[1] > e[2]
    assert rank1_energy(torch.randn(256, 256, generator=g).double()) < 0.05  # posto cheio
    assert rank1_energy(torch.zeros(4, 4, dtype=torch.float64)) is None


def edited(sd, names, rank1=True, seed=1):
    g = torch.Generator().manual_seed(seed)
    out = dict(sd)
    for n in names:
        w = sd[n]
        dw = (torch.randn(w.shape[0], 1, generator=g) @ torch.randn(1, w.shape[1], generator=g)) if rank1 \
            else torch.randn(w.shape, generator=g)
        out[n] = w + 0.01 * dw
    return out


def test_s3_base_igual_abliterado_e_finetune():
    m = tiny_model()
    sd, L = m.state_dict(), m.config.num_hidden_layers
    same = s3(sd, sd, L)
    assert same.e1 == 0.0 and same.null_matrices == len(watched_names(L))
    abl = s3(sd, edited(sd, watched_names(L)), L)
    assert abl.e1 == pytest.approx(1.0) and abl.null_matrices == 0
    ft = s3(sd, edited(sd, watched_names(L), rank1=False), L)
    assert ft.e1 < 0.5
    other = s3(sd, edited(sd, ["model.layers.0.self_attn.q_proj.weight"]), L)  # fora das vigiadas
    assert other.e1 == 0.0


def test_s3_recusa_arquitetura_diferente():
    m = tiny_model()
    sd, L = m.state_dict(), m.config.num_hidden_layers
    bad = dict(sd)
    bad["model.layers.0.mlp.down_proj.weight"] = torch.zeros(3, 3)
    with pytest.raises(ArchitectureMismatch):
        s3(sd, bad, L)
    del bad["model.layers.0.mlp.down_proj.weight"]
    with pytest.raises(ArchitectureMismatch):
        s3(sd, bad, L)
