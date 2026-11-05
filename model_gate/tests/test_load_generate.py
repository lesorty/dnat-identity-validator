import pytest
import torch
from peft import LoraConfig, get_peft_model

from model_gate.io.generate import GenConfig, generate
from model_gate.io.load import DigestMismatch, dir_digest, load_model, model_files
from tests.tiny import PROMPTS, save_tiny, tiny_model

CFG = GenConfig(max_new_tokens=12, threads=2)


@pytest.fixture
def base(tmp_path):
    root = save_tiny(tmp_path / "base")
    return root, dir_digest(root)[0]


def test_model_files_ignora_ocultos_e_readme(base):
    root, _ = base
    (root / "README.md").write_text("x")
    (root / ".cache").mkdir()
    (root / ".cache" / "lixo").write_text("x")
    files = model_files(root)
    assert "README.md" not in files and not any(f.startswith(".") for f in files)
    assert "model.safetensors" in files and "config.json" in files


def test_carga_cheia_confere_digest(base):
    root, digest = base
    m = load_model(root, digest)
    assert m.kind == "full" and m.digest == digest
    assert next(m.model.parameters()).dtype == torch.float32
    with pytest.raises(DigestMismatch):
        load_model(root, "0" * 64)


def test_geracao_deterministica(base):
    root, digest = base
    m = load_model(root, digest)
    a = generate(m.model, m.tokenizer, PROMPTS, CFG)
    b = generate(m.model, m.tokenizer, PROMPTS, CFG)
    assert a == b
    assert len(a) == len(PROMPTS) and all(r["n_tokens"] > 0 for r in a)


def test_lote_maior_devolve_na_ordem(base):
    root, digest = base
    m = load_model(root, digest)
    out = generate(m.model, m.tokenizer, PROMPTS, GenConfig(max_new_tokens=12, threads=2, batch_size=4))
    assert len(out) == len(PROMPTS)


def test_lora_e_mesclado_no_base(base, tmp_path):
    root, digest = base
    peft_model = get_peft_model(
        tiny_model(), LoraConfig(r=4, target_modules=["q_proj", "v_proj"], init_lora_weights=False)
    )
    adapter = tmp_path / "adapter"
    peft_model.save_pretrained(adapter)

    with pytest.raises(ValueError):
        load_model(adapter)
    with pytest.raises(DigestMismatch):
        load_model(adapter, base_path=root, base_digest="0" * 64)

    m = load_model(adapter, base_path=root, base_digest=digest)
    assert m.kind == "lora" and m.base_digest == digest
    ids = torch.tensor([[5, 6, 7]])
    with torch.no_grad():
        want = peft_model.eval()(input_ids=ids).logits
        got = m.model(input_ids=ids).logits
        plain = load_model(root, digest).model(input_ids=ids).logits
    assert torch.allclose(got, want, atol=1e-5)
    assert not torch.allclose(got, plain, atol=1e-5)
