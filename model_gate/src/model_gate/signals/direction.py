"""Direção de recusa por camada no base custodiado (T-402, absorve T-403 e T-404).

- Direção: média(nocivos) − média(inócuos) por camada, nos pares de treino (Arditi);
  guarda-se a unitária e a norma bruta.
- Escolha da camada (critério fixado antes de ver qualquer derivado, R14): entre as camadas
  do meio, de ⌊0,2·L⌋ a ⌊0,8·L⌋ − 1 (Arditi descarta as finais, perto do unembedding), a de
  maior d de Cohen da projeção na validação; empate pela menor camada. O AUROC vai junto,
  só para leitura.
- Pacote da referência: direções, normas, gap do base na validação e metadados num
  safetensors; o SHA-256 do arquivo entra na referência do pai e no recibo (T-608).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import torch
from safetensors.torch import load_file, save_file

LAYER_RANGE = (0.2, 0.8)


def mean_diff(harmful: torch.Tensor, harmless: torch.Tensor) -> torch.Tensor:
    """[n, L, d] × [m, L, d] -> [L, d]."""
    return harmful.mean(0) - harmless.mean(0)


def unit(dirs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Unitárias por camada. Camada sem diferença (a 0, onde o último token é o mesmo token do
    template em todo prompt) fica com direção nula e nunca é candidata."""
    norm = dirs.norm(dim=-1)
    return torch.where(norm.unsqueeze(-1) > 0, dirs / norm.clamp_min(1e-30).unsqueeze(-1), 0.0), norm


def project(acts: torch.Tensor, dirs_unit: torch.Tensor) -> torch.Tensor:
    """[n, L, d] · [L, d] -> [n, L]."""
    return (acts * dirs_unit.unsqueeze(0)).sum(-1)


def cohen_d(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """d de Cohen por coluna: [n, L] × [m, L] -> [L], variância combinada."""
    na, nb = a.shape[0], b.shape[0]
    pooled = ((na - 1) * a.var(0) + (nb - 1) * b.var(0)) / (na + nb - 2)
    return (a.mean(0) - b.mean(0)) / pooled.clamp_min(1e-12).sqrt()


def auroc(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """P(a > b) + ½P(a = b) por coluna (Mann–Whitney)."""
    diff = a.unsqueeze(1) - b.unsqueeze(0)  # [na, nb, L]
    return ((diff > 0).float() + 0.5 * (diff == 0).float()).mean((0, 1))


def candidate_layers(n_layers: int, layer_range: tuple[float, float] = LAYER_RANGE) -> range:
    lo, hi = int(layer_range[0] * n_layers), int(layer_range[1] * n_layers)
    return range(lo, hi)


def choose_layer(d: torch.Tensor, layer_range: tuple[float, float] = LAYER_RANGE) -> int:
    cands = candidate_layers(d.shape[0], layer_range)
    return max(cands, key=lambda layer: (float(d[layer]), -layer))


def fit(harm_train, harmless_train, harm_val, harmless_val) -> dict:
    """Direção, escolha da camada e gap do base: tudo o que a T-402 grava."""
    dirs_unit, norm = unit(mean_diff(harm_train, harmless_train))
    ph, pn = project(harm_val, dirs_unit), project(harmless_val, dirs_unit)
    d = cohen_d(ph, pn)
    return {"dirs": dirs_unit, "raw_norm": norm, "cohen_d": d, "auroc": auroc(ph, pn),
            "gap_base": ph.mean(0) - pn.mean(0), "layer": choose_layer(d)}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def content_sha256(tensors: dict[str, torch.Tensor], meta: dict | None = None) -> str:
    """Hash do conteúdo, estável entre gravações: nome, dtype, forma e bytes de cada tensor em
    ordem de nome, e os metadados em JSON canônico. O hash do arquivo não serve, porque o
    safetensors grava os metadados sem ordem fixa."""
    h = hashlib.sha256()
    for k in sorted(tensors):
        t = tensors[k].detach().cpu().contiguous()
        h.update(f"{k}\0{t.dtype}\0{list(t.shape)}\0".encode())
        h.update(t.numpy().tobytes())
    h.update(json.dumps(meta or {}, sort_keys=True, ensure_ascii=False).encode())
    return h.hexdigest()


TENSORS = ("dirs", "raw_norm", "gap_base", "cohen_d", "auroc")


def save_direction(path: Path, fitted: dict, meta: dict) -> str:
    """Grava o pacote e devolve o hash do conteúdo (content_sha256)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tensors = {k: fitted[k].contiguous() for k in TENSORS}
    meta = {**meta, "layer": fitted["layer"]}
    save_file(tensors, str(path), metadata={"meta": json.dumps(meta, sort_keys=True)})
    return content_sha256(tensors, meta)


def load_direction(path: Path, expected_sha256: str | None = None) -> dict:
    from safetensors import safe_open

    with safe_open(str(path), framework="pt") as f:
        meta = json.loads(f.metadata()["meta"])
    tensors = load_file(str(path))
    if expected_sha256 is not None and content_sha256(tensors, meta) != expected_sha256:
        raise ValueError(f"{path}: hash não bate com a referência custodiada")
    return {**tensors, "meta": meta, "layer": meta["layer"]}
