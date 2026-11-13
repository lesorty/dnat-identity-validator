"""Quantizar e desquantizar em CPU para os formatos liberados (T-501, absorve a T-502; D5, E14 §8).

Formalização por bloco de Egashira §3: o peso é cortado em blocos, cada bloco é dividido pelo seu
máximo absoluto (absmax) e cada valor vai para o código mais próximo de um alfabeto fixo. O Juiz e
o serviço usam o mesmo código: arredondam os pesos para o formato e fazem a conta em precisão
cheia, em CPU. Assim os pesos ficam idênticos aos do formato; só a precisão da conta muda, igual
nos dois lados (E14 §8).

Formatos (os mesmos parâmetros padrão do bitsandbytes, a referência; README de formats/, T-503):
    nf4   blocos de 64, alfabeto NF4 de 16 valores (QLoRA, quantis da normal)
    fp4   blocos de 64, alfabeto FP4 (e2m1 do bitsandbytes, normalizado para máximo 1)
    int8  LLM.int8 nos pesos: absmax por linha (vetorial), round(w · 127 / absmax)
    A decomposição de outliers do LLM.int8 é nas ativações, na hora da conta, e não muda os pesos
    guardados: fica fora daqui.

Arredondamento: o código mais próximo. No FP4 os empates exatos são comuns (pesos em bf16 dão
razões como 5/24, no meio de 1/6 e 1/4): sinal e magnitude separados, como no bitsandbytes, e a
magnitude desce no empate. O bitsandbytes desempata de outro jeito em parte desses empates (não
achamos a regra dele); NF4 e int8 batem bit a bit. A conferência com o
bitsandbytes está em experiments/check_quant_reference.py e no README de formats/.

Que matrizes: todas as nn.Linear, menos o lm_head, como o transformers faz ao carregar com o
bitsandbytes (as embeddings também ficam em precisão cheia).
"""

from __future__ import annotations

from dataclasses import dataclass

import torch

BLOCKSIZE_4BIT = 64

NF4_CODE = torch.tensor([
    -1.0, -0.6961928009986877, -0.5250730514526367, -0.39491748809814453, -0.28444138169288635,
    -0.18477343022823334, -0.09105003625154495, 0.0, 0.07958029955625534, 0.16093020141124725,
    0.24611230194568634, 0.33791524171829224, 0.44070982933044434, 0.5626170039176941, 0.7229568362236023, 1.0,
], dtype=torch.float32)

# e2m1 do bitsandbytes, dividido pelo máximo (6), por magnitude: 0, 1/192, 1/6, 1/4, 1/3, 1/2, 2/3, 1.
# O código de 4 bits é sinal (bit 3) + índice da magnitude (bits 0–2), como no bitsandbytes.
_FP4_POS = [0.0, 1 / 192, 1 / 6, 0.25, 1 / 3, 0.5, 2 / 3, 1.0]
FP4_TABLE = torch.tensor(_FP4_POS + [-v for v in _FP4_POS], dtype=torch.float64).to(torch.float32)
FP4_CODE = torch.tensor(sorted(set(_FP4_POS) | {-v for v in _FP4_POS}), dtype=torch.float64).to(torch.float32)


# Limiares de magnitude: |x| > limiar sobe de código. São os pontos médios exatos, levados a
# float32; no empate exato a magnitude desce. O bitsandbytes 0.50.2 desempata de outro jeito em
# parte dos empates (cerca de 0,05% dos pesos de um bf16; README de formats/).
FP4_THRESHOLDS = torch.tensor([(lo + hi) / 2 for lo, hi in zip(_FP4_POS, _FP4_POS[1:])],
                              dtype=torch.float64).to(torch.float32)

FORMATS = ("fp", "int8", "nf4", "fp4")
CODES = {"nf4": NF4_CODE, "fp4": FP4_TABLE}  # código de 4 bits -> valor
_NF4_MIDS = ((NF4_CODE.to(torch.float64)[1:] + NF4_CODE.to(torch.float64)[:-1]) / 2).to(torch.float32)


def _codes_4bit(scaled: torch.Tensor, fmt: str) -> torch.Tensor:
    if fmt == "nf4":
        # Código mais próximo; os pontos médios do NF4 não caem em razões exatas de bf16.
        return torch.bucketize(scaled, _NF4_MIDS, right=True).to(torch.uint8)
    mag = torch.bucketize(scaled.abs(), FP4_THRESHOLDS, right=False)
    return (mag + 8 * (scaled < 0).to(mag.dtype)).to(torch.uint8)


