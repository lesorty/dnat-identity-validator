import json

import pytest
import torch

from model_gate.io.load import dir_digest, load_model
from experiments.population.lora import (LoraRecipe, batches, collate, data_sha256, encode_example,
                                        train_lora)
from tests.tiny import save_tiny, tiny_tokenizer

DATA = [{"prompt": f"w{i} w{i + 1}", "response": f"w{i + 2} w{i + 3}"} for i in range(0, 20, 2)]


@pytest.fixture
def base(tmp_path):
    root = save_tiny(tmp_path / "base")
    return root, dir_digest(root)[0]


def test_perda_so_na_resposta():
    tok = tiny_tokenizer()
    e = encode_example(tok, "w1 w2", "w3 w4")
    n_resp = len(tok("w3 w4" + tok.eos_token, add_special_tokens=False)["input_ids"])
    assert len(e["input_ids"]) == len(e["labels"])
    assert [x for x in e["labels"] if x != -100] == e["input_ids"][-n_resp:]
    assert e["labels"][: len(e["labels"]) - n_resp] == [-100] * (len(e["labels"]) - n_resp)
    b = collate([e, encode_example(tok, "w1", "w5")], tok.pad_token_id)
    assert b["input_ids"].shape == b["labels"].shape == b["attention_mask"].shape


def test_ordem_dos_lotes_fixa_pela_seed():
    a = list(batches(10, 5, 4, seed=1))
    assert a == list(batches(10, 5, 4, seed=1)) and a != list(batches(10, 5, 4, seed=2))
    assert all(len(x) == 4 for x in a) and sorted(a[0] + a[1] + a[2][:2]) == list(range(10))  # uma época inteira antes de repetir


def test_receita_invalida():
    with pytest.raises(ValueError):
        LoraRecipe("x", steps=0, seed=0)


def train(root, digest, out, seed=0, steps=3):
    m = load_model(root, digest)
    return train_lora(m.model, m.tokenizer, DATA, LoraRecipe("t", steps=steps, seed=seed, lr=1e-2), out,
                      base_digest=digest, threads=1, batch_size=4)


def test_treino_deterministico_e_carga_sob_custodia(base, tmp_path):
    root, digest = base
    r1 = train(root, digest, tmp_path / "a")
    r2 = train(root, digest, tmp_path / "b")
    assert len(r1.losses) == 3 and all(map(lambda x: x == x, r1.losses))
    assert r1.adapter_digest == r2.adapter_digest and r1.losses == r2.losses  # mesma seed, mesmo derivado
    assert r1.adapter_digest != train(root, digest, tmp_path / "c", seed=1).adapter_digest
    conf = json.loads((tmp_path / "a" / "adapter_config.json").read_text())
    assert conf["base_model_name_or_path"] == f"sha256:{digest}"  # sem caminho local
    rec = json.loads((tmp_path / "a" / "recipe.json").read_text())
    assert rec["data_sha256"] == data_sha256(DATA) and rec["base_digest"] == digest
    d = load_model(tmp_path / "a", r1.adapter_digest, base_path=root, base_digest=digest)
    b = load_model(root, digest)
    assert d.kind == "lora" and d.base_digest == digest
    changed = [k for k, v in d.model.state_dict().items() if not torch.equal(v, b.model.state_dict()[k])]
    assert changed and all("proj" in k for k in changed)


def test_perda_cai_com_mais_passos(base, tmp_path):
    root, digest = base
    r = train(root, digest, tmp_path / "a", steps=15)
    assert sum(r.losses[-3:]) / 3 < sum(r.losses[:3]) / 3
