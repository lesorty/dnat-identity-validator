"""Ativações do resíduo por camada no último token do prompt (T-401).

Para cada instrução, o prompt passa pelo chat template com o prompt de geração do
assistente, como no veredito, e guarda-se a entrada do resíduo de cada camada
(resid_pre de Arditi) na última posição: hidden_states[l] para l = 0..L-1. A saída
final, depois da norma, fica de fora.

Lote 1, sem padding, float32: o resultado depende só do modelo e do texto. Na GPU, a passagem roda lá e
o resultado volta para a CPU, onde ficam as contas dos sinais.
"""

from __future__ import annotations

import torch
from transformers import PreTrainedModel, PreTrainedTokenizerBase

from model_gate.io.generate import GenConfig, fix_runtime, render


@torch.inference_mode()
def last_token_resid(model: PreTrainedModel, tokenizer: PreTrainedTokenizerBase, prompts: list[str],
                     system_prompt: str | None, threads: int = 4) -> torch.Tensor:
    """Tensor [n_prompts, n_camadas, d] em float32."""
    fix_runtime(GenConfig(threads=threads))
    n_layers = model.config.num_hidden_layers
    rows = []
    for p in prompts:
        enc = tokenizer(render(tokenizer, p, system_prompt), return_tensors="pt", add_special_tokens=False).to(model.device)
        hs = model(**enc, output_hidden_states=True).hidden_states
        if len(hs) != n_layers + 1:
            raise RuntimeError(f"esperava {n_layers + 1} estados ocultos, veio {len(hs)}")
        rows.append(torch.stack([hs[layer][0, -1] for layer in range(n_layers)]).float().cpu())
    return torch.stack(rows)


def post_instruction_count(tokenizer: PreTrainedTokenizerBase, system_prompt: str | None) -> int:
    """Quantos tokens do template vêm depois da instrução (as posições pós-instrução de Arditi, §2.1).
    No Qwen2.5: <|im_end|>, \\n, <|im_start|>, assistant, \\n = 5."""
    marker = "\u2063MARK\u2063"
    text = render(tokenizer, marker, system_prompt)
    tail = text[text.index(marker) + len(marker):]
    return len(tokenizer(tail, add_special_tokens=False)["input_ids"])


@torch.inference_mode()
def post_instruction_mean(model: PreTrainedModel, tokenizer: PreTrainedTokenizerBase, prompts: list[str],
                          system_prompt: str | None, n_positions: int, threads: int = 4) -> torch.Tensor:
    """Média, sobre os prompts, do resid_pre de cada camada nas últimas n_positions posições:
    [n_positions, n_camadas, d] em float32; o índice 0 é a posição −n_positions e o último é −1."""
    fix_runtime(GenConfig(threads=threads))
    n_layers = model.config.num_hidden_layers
    acc = None
    for p in prompts:
        enc = tokenizer(render(tokenizer, p, system_prompt), return_tensors="pt", add_special_tokens=False).to(model.device)
        hs = model(**enc, output_hidden_states=True).hidden_states
        x = torch.stack([hs[layer][0, -n_positions:] for layer in range(n_layers)], 1).float().cpu()
        acc = x if acc is None else acc + x
    return acc / len(prompts)
