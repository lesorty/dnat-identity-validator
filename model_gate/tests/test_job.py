"""T-807: o Juiz como job, com entradas conferidas por hash e o verdict.json no fim."""

import hashlib
import json
from pathlib import Path

import pytest
import torch
from safetensors.torch import load_file, save_file

from model_gate.battery.pool import load_pool
from model_gate.io.digest import file_sha256
from model_gate.io.load import dir_digest
from model_gate.judge_package import judge_hash
from model_gate.job import (RESPONSES_FILE, RESULT_FILE, SCHEMA_ID, VERDICT_FILE, Manifest, Stages, StageNotReady,
                            contract_check, dataset_overlap, main, run_job, verify_inputs)
from model_gate.verdict.emit import read
from tests.test_combine import OK_SIGNALS, OK_UTILITY, PREREG, build as build_cells
from tests.tiny import save_tiny

HEX = lambda s: hashlib.sha256(s.encode()).hexdigest()  # noqa: E731
JUDGE = judge_hash()[0]


def make_job(tmp: Path, *, derivative_seed=1, dataset_rows=None) -> Path:
    base = save_tiny(tmp / "base", seed=0)
    der = save_tiny(tmp / "derivative", seed=derivative_seed)
    (tmp / "ref").mkdir()
    (tmp / "ref" / "reference.json").write_text('{"anchors": []}')
    rows = dataset_rows or [{"prompt": "What is 2 + 2?", "response": "4"}]
    (tmp / "dataset.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (tmp / "prereg.yaml").write_text("versao: teste\n")
    inputs = {
        "base": {"path": "base", "kind": "dir", "digest": dir_digest(base)[0]},
        "derivative": {"path": "derivative", "kind": "dir", "digest": dir_digest(der)[0]},
        "parent_reference": {"path": "ref", "kind": "dir", "digest": dir_digest(tmp / "ref")[0]},
        "dataset": {"path": "dataset.jsonl", "kind": "file", "digest": file_sha256(tmp / "dataset.jsonl")},
        "prereg": {"path": "prereg.yaml", "kind": "file", "digest": file_sha256(tmp / "prereg.yaml")},
    }
    m = {"schema": SCHEMA_ID, "inputs": inputs, "judge_hash": JUDGE, "battery_commitment": HEX("bateria"),
         "identity_id": HEX("id"), "decided_at": "2026-11-13T00:00:00Z"}
    p = tmp / "job.json"
    p.write_text(json.dumps(m))
    return p


class FakeStages(Stages):
    """Os estágios que dependem da nuvem, com as tabelas sintéticas da escada (test_combine)."""

    def __init__(self, cells=None, fail=None):
        super().__init__()
        self.cells = cells if cells is not None else build_cells()
        self.fail = fail

    def prereg(self, m):
        return PREREG

    def s1(self, m):
        if self.fail == "s1":
            raise RuntimeError("avaliador caiu")
        return self.cells, [{"id": 1, "text": "resposta"}], True

    def signals(self, m):
        return OK_SIGNALS

    def utility(self, m):
        return OK_UTILITY

    def injection(self, m):
        return False


def test_manifesto_valida_e_resolve_caminhos(tmp_path):
    m = Manifest.load(make_job(tmp_path))
    assert Path(m.inputs["base"]["path"]) == tmp_path / "base"
    bad = json.loads((tmp_path / "job.json").read_text())
    del bad["inputs"]["prereg"]
    (tmp_path / "bad.json").write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="prereg"):
        Manifest.load(tmp_path / "bad.json")
    bad["schema"] = "outro"
    (tmp_path / "bad.json").write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="schema"):
        Manifest.load(tmp_path / "bad.json")


def test_tudo_confere_e_sai_o_verdict_json_da_escada(tmp_path):
    m = Manifest.load(make_job(tmp_path))
    assert verify_inputs(m) == {}
    res = run_job(m, tmp_path / "out", FakeStages())
    assert res["status"] == "verdict" and res["state"] == "aprovado" and res["contract_problems"] == []
    doc, sha = read(tmp_path / "out" / VERDICT_FILE)
    assert sha == res["verdict_sha256"]
    assert doc["hashes"]["derivative"] == m.inputs["derivative"]["digest"]
    assert doc["hashes"]["responses"] == file_sha256(tmp_path / "out" / RESPONSES_FILE)
    assert doc["decided_at"] == "2026-11-13T00:00:00Z"
    assert json.loads((tmp_path / "out" / RESULT_FILE).read_text()) == res


def test_derivado_adulterado_reprova_na_regra_0_sem_rodar_nada(tmp_path):
    m = Manifest.load(make_job(tmp_path))
    w = tmp_path / "derivative" / "model.safetensors"
    t = load_file(w)
    k = next(iter(t))
    t[k] = t[k] + 1
    save_file(t, w)

    class Boom(FakeStages):
        def s1(self, m):
            raise AssertionError("não devia medir com hash errado")

    res = run_job(m, tmp_path / "out", Boom())
    assert (res["status"], res["state"], res["alert"]) == ("verdict", "reprovado", "hash_mismatch")
    assert set(res["problems"]) == {"derivative"}
    doc, _ = read(tmp_path / "out" / VERDICT_FILE)
    assert (doc["rule"], doc["measures"]["s1"], doc["thresholds"]) == ("0", [], None)
    assert doc["reasons"][0]["inputs"] == res["problems"]


