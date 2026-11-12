import json

import pytest
import torch
from safetensors.torch import load_file

from experiments.population.abliterate import (EMBED, AblationRecipe, abliterate, orthogonalize_embed,
                                               orthogonalize_out)
from experiments.population.make_abliterated import parse_recipe
from model_gate.io.load import dir_digest, load_model
from model_gate.signals.direction import save_direction
from tests.tiny import PROMPTS, save_tiny, tiny_tokenizer

D, L = 32, 2  # d_model e camadas do Qwen2 minúsculo


def unit_dir(seed, dtype=torch.float32):
    g = torch.Generator().manual_seed(seed)
    v = torch.randn(D, generator=g, dtype=torch.float64)
    return (v / v.norm()).to(dtype)


@pytest.fixture
def setup(tmp_path):
    root = save_tiny(tmp_path / "base")
    digest = dir_digest(root)[0]
    dirs = torch.stack([unit_dir(1), unit_dir(2)])
    fitted = {"dirs": dirs, "raw_norm": torch.ones(L), "gap_base": torch.ones(L), "cohen_d": torch.ones(L),
              "auroc": torch.ones(L), "layer": 1}
    pack = tmp_path / "dirs.safetensors"
    sha = save_direction(pack, fitted, {"base_digest": digest})
    return root, digest, pack, sha, dirs


def recipe(**kw):
    base = dict(name="t", direction_layer=1, layers=(0, 1), scale=1.0, embedding=True)
    return AblationRecipe(**{**base, **kw})


def test_formulas_tiram_a_fracao_alpha_da_projecao():
    r = unit_dir(3, torch.float64)
    w = torch.randn(D, 7, dtype=torch.float64)
    e = torch.randn(11, D, dtype=torch.float64)
    assert torch.allclose(r @ orthogonalize_out(w, r, 1.0), torch.zeros(7, dtype=torch.float64), atol=1e-12)
    assert torch.allclose(r @ orthogonalize_out(w, r, 0.5), 0.5 * (r @ w))
    assert torch.allclose(orthogonalize_embed(e, r, 1.0) @ r, torch.zeros(11, dtype=torch.float64), atol=1e-12)
    # só a componente em r̂ muda: o complemento ortogonal fica igual
    p = torch.eye(D, dtype=torch.float64) - torch.outer(r, r)
    assert torch.allclose(p @ orthogonalize_out(w, r, 0.7), p @ w)
    assert torch.linalg.matrix_rank(w - orthogonalize_out(w, r, 0.7)) == 1  # edição de posto 1 (S3)


def test_receita_invalida():
    for kw in ({"scale": 0.0}, {"scale": 1.5}, {"layers": (), "embedding": False}, {"layers": (1, 0)}):
        with pytest.raises(ValueError):
            recipe(**kw)
    with pytest.raises(SystemExit):
        parse_recipe({"name": "x", "direction": {}, "direction_layer": 1, "layers": "all", "scale": 1.0}, L)
    r, _ = parse_recipe({"name": "x", "direction": {}, "direction_layer": 1, "layers": "all", "scale": 1,
                         "embedding": True}, L)
    assert r.layers == (0, 1)


def test_residuo_sem_direcao_em_todas_as_camadas(setup, tmp_path):
    """Receita completa (todas as camadas + embedding, α = 1): o resíduo nunca tem componente em r̂."""
    root, digest, pack, sha, dirs = setup
    res = abliterate(root, digest, pack, sha, recipe(), tmp_path / "d")
    assert res.max_residual < 1e-6
    d = load_model(tmp_path / "d", res.digest)
    b = load_model(root, digest)
    r = dirs[1]
    enc = tiny_tokenizer()(PROMPTS[2], return_tensors="pt", add_special_tokens=False)
    with torch.no_grad():
        hd = d.model(**enc, output_hidden_states=True).hidden_states
        hb = b.model(**enc, output_hidden_states=True).hidden_states
    for layer in range(L):  # resid_pre de cada bloco, todas as posições
        assert float((hd[layer] @ r).abs().max()) < 1e-5
        assert float((hb[layer] @ r).abs().max()) > 1e-3  # no base a componente existe


def test_so_as_matrizes_da_receita_mudam_e_digest_estavel(setup, tmp_path):
    root, digest, pack, sha, _ = setup
    a = abliterate(root, digest, pack, sha, recipe(layers=(1,), scale=0.5, embedding=False), tmp_path / "a")
    b = abliterate(root, digest, pack, sha, recipe(layers=(1,), scale=0.5, embedding=False), tmp_path / "b")
    assert a.digest == b.digest  # mesma receita, mesmo derivado
    c = abliterate(root, digest, pack, sha, recipe(layers=(1,), scale=1.0, embedding=False), tmp_path / "c")
    assert c.digest != a.digest
    wb, wa = load_file(str(root / "model.safetensors")), load_file(str(tmp_path / "a" / "model.safetensors"))
    changed = sorted(k for k in wb if not torch.equal(wb[k], wa[k]))
    assert changed == ["model.layers.1.mlp.down_proj.weight", "model.layers.1.self_attn.o_proj.weight"]
    assert EMBED not in changed
    rec = json.loads((tmp_path / "a" / "recipe.json").read_text())
    assert rec["recipe"]["scale"] == 0.5 and rec["base_digest"] == digest and rec["direction_sha256"] == sha


def test_recusa_pacote_ou_base_errados(setup, tmp_path):
    root, digest, pack, sha, _ = setup
    with pytest.raises(ValueError):
        abliterate(root, digest, pack, "0" * 64, recipe(), tmp_path / "x")  # hash do pacote
    with pytest.raises(RuntimeError):
        abliterate(root, "0" * 64, pack, sha, recipe(), tmp_path / "y")  # digest do base
    with pytest.raises(ValueError):
        abliterate(root, digest, pack, sha, recipe(layers=(0, 5)), tmp_path / "z")  # camada inexistente