@dataclass(frozen=True)
class Quantized:
    """Pesos quantizados: índices no alfabeto (ou inteiros int8), escala por bloco e forma original."""
    fmt: str
    codes: torch.Tensor     # uint8 (4 bits: índice no alfabeto) ou int8
    absmax: torch.Tensor    # float32, um por bloco (4 bits) ou por linha (int8)
    shape: tuple[int, ...]
    blocksize: int | None


def _check(w: torch.Tensor) -> torch.Tensor:
    if not torch.is_floating_point(w):
        raise TypeError("só tensores de ponto flutuante")
    if not torch.isfinite(w).all():
        raise ValueError("peso não finito")
    return w.detach().to(torch.float32)


def quantize_4bit(w: torch.Tensor, fmt: str, blocksize: int = BLOCKSIZE_4BIT) -> Quantized:
    """Blocos de `blocksize` no tensor achatado (linha a linha), absmax por bloco, código mais próximo."""
    if fmt not in CODES:
        raise ValueError(f"formato de 4 bits desconhecido: {fmt!r}")
    x = _check(w).reshape(-1)
    n = x.numel()
    pad = (-n) % blocksize
    if pad:
        x = torch.cat([x, x.new_zeros(pad)])
    blocks = x.reshape(-1, blocksize)
    absmax = blocks.abs().amax(dim=1)
    scale = torch.where(absmax > 0, absmax, torch.ones_like(absmax))
    scaled = (blocks / scale[:, None]).clamp(-1.0, 1.0)
    idx = _codes_4bit(scaled, fmt)
    return Quantized(fmt, idx.reshape(-1)[:n], absmax, tuple(w.shape), blocksize)


def dequantize_4bit(q: Quantized) -> torch.Tensor:
    code = CODES[q.fmt]
    n = q.codes.numel()
    pad = (-n) % q.blocksize
    idx = torch.cat([q.codes, q.codes.new_zeros(pad)]) if pad else q.codes
    vals = code[idx.long()].reshape(-1, q.blocksize) * q.absmax[:, None]
    return vals.reshape(-1)[:n].reshape(q.shape)


def quantize_int8(w: torch.Tensor) -> Quantized:
    """LLM.int8 nos pesos: absmax por linha (a última dimensão é a entrada da nn.Linear)."""
    x = _check(w)
    if x.dim() != 2:
        raise ValueError("int8 vetorial pede uma matriz")
    absmax = x.abs().amax(dim=1)
    scale = torch.where(absmax > 0, absmax, torch.ones_like(absmax))
    q = torch.round(x * (127.0 / scale[:, None])).clamp(-127, 127).to(torch.int8)
    return Quantized("int8", q, absmax, tuple(x.shape), None)


def dequantize_int8(q: Quantized) -> torch.Tensor:
    return q.codes.to(torch.float32) * (q.absmax[:, None] / 127.0)


def quantize(w: torch.Tensor, fmt: str) -> Quantized:
    if fmt == "int8":
        return quantize_int8(w)
    if fmt in CODES:
        return quantize_4bit(w, fmt)
    raise ValueError(f"formato desconhecido: {fmt!r} (use {FORMATS})")


def dequantize(q: Quantized) -> torch.Tensor:
    return dequantize_int8(q) if q.fmt == "int8" else dequantize_4bit(q)


def round_trip(w: torch.Tensor, fmt: str) -> torch.Tensor:
    """O peso como o formato o guarda, de volta em precisão cheia (no dtype original)."""
    if fmt == "fp":
        return w.detach().clone()
    return dequantize(quantize(w, fmt)).to(w.dtype)


def quantize_model_(model: torch.nn.Module, fmt: str, skip: tuple[str, ...] = ("lm_head",)) -> list[str]:
    """Arredonda no lugar os pesos de toda nn.Linear do modelo, menos as de nome em `skip`.

    Devolve os nomes das matrizes arredondadas. Os vieses ficam em precisão cheia (como no
    bitsandbytes). "fp" não muda nada.
    """
    if fmt not in FORMATS:
        raise ValueError(f"formato desconhecido: {fmt!r} (use {FORMATS})")
    done = []
    if fmt == "fp":
        return done
    with torch.no_grad():
        for name, mod in model.named_modules():
            if isinstance(mod, torch.nn.Linear) and not any(name == s or name.endswith("." + s) for s in skip):
                mod.weight.copy_(round_trip(mod.weight, fmt))
                done.append(name)
    return done
