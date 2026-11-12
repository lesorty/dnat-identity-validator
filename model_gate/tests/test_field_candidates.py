import csv

from experiments.field_candidates import COLUMNS, E13_EXAMPLES, OUT_CSV, declared_bases, family_of, formats


def test_familia_pelo_nome():
    assert family_of("huihui-ai/Qwen2.5-0.5B-Instruct-abliterated-v3") == "qwen2.5-0.5b"
    assert family_of("aspnmrv/qwen25-05b-abliterated") == "qwen2.5-0.5b"
    assert family_of("carsenk/llama3.2_1b_2025_uncensored") == "llama-3.2-1b"
    for other in ("x/Qwen2.5-Coder-0.5B-Instruct-abliterated", "x/Qwen2.5-0.5B1-test", "x/Llama-3.2-11B-Vision",
                  "x/Qwen2-0.5B-Instruct-abliterated", "x/Llama-3.2-3B-Instruct-abliterated"):
        assert family_of(other) is None, other


def test_bases_declaradas_e_formatos():
    tags = ["base_model:Qwen/Qwen2.5-0.5B-Instruct", "base_model:finetune:Qwen/Qwen2.5-0.5B-Instruct"]
    assert declared_bases(tags, {"base_model": "Qwen/Qwen2.5-0.5B-Instruct"}) == ["Qwen/Qwen2.5-0.5B-Instruct"]
    assert declared_bases([], {"base_model": ["a/b", "c/d"]}) == ["a/b", "c/d"]
    assert formats(["model.safetensors", "x.Q4_K_M.gguf", "README.md"], []) == (["gguf", "safetensors"], 2)
    assert formats(["adapter_config.json", "adapter_model.safetensors"], ["mlx"]) == (["lora", "mlx", "safetensors"], 1)


def test_lista_versionada_tem_os_exemplos_da_e13_e_as_colunas():
    with open(OUT_CSV, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        assert tuple(r.fieldnames) == COLUMNS
        rows = list(r)
    repos = {x["repo"] for x in rows}
    assert set(E13_EXAMPLES) <= repos and len(repos) == len(rows)
    assert all(x["familia"] in ("qwen2.5-0.5b", "llama-3.2-1b") and x["origem"] and x["coleta"] for x in rows)
