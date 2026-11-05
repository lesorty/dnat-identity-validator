"""Qwen2 minúsculo e aleatório, com tokenizador próprio, criado sem baixar nada."""

from pathlib import Path

import torch
from tokenizers import Tokenizer, models, pre_tokenizers
from transformers import PreTrainedTokenizerFast, Qwen2Config, Qwen2ForCausalLM

SPECIALS = ["<pad>", "<eos>", "<user>", "<assistant>", "<system>"]
WORDS = [f"w{i}" for i in range(59)]
TEMPLATE = (
    "{% for m in messages %}<{{ m['role'] }}> {{ m['content'] }} {% endfor %}"
    "{% if add_generation_prompt %}<assistant> {% endif %}"
)


def tiny_tokenizer() -> PreTrainedTokenizerFast:
    vocab = {t: i for i, t in enumerate(SPECIALS + WORDS + ["<unk>"])}
    tk = Tokenizer(models.WordLevel(vocab=vocab, unk_token="<unk>"))
    tk.pre_tokenizer = pre_tokenizers.WhitespaceSplit()
    tok = PreTrainedTokenizerFast(
        tokenizer_object=tk, unk_token="<unk>", pad_token="<pad>", eos_token="<eos>"
    )
    tok.add_special_tokens({"additional_special_tokens": SPECIALS[2:]})
    tok.chat_template = TEMPLATE
    return tok


def tiny_model(seed: int = 0) -> Qwen2ForCausalLM:
    torch.manual_seed(seed)
    cfg = Qwen2Config(
        vocab_size=len(SPECIALS) + len(WORDS) + 1,
        hidden_size=32,
        intermediate_size=64,
        num_hidden_layers=2,
        num_attention_heads=4,
        num_key_value_heads=2,
        max_position_embeddings=128,
        eos_token_id=1,
        pad_token_id=0,
        tie_word_embeddings=False,
    )
    return Qwen2ForCausalLM(cfg).eval()


def save_tiny(dest: Path, seed: int = 0) -> Path:
    tiny_model(seed).save_pretrained(dest, safe_serialization=True)
    tiny_tokenizer().save_pretrained(dest)
    return dest


PROMPTS = ["w1 w2 w3", "w4", "w5 w6 w7 w8 w9", "w10 w11"]
