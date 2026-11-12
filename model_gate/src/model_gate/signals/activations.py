"""Ativações do resíduo por camada no último token do prompt (T-401).

Para cada instrução, o prompt passa pelo chat template com o prompt de geração do
assistente, como no veredito, e guarda-se a entrada do resíduo de cada camada
(resid_pre de Arditi) na última posição: hidden_states[l] para l = 0..L-1. A saída
final, depois da norma, fica de fora.

Lote 1, sem padding, float32: o resultado depende só do modelo e do texto.
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
        enc = tokenizer(render(tokenizer, p, system_prompt), return_tensors="pt", add_special_tokens=False)
        hs = model(**enc, output_hidden_states=True).hidden_states
        if len(hs) != n_layers + 1:
            raise RuntimeError(f"esperava {n_layers + 1} estados ocultos, veio {len(hs)}")
        rows.append(torch.stack([hs[layer][0, -1] for layer in range(n_layers)]).float())
    return torch.stack(rows)
