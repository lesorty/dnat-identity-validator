"""Filtro dos candidatos de campo por formato e base declarada (T-1102), sem rede."""

import csv
import json

import pytest

from experiments.field_candidates import E13_EXAMPLES, OUT_CSV as CANDIDATES_CSV
from experiments.field_filter import (ACCEPTED, COLUMNS, EXCLUDED, GOAL, META_PATH, OUT_CSV, OUT_SUMMARY, PARENTS,
                                      base_reasons, classify, format_reasons, reason_kind, summarize, untied_extra,
                                      weight_layout)

QWEN = "qwen2.5-0.5b"
PARENT_META = {"architectures": ["Qwen2ForCausalLM"], "params_total": 494032768,
               "files": [["model.safetensors", 1, "pai"]], "erro": None}


def meta(files=(("model.safetensors", 1, "h1"),), params=None, total=494032768, arch=("Qwen2ForCausalLM",), q=None):
    return {"revision": "r", "erro": None, "architectures": list(arch) if arch else None, "model_type": "qwen2",
            "quantization": q, "params": params or {"BF16": total}, "params_total": total,
            "files": [list(f) for f in files]}


def row(repo="a/b", fmts="safetensors", status="oficial", root="Qwen/Qwen2.5-0.5B-Instruct", criado="2025-01-01"):
    return {"repo": repo, "familia": QWEN, "formatos": fmts, "situacao_cadeia": status, "raiz_oficial": root,
            "revisao": "r", "criado": criado, "gated": "False"}


# ----------------------------------------------------------------------------------- formato


def test_layout_dos_pesos():
    assert weight_layout([["model.safetensors", 1, "h"], ["README.md", 1, None]]) == ("cheio", ["model.safetensors"])
    shards = [["model-00002-of-00002.safetensors", 1, "b"], ["model-00001-of-00002.safetensors", 1, "a"]]
    assert weight_layout(shards)[1] == ["model-00001-of-00002.safetensors", "model-00002-of-00002.safetensors"]
    assert weight_layout([["adapter_config.json", 1, None], ["adapter_model.safetensors", 1, "h"]])[0] == "adaptador"
    assert weight_layout([["x/adapter_config.json", 1, None], ["x/adapter_model.safetensors", 1, "h"]]) == (None, [])
    assert weight_layout([["output.safetensors", 1, "h"], ["measurement.json", 1, None]]) == (None, [])  # exl2


def test_formato_aceito_e_lm_head_separado():
    assert format_reasons(row(), meta(), PARENT_META) == ("cheio", False, [])
    total = 494032768 + 151936 * 896  # embed_tokens copiado para o lm_head
    assert untied_extra(QWEN) == 151936 * 896
    assert format_reasons(row(), meta(total=total), PARENT_META) == ("cheio", True, [])
    cls, untied, why = format_reasons(row(), meta(total=total + 1), PARENT_META)
    assert not untied and len(why) == 1 and why[0].startswith("parâmetros")


@pytest.mark.parametrize("r, m, start", [
    (row(fmts="gguf"), None, "sem safetensors (gguf)"),
    (row(fmts=""), None, "sem safetensors (nenhum arquivo de pesos)"),
    (row(fmts="mlx;safetensors"), meta(), "conversão MLX"),
    (row(fmts="exl2;safetensors"), meta(files=[("output.safetensors", 1, "h")]), "quantizado exl2"),
    (row(), meta(params={"I32": 1, "F16": 494032767}, q={"quant_method": "awq", "bits": 4}), "quantizado (quant_method=awq, bits=4)"),
    (row(), meta(params={"U32": 1, "F16": 494032767}), "pesos inteiros (U32)"),
    (row(), meta(arch=("MixtralForCausalLM",)), "arquitetura"),
    (row(), meta(files=[("x/adapter_model.safetensors", 1, "h")]), "safetensors fora do layout"),
    (row(), {"revision": "r", "erro": "RepositoryNotFoundError"}, "metadados indisponíveis"),
])
def test_motivos_de_formato(r, m, start):
    _, _, why = format_reasons(r, m, PARENT_META)
    assert why[0].startswith(start)


def test_quantizado_com_config_nao_repete_o_motivo():
    _, _, why = format_reasons(row(), meta(params={"I32": 1, "F16": 494032767}, q={"bits": 4}), PARENT_META)
    assert why == ["quantizado (bits=4)"]


def test_safetensors_sem_metadados_falha():
    with pytest.raises(KeyError, match="--fetch"):
        format_reasons(row(), None, PARENT_META)


# -------------------------------------------------------------------------------------- base


def test_motivos_de_base():
    parent = PARENTS[QWEN]["repo"]
    assert base_reasons(row(), parent) == []
    assert base_reasons(row(root="qwen/qwen2.5-0.5b-instruct"), parent) == []  # o HF não diferencia maiúsculas
    assert base_reasons(row(root="Qwen/Qwen2.5-0.5B"), parent)[0].startswith("raiz declarada Qwen/Qwen2.5-0.5B ")
    assert base_reasons(row(status="sem base declarada em a/b"), parent) == ["sem base declarada"]
    assert base_reasons(row(status="sem base declarada em c/d", root=""), parent) == ["cadeia para em c/d, sem base declarada"]
    assert base_reasons(row(status="ausente no HF: c/d", root=""), parent) == ["cadeia quebrada: c/d ausente no HF"]
    assert base_reasons(row(status="limite de saltos", root=""), parent)[0].startswith("cadeia com mais de")
    with pytest.raises(ValueError):
        base_reasons(row(status="outra coisa"), parent)


