"""Dispositivo de execução: CPU (padrão, D2) ou GPU, escolhido por MODEL_GATE_DISPOSITIVO.

    MODEL_GATE_DISPOSITIVO=cpu    (padrão) tudo como antes: float32 na CPU, threads fixas
    MODEL_GATE_DISPOSITIVO=cuda   modelos na GPU, ainda em float32, guloso e determinístico

Na GPU:
- CUBLAS_WORKSPACE_CONFIG=:4096:8 (exigido pelo cuBLAS para ser determinístico) e TF32 desligado, para
  que float32 seja float32 de verdade;
- só a geração e as passagens do modelo vão para a GPU. As contas dos sinais (direção do S2, ΔW e SVD do
  S3, arredondamento dos formatos) continuam na CPU, com o mesmo código, para não mudar de número com a
  placa;
- MODEL_GATE_DETERMINISMO=aviso troca o erro de uma operação sem versão determinística por um aviso (fica
  registrado em describe()); o padrão é exigir.

O dispositivo e a placa entram no registro de cada geração (GenConfig.record), para que um veredito diga
onde foi medido.
"""

from __future__ import annotations

import os

import torch

_CHOICES = ("cpu", "cuda")


def name() -> str:
    d = os.environ.get("MODEL_GATE_DISPOSITIVO", "cpu").strip().lower() or "cpu"
    if d not in _CHOICES:
        raise ValueError(f"MODEL_GATE_DISPOSITIVO={d!r}: use {_CHOICES}")
    return d


def strict() -> bool:
    return os.environ.get("MODEL_GATE_DETERMINISMO", "exigir") != "aviso"


_prepared = False


def device() -> torch.device:
    """O dispositivo escolhido, já preparado; falha se pediu GPU e não há."""
    global _prepared
    d = name()
    if d == "cuda":
        if not _prepared:
            os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
            if not torch.cuda.is_available():
                raise RuntimeError("MODEL_GATE_DISPOSITIVO=cuda, mas o torch não vê GPU "
                                   f"(torch {torch.__version__}, CUDA {torch.version.cuda})")
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True
            _prepared = True
        return torch.device("cuda", 0)
    return torch.device("cpu")


def deterministic() -> None:
    """torch.use_deterministic_algorithms conforme MODEL_GATE_DETERMINISMO."""
    if name() == "cuda":
        device()
    torch.use_deterministic_algorithms(True, warn_only=not strict())


def describe() -> dict:
    """O que gravar junto com cada medida."""
    d = name()
    out = {"device": d}
    if d == "cuda" and torch.cuda.is_available():
        p = torch.cuda.get_device_properties(0)
        out |= {"gpu": p.name, "gpu_mem_gb": round(p.total_memory / 2**30, 1), "cuda": torch.version.cuda,
                "determinismo": "exigir" if strict() else "aviso"}
    return out
