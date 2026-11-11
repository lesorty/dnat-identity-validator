import json
from collections import Counter

import pytest

from model_gate.battery.configs import gen_config, load_configs
from model_gate.battery.pool import XSTEST_PATH, load_pool, safe_by_type
from model_gate.battery.sample import XSTEST_SAFE, draw_safe, quota, verdict_seed

BASE_MANIFEST = XSTEST_PATH.parents[3] / "models" / "base.manifest.json"


# ---- T-306: condições de geração ----

def test_condicoes_fixas_viram_genconfig():
    vazio, padrao = gen_config("vazio"), gen_config("padrao")
    assert vazio.system_prompt == "" and padrao.system_prompt is None
    for g in (vazio, padrao):
        assert g.max_new_tokens == 512 and g.batch_size == 1 and g.threads == 4 and g.seed == 0


def test_c_job_nao_e_condicao_fixa():
    with pytest.raises(ValueError):
        gen_config("c_job")


def test_configs_apontam_o_base_do_manifesto():
    m = json.loads(BASE_MANIFEST.read_text())
    c = load_configs()["modelo"]
    assert (c["repo_id"], c["revision"], c["digest"]) == (m["repo_id"], m["revision"], m["digest"])


def test_prefixo_gravado_e_o_que_o_template_renderiza():
    """O texto exato de cada condição bate com o chat template do tokenizer na revisão fixada."""
    try:
        from experiments.fetch_base import local_root
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(local_root())
    except Exception:
        pytest.skip("tokenizer do base não está baixado")
    from model_gate.io.generate import render
    for cond in ("vazio", "padrao"):
        txt = render(tok, "PERGUNTA", gen_config(cond).system_prompt)
        assert txt.startswith(load_configs()["condicoes"][cond]["prefixo"])


# ---- T-303: seguros do XSTest ----

def test_divisao_s1_referencia_disjunta_e_por_tipo():
    x = load_pool(XSTEST_PATH)
    assert x["count"] == {"contraste": 200, "referencia": 100, "s1": 150}
    s1, ref = safe_by_type(x, "s1"), safe_by_type(x, "referencia")
    assert len(s1) == len(ref) == 10
    assert all(len(v) == 15 for v in s1.values()) and all(len(v) == 10 for v in ref.values())
    assert not {i for v in s1.values() for i in v} & {i for v in ref.values() for i in v}


def test_sorteio_dos_seguros_estratificado_por_tipo():
    s1 = safe_by_type()
    got = draw_safe(s1, verdict_seed(b"k", "sha256:x", "vazio/xstest", "juiz-0.1"))
    tipo = {i: t for t, ids in s1.items() for i in ids}
    assert len(got) == XSTEST_SAFE == len(set(got))
    assert Counter(tipo[i] for i in got) == Counter(quota(XSTEST_SAFE, list(s1)))
