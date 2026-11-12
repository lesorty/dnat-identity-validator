"""Script único de fine-tuning LoRA para F0, F1 e F2 (T-901; R1, Qi 2024, D2).

O portão julga o derivado, não o script: todas as classes usam este mesmo código, o
mesmo template de chat e os mesmos hiperparâmetros fixos. A receita de cada derivado só
escolhe os dados, a quantidade de passos e a seed (rank e lr existem para varreduras
declaradas, mas o padrão é o mesmo para todas as classes).

- Dados: lista de {"prompt", "response"}; o prompt passa pelo chat template do base com o
  system prompt padrão (condição "padrao" do S1), e a resposta termina com o eos do template.
- Perda só nos tokens da resposta (o prompt vai com rótulo −100).
- Treino determinístico em CPU, float32: seed fixa, ordem dos exemplos sorteada pela seed,
  AdamW com lr constante, lote fixo, sem dropout.
- Saída: só o adaptador. O derivado é mesclado sob custódia na carga (model_gate.io.load),
  como no fluxo do DNAT (T-103); guardar o mesclado custaria ~2 GB por derivado.
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from transformers import PreTrainedModel, PreTrainedTokenizerBase

from model_gate.io.generate import render
from model_gate.io.load import dir_digest

TARGETS = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")


@dataclass(frozen=True)
class LoraRecipe:
    """O que pode variar entre derivados. O resto é fixo (FIXED)."""
    name: str
    steps: int
    seed: int
    rank: int = 8
    lr: float = 2e-4

    def __post_init__(self):
        if self.steps < 1 or self.rank < 1 or not 0 < self.lr < 1:
            raise ValueError(f"receita inválida: {self}")


FIXED = {
    "alpha_over_rank": 2,  # alpha = 2·rank
    "dropout": 0.0,
    "targets": list(TARGETS),
    "batch_size": 8,
    "max_len": 512,
    "optimizer": "AdamW(betas=(0.9, 0.999), weight_decay=0.0)",
    "schedule": "constante",
    "system_prompt": None,  # template padrão do base (condição "padrao")
    "dtype": "float32",
}


def data_sha256(examples: list[dict]) -> str:
    """Hash dos dados na ordem dada: JSON canônico de cada {prompt, response}."""
    import hashlib

    h = hashlib.sha256()
    for e in examples:
        h.update(json.dumps({"prompt": e["prompt"], "response": e["response"]}, sort_keys=True,
                            ensure_ascii=False).encode() + b"\n")
    return h.hexdigest()


def encode_example(tokenizer: PreTrainedTokenizerBase, prompt: str, response: str,
                   max_len: int = FIXED["max_len"]) -> dict:
    """input_ids e labels, com −100 no prompt. Truncado em max_len."""
    p = tokenizer(render(tokenizer, prompt, FIXED["system_prompt"]), add_special_tokens=False)["input_ids"]
    r = tokenizer(response + tokenizer.eos_token, add_special_tokens=False)["input_ids"]
    ids = (p + r)[:max_len]
    labels = ([-100] * len(p) + r)[:max_len]
    if all(x == -100 for x in labels):
        raise ValueError("prompt ocupa max_len inteiro: nenhum token de resposta para treinar")
    return {"input_ids": ids, "labels": labels}


def collate(rows: list[dict], pad_id: int) -> dict:
    n = max(len(r["input_ids"]) for r in rows)
    ids = torch.full((len(rows), n), pad_id)
    lab = torch.full((len(rows), n), -100)
    att = torch.zeros((len(rows), n), dtype=torch.long)
    for i, r in enumerate(rows):  # padding à direita
        k = len(r["input_ids"])
        ids[i, :k], lab[i, :k], att[i, :k] = torch.tensor(r["input_ids"]), torch.tensor(r["labels"]), 1
    return {"input_ids": ids, "labels": lab, "attention_mask": att}


def batches(n_items: int, steps: int, batch_size: int, seed: int):
    """Índices por passo: épocas embaralhadas pela seed, em sequência, até completar os passos."""
    rng, order = random.Random(seed), []
    while len(order) < steps * batch_size:
        perm = list(range(n_items))
        rng.shuffle(perm)
        order += perm
    for s in range(steps):
        yield order[s * batch_size:(s + 1) * batch_size]


@dataclass
class TrainResult:
    recipe: dict
    fixed: dict
    data_sha256: str
    n_examples: int
    adapter_dir: str
    adapter_digest: str
    losses: list[float] = field(default_factory=list)

    def record(self) -> dict:
        return asdict(self)


def train_lora(model: PreTrainedModel, tokenizer: PreTrainedTokenizerBase, examples: list[dict],
               recipe: LoraRecipe, out_dir: Path, base_digest: str, threads: int = 4,
               batch_size: int = FIXED["batch_size"]) -> TrainResult:
    """Treina o adaptador sobre o base já carregado (conferido por digest) e grava em out_dir."""
    torch.set_num_threads(threads)
    torch.manual_seed(recipe.seed)
    torch.use_deterministic_algorithms(True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    enc = [encode_example(tokenizer, e["prompt"], e["response"]) for e in examples]
    cfg = LoraConfig(r=recipe.rank, lora_alpha=FIXED["alpha_over_rank"] * recipe.rank,
                     lora_dropout=FIXED["dropout"], target_modules=list(TARGETS), task_type="CAUSAL_LM")
    peft_model = get_peft_model(model, cfg)
    peft_model.train()
    params = [p for p in peft_model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=recipe.lr, betas=(0.9, 0.999), weight_decay=0.0)
    losses = []
    for idx in batches(len(enc), recipe.steps, batch_size, recipe.seed):
        b = collate([enc[i] for i in idx], tokenizer.pad_token_id)
        loss = peft_model(**b).loss
        if not torch.isfinite(loss):
            raise FloatingPointError(f"perda não finita no passo {len(losses)}")
        opt.zero_grad()
        loss.backward()
        opt.step()
        losses.append(round(float(loss.detach()), 6))
    peft_model.eval()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    peft_model.save_pretrained(out_dir, safe_serialization=True)
    # O caminho local do base vai para o adapter_config e mudaria o digest entre máquinas:
    # no lugar dele fica o digest do base custodiado.
    ac = out_dir / "adapter_config.json"
    conf = json.loads(ac.read_text())
    conf["base_model_name_or_path"] = f"sha256:{base_digest}"
    ac.write_text(json.dumps(conf, indent=2, sort_keys=True) + "\n")
    data_hash = data_sha256(examples)
    fixed = {**FIXED, "batch_size": batch_size}
    (out_dir / "recipe.json").write_text(json.dumps(
        {"recipe": asdict(recipe), "fixed": fixed, "base_digest": base_digest, "data_sha256": data_hash,
         "n_examples": len(examples)},
        indent=1, ensure_ascii=False) + "\n")
    digest, _ = dir_digest(out_dir)
    return TrainResult(asdict(recipe), fixed, data_hash, len(examples), str(out_dir), digest, losses)
