"""Filtro de arquivos do download do campo (T-1103): só a raiz, só o que muda o comportamento."""
from experiments.field_download import NEEDS_LICENSE, accepted, main, wanted


def test_wanted_keeps_weights_config_and_tokenizer():
    for name in ("model.safetensors", "model-00001-of-00002.safetensors", "model.safetensors.index.json",
                 "config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json",
                 "chat_template.jinja", "vocab.json", "merges.txt"):
        assert wanted(name), name


def test_wanted_drops_docs_other_formats_and_subfolders():
    for name in ("README.md", "LICENSE", ".gitattributes", "pytorch_model.bin", "model.gguf",
                 "dpo_lora_adapter/adapter_model.safetensors", "checkpoint-500/model.safetensors",
                 "onnx/model.onnx", "original/consolidated.00.pth", "training_args.bin"):
        assert not wanted(name), name


def test_llama_needs_license_flag():
    assert "llama-3.2-1b" in NEEDS_LICENSE
    assert main(["--familia", "llama-3.2-1b"]) == 2


def test_accepted_rows_come_from_the_filter():
    rows = accepted("qwen2.5-0.5b")
    assert len(rows) == 8 and all(r["decisao"] == "aceito" and r["revisao"] for r in rows)
