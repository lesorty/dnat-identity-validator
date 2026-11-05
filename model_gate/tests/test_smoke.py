"""Fumaça do ambiente (T-202): importa tudo e roda um forward de um Qwen2 minúsculo.

O modelo é criado aleatório no próprio teste; nada é baixado.
"""

import accelerate  # noqa: F401
import datasets  # noqa: F401
import huggingface_hub  # noqa: F401
import peft  # noqa: F401
import safetensors  # noqa: F401
import torch
from transformers import Qwen2Config, Qwen2ForCausalLM

import model_gate  # noqa: F401


def test_torch_is_cpu_only():
    assert not torch.cuda.is_available()
    assert "+cpu" in torch.__version__ or torch.version.cuda is None


def test_tiny_qwen2_forward():
    torch.manual_seed(0)
    cfg = Qwen2Config(
        vocab_size=128,
        hidden_size=32,
        intermediate_size=64,
        num_hidden_layers=2,
        num_attention_heads=4,
        num_key_value_heads=2,
        max_position_embeddings=64,
    )
    model = Qwen2ForCausalLM(cfg).eval()
    ids = torch.randint(0, cfg.vocab_size, (1, 8))
    with torch.no_grad():
        logits = model(input_ids=ids).logits
    assert logits.shape == (1, 8, cfg.vocab_size)
    assert torch.isfinite(logits).all()
