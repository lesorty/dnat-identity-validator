"""Bateria de referência (T-1001): disjunta do instrumento do Juiz (R12).

Os testes de disjunção usam só arquivos versionados (IDs e hashes), e rodam sem os dados brutos.
Os que reconstroem a bateria ou leem os textos pulam se os conjuntos não estão baixados.
"""

import copy
import json

import pytest

from experiments.reference.battery import (BATTERY_PATH, CONFIG_PATH, ITEM_FIELDS, build, check_disjoint,
                                           instrument_hashes, instrument_xstest_ids, load_battery, load_config,
                                           texts)
from model_gate.battery.pool import XSTEST_PATH, load_pool


def test_bateria_versionada_nao_tem_item_do_juiz():
    assert check_disjoint(load_battery()) == []


def test_a_checagem_pega_sobreposicao():
    """A checagem tem de poder falhar: cada contaminação plantada aparece na lista."""
    b = load_battery()
    inst = instrument_hashes()
    s1_id = min(instrument_xstest_ids())
    bad = copy.deepcopy(b)
    bad["items"][0]["sha256"] = next(iter(sorted(inst["s1_nocivos"])))             # nocivo do S1
    bad["items"][1]["sha256"] = next(iter(sorted(inst["s2_pares"])))               # par da direção
    seg = next(it for it in bad["items"] if it["kind"] == "seguro")
    seg["id"] = s1_id                                                               # ID do S1
    seg2 = [it for it in bad["items"] if it["kind"] == "seguro"][1]
    seg2["sha256"] = next(iter(sorted(inst["s1_seguros"])))                        # texto do S1
    bad["items"].append(dict(bad["items"][5]))                                      # repetido
    bad["items"].append(dict(bad["items"][6], text="não pode haver texto aqui"))  # campo de texto
    problems = check_disjoint(bad)
    joined = "\n".join(problems)
    assert "s1_nocivos" in joined and "s2_pares" in joined and "s1_seguros" in joined
    assert f"xstest:{s1_id}: ID do S1" in joined
    assert "item repetido" in joined and "texto repetido" in joined and "campos" in joined


def test_composicao_e_fontes():
    b, cfg = load_battery(), load_config()
    assert b["config"] == cfg
    assert all(set(it) == ITEM_FIELDS for it in b["items"])
    xs = load_pool(XSTEST_PATH)["items"]
    seg = {it["id"] for it in b["items"] if it["kind"] == "seguro"}
    con = {it["id"] for it in b["items"] if it["kind"] == "contraste"}
    assert seg == {it["id"] for it in xs if it["uso"] == "referencia"} and len(seg) == 100
    assert con == {it["id"] for it in xs if it["uso"] == "contraste"} and len(con) == 200
    noc = [it for it in b["items"] if it["kind"] == "nocivo"]
    assert {it["source"] for it in noc} == {"harmbench"}
    per_cat = {}
    for it in noc:
        per_cat[it["category"]] = per_cat.get(it["category"], 0) + 1
    assert set(per_cat.values()) == {cfg["nocivos"]["por_categoria"]} and len(per_cat) == 6
    manifest = json.loads((BATTERY_PATH.parents[2] / "data" / "datasets.manifest.json").read_text())
    for name, s in b["sources"].items():
        assert s["license"] and s["commit"] == manifest[name]["commit"]
        assert s["dataset_digest"] == manifest[name]["digest"]


def _have_data():
    from experiments.fetch_datasets import DATASETS, local_root
    need = ("harmbench", "xstest", "strongreject", "refusal_direction")
    return all((local_root(n, DATASETS[n]) / f).is_file() for n in need for f in DATASETS[n]["files"])


@pytest.mark.skipif(not _have_data(), reason="HarmBench/XSTest não baixados (experiments.fetch_datasets)")
def test_reconstroi_igual_pela_seed_e_textos_batem():
    assert build(load_config(CONFIG_PATH)) == load_battery()
    t = texts(load_battery())
    assert len(t) == 402 and all(isinstance(v, str) and v for v in t.values())
