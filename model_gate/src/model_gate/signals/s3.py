"""S3: energia rank-1 de ΔW nas matrizes vigiadas, contra o base custodiado (T-407, T-408; Hurtado).

Receita de Hurtado (2026, §3 e App. C), primitiva WeightWatch:

    ΔW_m = W_base,m − W_derivado,m
    E1   = média sobre m ∈ W de σ1²(ΔW_m) / Σ_i σi²(ΔW_m)   ∈ [0, 1]

com W = o_proj e down_proj de cada camada da faixa do meio B = ⌊0,33·L⌋ … ⌊0,67·L⌋
(inclusive). A abliteração é uma edição de posto 1 e leva E1 para perto de 1; um fine-tune
comum espalha a energia. E1 dispara em qualquer edição de posto baixo, inclusive benigna,
por isso é segunda linha (no máximo inconclusivo).

- Casamento pelo nome e pela forma; arquitetura diferente é recusada.
- ΔW nulo (matriz idêntica ao base) tem E1 = 0 e é contado à parte, sem dividir por zero.
- SVD em float64: ΔW pequenos (quantização) perdem precisão em float32.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import torch

BAND = (0.33, 0.67)
WATCHED = ("self_attn.o_proj.weight", "mlp.down_proj.weight")


class ArchitectureMismatch(ValueError):
    """Derivado e base não têm as mesmas matrizes vigiadas."""


def band(n_layers: int, frac: tuple[float, float] = BAND) -> range:
    """Faixa do meio de Hurtado: ⌊0,33·L⌋ … ⌊0,67·L⌋, inclusive."""
    return range(int(frac[0] * n_layers), int(frac[1] * n_layers) + 1)


def watched_names(n_layers: int, prefix: str = "model.layers") -> list[str]:
    return [f"{prefix}.{layer}.{w}" for layer in band(n_layers) for w in WATCHED]


def delta_weights(base: Mapping[str, torch.Tensor], derivative: Mapping[str, torch.Tensor],
                  n_layers: int) -> dict[str, torch.Tensor]:
    """ΔW = W_base − W_derivado nas matrizes vigiadas (T-407), em float64."""
    out = {}
    for name in watched_names(n_layers):
        if name not in base or name not in derivative:
            raise ArchitectureMismatch(f"matriz vigiada ausente: {name}")
        wb, wd = base[name], derivative[name]
        if wb.shape != wd.shape:
            raise ArchitectureMismatch(f"{name}: forma {tuple(wd.shape)} != base {tuple(wb.shape)}")
        out[name] = wb.detach().to(torch.float64) - wd.detach().to(torch.float64)
    return out


def rank1_energy(dw: torch.Tensor) -> float | None:
    """σ1² / Σσi²; None para ΔW nulo."""
    s = torch.linalg.svdvals(dw)
    total = float((s ** 2).sum())
    return None if total == 0.0 else float(s[0] ** 2) / total


@dataclass(frozen=True)
class S3Result:
    layers: list[int]
    per_matrix: dict[str, float]  # E1 por matriz (0 nas nulas)
    e1: float                     # média de Hurtado sobre as matrizes da faixa
    e1_max: float                 # só para leitura
    null_matrices: int            # matrizes idênticas ao base

    def record(self) -> dict:
        return {"layers": [self.layers[0], self.layers[-1]], "e1": self.e1, "e1_max": self.e1_max,
                "null_matrices": self.null_matrices, "matrices": len(self.per_matrix)}


def s3(base: Mapping[str, torch.Tensor], derivative: Mapping[str, torch.Tensor], n_layers: int) -> S3Result:
    """E1 do derivado contra o base (T-408). base e derivative: state_dict dos dois modelos."""
    dws = delta_weights(base, derivative, n_layers)
    energies = {k: rank1_energy(v) for k, v in dws.items()}
    per = {k: (0.0 if e is None else e) for k, e in energies.items()}
    vals = list(per.values())
    return S3Result(list(band(n_layers)), per, sum(vals) / len(vals), max(vals),
                    sum(e is None for e in energies.values()))