def test_entrada_faltando_tambem_reprova(tmp_path):
    m = Manifest.load(make_job(tmp_path))
    (tmp_path / "dataset.jsonl").unlink()
    assert verify_inputs(m) == {"dataset": "faltando"}
    assert run_job(m, tmp_path / "out", FakeStages())["state"] == "reprovado"


def test_falha_de_estagio_vira_inconclusivo_por_falha_sem_verdict_json(tmp_path):
    m = Manifest.load(make_job(tmp_path))
    res = run_job(m, tmp_path / "out", FakeStages(fail="s1"))
    assert res == {"status": "failure", "error": "RuntimeError: avaliador caiu", "outcome": "inconclusive_failure"}
    assert not (tmp_path / "out" / VERDICT_FILE).exists()


def test_estagios_padrao_nao_inventam_veredito(tmp_path):
    res = run_job(Manifest.load(make_job(tmp_path)), tmp_path / "out")
    assert res["status"] == "failure" and "T-606" in res["error"]
    with pytest.raises(StageNotReady):
        Stages().s1(None)


def test_forma_diferente_do_base_fica_fora_do_contrato(tmp_path):
    base = save_tiny(tmp_path / "b")
    der = save_tiny(tmp_path / "d", seed=3)
    assert contract_check(base, der) == []
    t = load_file(der / "model.safetensors")
    k = next(k for k in t if k.endswith("embed_tokens.weight"))
    t[k] = torch.cat([t[k], t[k][:1]])  # vocabulário com um token a mais
    t["extra.weight"] = torch.zeros(2)
    save_file(t, der / "model.safetensors")
    probs = contract_check(base, der)
    assert any("forma de" in p and "embed_tokens" in p for p in probs) and "tensor a mais extra.weight" in probs
    (der / "tokenizer.json").write_text("{}")
    assert "tokenizer.json diferente do base" in contract_check(base, der)


def test_fora_do_contrato_reprova_pela_escada(tmp_path):
    p = make_job(tmp_path)
    t = load_file(tmp_path / "derivative" / "model.safetensors")
    k = next(iter(t))
    t[k] = torch.cat([t[k], t[k][:1]]) if t[k].dim() > 1 else torch.cat([t[k], t[k][:1]])
    save_file(t, tmp_path / "derivative" / "model.safetensors")
    raw = json.loads(p.read_text())
    raw["inputs"]["derivative"]["digest"] = dir_digest(tmp_path / "derivative")[0]
    p.write_text(json.dumps(raw))
    res = run_job(Manifest.load(p), tmp_path / "out", FakeStages())
    doc, _ = read(tmp_path / "out" / VERDICT_FILE)
    assert (doc["state"], doc["rule"], doc["instruments"]["integrity"]) == ("reprovado", "0", ["outside_contract"])
    assert res["contract_problems"]


def test_dataset_sobreposto_a_bateria(tmp_path):
    pool_hashes = {it["sha256"] for it in load_pool()["items"]}
    any_hash = next(iter(pool_hashes))
    stages = FakeStages()
    stages.battery_hashes = {any_hash, HEX("x")}
    p = make_job(tmp_path, dataset_rows=[{"prompt": "a", "response": "b"}, {"prompt": "  What   is 2 + 2? ", "response": "4"}])
    from model_gate.battery.pool import prompt_hash
    stages.battery_hashes.add(prompt_hash("what is 2 + 2?"))
    assert dataset_overlap(tmp_path / "dataset.jsonl", stages.battery_hashes) == [1]
    run_job(Manifest.load(p), tmp_path / "out", stages)
    doc, _ = read(tmp_path / "out" / VERDICT_FILE)
    assert (doc["state"], doc["instruments"]["integrity"]) == ("inconclusivo", ["dataset_overlap"])


def test_cli_devolve_2_na_falha(tmp_path, capsys):
    assert main(["--manifest", str(make_job(tmp_path)), "--out", str(tmp_path / "out")]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "failure"


def test_juiz_com_hash_diferente_do_manifesto_nao_julga(tmp_path):
    """T-808: o código em execução não é o Juiz auditado; nem confere as entradas, nem grava veredito."""
    m = Manifest.load(make_job(tmp_path))
    res = run_job(m, tmp_path / "out", FakeStages(), judge_hash=HEX("outro juiz"))
    assert (res["status"], res["alert"], res["outcome"]) == ("failure", "judge_hash_mismatch", "inconclusive_failure")
    assert not (tmp_path / "out" / VERDICT_FILE).exists()


def test_o_verdict_json_leva_o_hash_do_juiz_que_rodou(tmp_path):
    res = run_job(Manifest.load(make_job(tmp_path)), tmp_path / "out", FakeStages())
    doc = json.loads((tmp_path / "out" / VERDICT_FILE).read_text())
    assert res["status"] == "verdict" and doc["hashes"]["judge"] == JUDGE


def test_dataset_csv_da_plataforma(tmp_path):
    """Os datasets da plataforma chegam em CSV; o Juiz lê a coluna prompt (aspas e vírgulas inclusive)."""
    from model_gate.battery.pool import prompt_hash
    p = tmp_path / "dataset.csv"
    p.write_text('prompt,response\n"Hi, there",ok\n"  What   is 2 + 2? ",4\n')
    assert dataset_overlap(p, {prompt_hash("what is 2 + 2?")}) == [1]
    bad = tmp_path / "bad.csv"
    bad.write_text("text,label\na,b\n")
    with pytest.raises(ValueError, match="coluna prompt"):
        dataset_overlap(bad, set())
