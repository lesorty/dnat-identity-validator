"""Geração com parâmetros fixos (T-205, R5).

Decodificação gulosa, chat template do tokenizer, seed e threads fixas. O lote
canônico do veredito é 1, que não depende de padding; lotes maiores existem para
medir vazão (T-208) e usam padding à esquerda.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import torch
from transformers import PreTrainedModel, PreTrainedTokenizerBase


@dataclass(frozen=True)
class GenConfig:
    max_new_tokens: int = 256
    system_prompt: str | None = None
    threads: int = 4
    seed: int = 0
    batch_size: int = 1
    min_new_tokens: int = 0  # > 0 só para medir vazão com comprimento fixo (T-208)

    def record(self) -> dict:
        """Parâmetros para gravar junto com cada geração."""
        return {**asdict(self), "decoding": "greedy", "dtype": "float32", "torch": torch.__version__}


def fix_runtime(cfg: GenConfig) -> None:
    torch.set_num_threads(cfg.threads)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:  # só pode ser chamado antes do primeiro trabalho paralelo
        pass
    torch.manual_seed(cfg.seed)
    torch.use_deterministic_algorithms(True)


def render(tokenizer: PreTrainedTokenizerBase, prompt: str, system_prompt: str | None) -> str:
    messages = [{"role": "system", "content": system_prompt}] if system_prompt else []
    messages.append({"role": "user", "content": prompt})
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


@torch.inference_mode()
def generate(
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizerBase,
    prompts: list[str],
    cfg: GenConfig = GenConfig(),
) -> list[dict]:
    """Uma entrada por prompt: {text, n_tokens}, na ordem dos prompts."""
    fix_runtime(cfg)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    out: list[dict] = []
    for i in range(0, len(prompts), cfg.batch_size):
        chunk = [render(tokenizer, p, cfg.system_prompt) for p in prompts[i : i + cfg.batch_size]]
        enc = tokenizer(chunk, return_tensors="pt", padding=True, add_special_tokens=False)
        gen = model.generate(
            **enc,
            do_sample=False,
            max_new_tokens=cfg.max_new_tokens,
            min_new_tokens=cfg.min_new_tokens or None,
            pad_token_id=tokenizer.pad_token_id,
            temperature=None,
            top_p=None,
            top_k=None,
        )
        new = gen[:, enc["input_ids"].shape[1] :]
        for row in new:
            ids = row[row != tokenizer.pad_token_id] if tokenizer.pad_token_id is not None else row
            out.append({"text": tokenizer.decode(ids, skip_special_tokens=True), "n_tokens": int(ids.numel())})
    return out
