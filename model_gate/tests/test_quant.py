"""T-501: quantizar e desquantizar por bloco em CPU, com tensores pequenos e valores conhecidos."""

import pytest
import torch

from model_gate.formats.quant import (BLOCKSIZE_4BIT, FP4_CODE, FP4_TABLE, FP4_THRESHOLDS, NF4_CODE, dequantize,
                                      quantize, quantize_model_, round_trip)
from tests.tiny import tiny_model


def test_alfabetos():
    assert len(NF4_CODE) == 16 and NF4_CODE[0] == -1 and NF4_CODE[-1] == 1 and 0.0 in NF4_CODE
    assert torch.all(NF4_CODE[1:] > NF4_CODE[:-1])
    assert len(FP4_TABLE) == 16 and set(FP4_CODE.tolist()) == set(FP4_TABLE.tolist())
    assert FP4_TABLE[:8].tolist() == pytest.approx([0, 1 / 192, 1 / 6, 1 / 4, 1 / 3, 1 / 2, 2 / 3, 1])
    assert len(FP4_THRESHOLDS) == 7


@pytest.mark.parametrize("fmt,code", [("nf4", NF4_CODE), ("fp4", FP4_CODE)])
def test_os_proprios_codigos_voltam_exatos(fmt, code):
    """Um bloco de absmax 1 com os valores do alfabeto volta igual."""
    w = code.repeat(BLOCKSIZE_4BIT // len(code) + 1)[:BLOCKSIZE_4BIT].clone()
    w[0] = 1.0
    assert torch.equal(round_trip(w, fmt), w)


@pytest.mark.parametrize("fmt", ["nf4", "fp4"])
def test_escala_por_bloco_e_codigo_mais_proximo(fmt):
    code = NF4_CODE if fmt == "nf4" else FP4_CODE
    g = torch.Generator().manual_seed(0)
    w = torch.randn(4, 96, generator=g) * torch.tensor([[0.01], [1.0], [5.0], [100.0]])
    out = round_trip(w, fmt)
    blocks, oblocks = w.reshape(-1, 64), out.reshape(-1, 64)
    for b, o in zip(blocks, oblocks):
        am = b.abs().max()
        assert o.abs().max() == pytest.approx(am)              # o máximo do bloco é exato (código ±1)
        dist = (b[:, None] / am - code[None, :]).abs()
        best = dist.min(dim=1).values
        got = (o / am - b / am).abs()
        assert torch.allclose(got, best, atol=1e-6)             # sempre o código mais próximo


def test_bloco_parcial_e_bloco_zero():
    w = torch.zeros(70)
    w[64:] = torch.tensor([0.5, -1.0, 0.25, 0.0, 0.75, -0.1])
    for fmt in ("nf4", "fp4"):
        out = round_trip(w, fmt)
        assert out.shape == w.shape and torch.all(out[:64] == 0)  # absmax 0: o bloco fica zero
        assert out[65] == -1.0


def test_desempate_do_fp4_desce_a_magnitude():
    w = torch.zeros(64)
    w[0] = 1.0
    w[1] = 5 / 24          # meio exato de 1/6 e 1/4
    w[2] = -5 / 24
    w[3] = 0.4166666666    # perto do meio de 1/3 e 1/2, abaixo
    out = round_trip(w, "fp4")
    assert out[1].item() == pytest.approx(1 / 6) and out[2].item() == pytest.approx(-1 / 6)
    assert out[3].item() == pytest.approx(1 / 3)


def test_int8_por_linha():
    w = torch.tensor([[1.0, -0.5, 0.25, 0.0], [10.0, 3.3, -7.1, 0.01], [0.0, 0.0, 0.0, 0.0]])
    q = quantize(w, "int8")
    assert q.codes.dtype == torch.int8 and q.codes[0].tolist() == [127, -64, 32, 0]  # round(-63.5) = -64
    assert q.codes[1, 0] == 127 and q.codes[1, 3] == 0
    out = dequantize(q)
    assert torch.all(out[2] == 0)
    assert torch.all((out - w).abs() <= w.abs().amax(dim=1, keepdim=True) / 254 + 1e-7)  # meio passo
    with pytest.raises(ValueError):
        quantize(torch.ones(3), "int8")


def test_dtype_e_erros():
    w = torch.randn(8, 64, dtype=torch.bfloat16)
    assert round_trip(w, "nf4").dtype == torch.bfloat16
    assert torch.equal(round_trip(w, "fp"), w)
    with pytest.raises(ValueError):
        quantize(w, "gguf")
    with pytest.raises(ValueError):
        quantize(torch.tensor([1.0, float("nan")]), "nf4")
    with pytest.raises(TypeError):
        quantize(torch.ones(4, dtype=torch.int32), "nf4")


def test_quantize_model_arredonda_as_lineares_menos_lm_head():
    model = tiny_model()
    before = {n: p.detach().clone() for n, p in model.named_parameters()}
    done = quantize_model_(model, "nf4")
    assert done and all("lm_head" not in n for n in done)
    params = dict(model.named_parameters())
    for name in done:
        w = params[f"{name}.weight"]
        assert torch.equal(w, round_trip(before[f"{name}.weight"], "nf4"))
        if f"{name}.bias" in params:
            assert torch.equal(params[f"{name}.bias"], before[f"{name}.bias"])
    for n, p in params.items():
        if not any(n == f"{d}.weight" for d in done):
            assert torch.equal(p, before[n]), n
    # idempotente: arredondar de novo não muda
    again = {n: p.detach().clone() for n, p in model.named_parameters()}
    quantize_model_(model, "nf4")
    assert all(torch.equal(p, again[n]) for n, p in model.named_parameters())
    assert quantize_model_(model, "fp") == []
    with pytest.raises(ValueError):
        quantize_model_(model, "q8")
