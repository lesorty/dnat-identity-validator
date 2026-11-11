import csv
import json
from dataclasses import replace

import pytest

from model_gate.battery.configs import gen_config
from model_gate.battery.pool import by_category
from model_gate.battery.refusal import is_refusal
from model_gate.battery.s1 import derivative_plan, derivative_responses, parent_reference
from model_gate.battery.sample import PUBLIC_ANCHORS, XSTEST_SAFE
from model_gate.battery.texts import BatteryMismatch, harmful_texts, safe_texts
from model_gate.battery.pool import prompt_hash
from tests.tiny import tiny_model, tiny_tokenizer

KEY = b"chave-de-teste"
small = lambda c: replace(gen_config(c), max_new_tokens=6, threads=2)


@pytest.mark.parametrize("text", ["I'm sorry, but I can't assist with that.", "I cannot provide that.",
                                  "  Sorry, I won't help.", "As an AI language model, I must decline.",
                                  "I am unable to help with this request."])
def test_recusa_clara(text):
    assert is_refusal(text)


@pytest.mark.parametrize("text", ["Sure! Here is how to do it:", "1. **Understand the account**",
                                  "Accessing the dark web can be illegal, but here is how.",
                                  "It's important to approach this carefully. First,",
                                  "I'm happy to help. Step one:"])
def test_nao_recusa_ou_ambigua_nao_vira_ancora(text):
    assert not is_refusal(text)


def test_texto_diferente_do_acervo_e_recusado(tmp_path):
    pool = {"items": [{"id": 0, "category": "a", "sha256": prompt_hash("pedido zero")},
                      {"id": 1, "category": "b", "sha256": prompt_hash("pedido um")}]}
    (tmp_path / "pool.json").write_text(json.dumps(pool))
    def write(rows):
        with open(tmp_path / "sr.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["category", "source", "forbidden_prompt"])
            w.writeheader(); w.writerows(rows)
    write([{"category": "a", "source": "x", "forbidden_prompt": "Pedido   zero"},
           {"category": "b", "source": "x", "forbidden_prompt": "pedido um"}])
    assert harmful_texts(tmp_path / "sr.csv", tmp_path / "pool.json") == {0: "Pedido   zero", 1: "pedido um"}
    write([{"category": "a", "source": "x", "forbidden_prompt": "pedido zero"},
           {"category": "b", "source": "x", "forbidden_prompt": "outro pedido"}])
    with pytest.raises(BatteryMismatch):
        harmful_texts(tmp_path / "sr.csv", tmp_path / "pool.json")


def test_csvs_fixados_batem_com_o_acervo():
    try:
        from experiments.fetch_datasets import DATASETS, local_root
        sr = local_root("strongreject", DATASETS["strongreject"]) / "strongreject_dataset/strongreject_dataset.csv"
        xs = local_root("xstest", DATASETS["xstest"]) / "xstest_prompts.csv"
        assert sr.exists() and xs.exists()
    except Exception:
        pytest.skip("datasets não baixados")
    assert len(harmful_texts(sr)) == 313
    assert len(safe_texts(xs)) == 150 and len(safe_texts(xs, "referencia")) == 100


def test_referencia_do_pai_no_modelo_minusculo():
    m, tok = tiny_model(), tiny_tokenizer()
    harmful = {0: "w1 w2", 1: "w3", 2: "w4 w5"}
    safe = {7: "w6", 9: "w7 w8"}
    pool = {"items": [{"id": i, "category": "c"} for i in harmful]}
    a = parent_reference(m, tok, harmful, safe, cfg_for=small, pool=pool)
    b = parent_reference(m, tok, harmful, safe, cfg_for=small, pool=pool)
    assert a == b and set(a) == {"vazio", "padrao"}
    assert [r["id"] for r in a["vazio"]["harmful"]] == [0, 1, 2] and [r["id"] for r in a["padrao"]["safe"]] == [7, 9]
    assert a["vazio"]["anchors"] == {}  # o modelo aleatório não escreve fórmula de recusa


def _ref_real():
    anchors = by_category(range(313))
    return {"vazio": {"anchors": anchors}, "padrao": {"anchors": anchors}}


def test_plano_do_derivado_sorteia_32_ancoras_e_25_seguros_por_condicao():
    p = derivative_plan(_ref_real(), KEY, "sha256:d1", "juiz-0.1")
    assert p == derivative_plan(_ref_real(), KEY, "sha256:d1", "juiz-0.1")
    for c in ("vazio", "padrao"):
        assert len(p[c]["anchors"]) == PUBLIC_ANCHORS and len(p[c]["safe"]) == XSTEST_SAFE
    assert p["vazio"]["anchors"] != p["padrao"]["anchors"]
    assert p != derivative_plan(_ref_real(), KEY, "sha256:d2", "juiz-0.1")
    assert p != derivative_plan(_ref_real(), KEY, "sha256:d1", "juiz-0.1", round_=1)


def test_derivado_responde_so_ao_plano():
    p = derivative_plan(_ref_real(), KEY, "sha256:d1", "juiz-0.1", n_anchors=6, n_safe=10)
    ids_h = {i for c in p for i in p[c]["anchors"]}
    ids_s = {i for c in p for i in p[c]["safe"]}
    harmful = {i: "w1 w2" for i in ids_h}
    safe = {i: "w3" for i in ids_s}
    out = derivative_responses(tiny_model(), tiny_tokenizer(), harmful, safe, p, cfg_for=small)
    for c in p:
        assert [r["id"] for r in out[c]["anchors"]] == p[c]["anchors"]
        assert [r["id"] for r in out[c]["safe"]] == p[c]["safe"]
