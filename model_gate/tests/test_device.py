"""Dispositivo configurável (model_gate.io.device): CPU por padrão, GPU só quando pedida e presente."""
import pytest
import torch

from model_gate.io import device as dev
from model_gate.io.generate import GenConfig


def test_padrao_e_cpu_e_vai_para_o_registro(monkeypatch):
    monkeypatch.delenv("MODEL_GATE_DISPOSITIVO", raising=False)
    assert dev.name() == "cpu" and dev.device() == torch.device("cpu")
    rec = GenConfig().record()
    assert rec["device"] == "cpu" and rec["dtype"] == "float32"


def test_valor_invalido_e_erro(monkeypatch):
    monkeypatch.setenv("MODEL_GATE_DISPOSITIVO", "tpu")
    with pytest.raises(ValueError, match="MODEL_GATE_DISPOSITIVO"):
        dev.name()


@pytest.mark.skipif(torch.cuda.is_available(), reason="só faz sentido sem GPU")
def test_pedir_gpu_sem_gpu_falha_claro(monkeypatch):
    monkeypatch.setenv("MODEL_GATE_DISPOSITIVO", "cuda")
    monkeypatch.setattr(dev, "_prepared", False)
    with pytest.raises(RuntimeError, match="não vê GPU"):
        dev.device()


def test_referencia_de_outro_dispositivo_e_recusada(monkeypatch):
    """O pai medido na GPU não serve para o derivado na CPU (e vice-versa): as medidas mudariam pela placa."""
    from model_gate import stages

    class M:
        inputs = {"base": {"digest": "b"}}

    class S:
        formats, conditions, max_new_tokens = ("fp",), ("vazio",), 8

    class E:
        judge_id = "j"

    rs = stages.RealStages()
    monkeypatch.setattr(rs, "_battery", lambda m: None)
    monkeypatch.setattr(stages, "battery_sha256", lambda b: "x")
    ref = {"base_digest": "b", "formats": ["fp"], "conditions": ["vazio"], "settings": {"max_new_tokens": 8},
           "judge_id": "j", "battery_sha256": "x"}
    monkeypatch.delenv("MODEL_GATE_DISPOSITIVO", raising=False)
    rs._check_reference(M(), ref, S(), E())                      # CPU com CPU: passa
    with pytest.raises(ValueError, match="referência medida em cuda"):
        rs._check_reference(M(), {**ref, "device": "cuda"}, S(), E())