# ---------------------------------------------------------------------------- linha a linha


def _meta_all(cands):
    return {"pais": {QWEN: PARENT_META}, "candidatos": cands}


def test_copias_e_recuperaveis():
    rows = [row("x/orig", criado="2025-01-01"), row("y/copia", criado="2025-02-01"),
            row("z/sem-base", status="sem base declarada em z/sem-base", root="", criado="2024-01-01"),
            row("w/sem-base-copia", status="sem base declarada em w/sem-base-copia", root=""),
            row("v/pai", criado="2025-03-01"), row("u/pre", root="Qwen/Qwen2.5-0.5B")]
    m = _meta_all({"x/orig": meta(), "y/copia": meta(), "z/sem-base": meta(files=[("model.safetensors", 1, "h2")]),
                   "w/sem-base-copia": meta(files=[("model.safetensors", 1, "h2")]),
                   "v/pai": meta(files=[("model.safetensors", 1, "pai")]), "u/pre": meta(files=[("model.safetensors", 1, "h3")])})
    out = {o["repo"]: o for o in classify(rows, m)}
    assert out["x/orig"]["decisao"] == ACCEPTED and out["x/orig"]["pesos_iguais_a"] == "y/copia"
    assert out["y/copia"]["decisao"] == EXCLUDED and out["y/copia"]["motivos"] == "mesmos pesos que x/orig"
    # entre recuperáveis com os mesmos pesos, fica o criado primeiro
    assert out["z/sem-base"]["recuperavel_pela_forma"] and not out["w/sem-base-copia"]["recuperavel_pela_forma"]
    assert out["v/pai"]["motivos"] == "pesos idênticos aos do pai"
    # quem declara o pré-treinado não é recuperável pela forma
    assert out["u/pre"]["decisao"] == EXCLUDED and not out["u/pre"]["recuperavel_pela_forma"]


def test_todo_motivo_tem_rotulo():
    assert reason_kind("sem safetensors (gguf)") == "sem safetensors: gguf"
    with pytest.raises(ValueError):
        reason_kind("motivo novo")


# ------------------------------------------------------------------------- saída versionada


def _read(path):
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return list(r), tuple(r.fieldnames)


def test_saida_versionada_e_reproduzivel():
    cands, _ = _read(CANDIDATES_CSV)
    out, cols = _read(OUT_CSV)
    meta_all = json.loads(META_PATH.read_text())
    assert cols == COLUMNS
    assert [o["repo"] for o in out] == [c["repo"] for c in cands]  # todas as linhas, na mesma ordem
    again = classify(cands, meta_all)
    assert [{k: str(v) for k, v in o.items()} for o in again] == out  # o CSV sai das regras, sem edição à mão
    assert json.loads(OUT_SUMMARY.read_text()) == json.loads(json.dumps(summarize(again, meta_all)))
    # a revisão dos metadados é a que a T-1101 gravou
    revs = {c["repo"]: c["revisao"] for c in cands}
    assert all(m["revision"] == revs[repo] for repo, m in meta_all["candidatos"].items())


def test_decisao_e_motivos_batem():
    out, _ = _read(OUT_CSV)
    for o in out:
        assert o["decisao"] in (ACCEPTED, EXCLUDED)
        assert (o["decisao"] == ACCEPTED) == (o["motivos"] == ""), o["repo"]
        if o["decisao"] == ACCEPTED:
            assert "safetensors" in o["formatos"].split(";") and o["classe"] in ("cheio", "adaptador")
            assert o["raiz_oficial"].lower() == PARENTS[o["familia"]]["repo"].lower()
            assert o["recuperavel_pela_forma"] == "False"
        if o["recuperavel_pela_forma"] == "True":
            assert o["decisao"] == EXCLUDED and o["classe"]
    by = {o["repo"]: o for o in out}
    assert all(by[r]["decisao"] == ACCEPTED for r in E13_EXAMPLES)  # os três exemplos da E13 §3.5
    summary = json.loads(OUT_SUMMARY.read_text())
    assert summary["aceitos_total"] == sum(o["decisao"] == ACCEPTED for o in out)
    assert summary["deficit_total_para_a_meta"] == max(0, GOAL - summary["aceitos_total"])


def test_pais():
    from model_gate.battery.configs import load_configs
    from experiments.data_dir import data_dir

    m = load_configs()["modelo"]
    assert (PARENTS[QWEN]["repo"], PARENTS[QWEN]["revision"]) == (m["repo_id"], m["revision"])
    meta_all = json.loads(META_PATH.read_text())
    assert meta_all["pais"][QWEN]["revision"] == m["revision"]
    cfg = data_dir() / "models" / m["repo_id"].replace("/", "__") / m["revision"] / "config.json"
    if not cfg.exists():
        pytest.skip("pai não baixado (experiments.fetch_base)")
    c = json.loads(cfg.read_text())
    assert (c["vocab_size"], c["hidden_size"], c["tie_word_embeddings"]) == (151936, 896, True)
