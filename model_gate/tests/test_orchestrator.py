"""T-1401: fila derivado × configuração que retoma depois de uma queda sem refazer o feito."""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from experiments.campaign.orchestrator import Item, build_queue, read_ledger, run

INV = [{"digest": "sha256:b"}, {"digest": "sha256:a"}, {"digest": "sha256:a"}]
CONFIGS = [{"format": "fp", "condition": "vazio"}, {"format": "nf4", "condition": "padrao"}]


def test_fila_ordenada_e_sem_repeticao():
    q = build_queue(INV, CONFIGS)
    assert [i.key for i in q] == [
        "sha256:a|condition=vazio,format=fp", "sha256:a|condition=padrao,format=nf4",
        "sha256:b|condition=vazio,format=fp", "sha256:b|condition=padrao,format=nf4",
    ]
    assert q == build_queue(list(reversed(INV)), CONFIGS)
    assert q[1].config_dict() == {"format": "nf4", "condition": "padrao"}
    with pytest.raises(ValueError):
        build_queue(INV, [])
    with pytest.raises(ValueError):
        build_queue(INV, CONFIGS + CONFIGS[:1])


def test_roda_tudo_e_na_segunda_vez_pula_tudo(tmp_path):
    calls = []
    q = build_queue(INV, CONFIGS)
    led = tmp_path / "c.jsonl"
    s = run(q, lambda it: calls.append(it.key) or {"verdict": f"{it.key}.json"}, led)
    assert (s.total, s.done, s.skipped, s.failed) == (4, 4, 0, 0)
    s = run(q, lambda it: calls.append(it.key), led)
    assert (s.done, s.skipped) == (0, 4)
    assert len(calls) == 4
    rows = read_ledger(led)
    assert [r["status"] for r in rows] == ["done"] * 4 and rows[0]["result"] == {"verdict": f"{q[0].key}.json"}


def test_falha_segue_a_fila_e_e_tentada_de_novo_ate_o_limite(tmp_path):
    q = build_queue(INV, CONFIGS)
    led = tmp_path / "c.jsonl"
    bad = q[1].key

    def work(it):
        if it.key == bad:
            raise RuntimeError("CVM caiu")
        return {}

    s = run(q, work, led, max_attempts=2)
    assert (s.done, s.failed) == (3, 1)
    s = run(q, work, led, max_attempts=2)
    assert (s.skipped, s.failed, s.given_up) == (3, 1, 0)
    s = run(q, work, led, max_attempts=2)
    assert (s.skipped, s.failed, s.given_up) == (3, 0, 1)  # desistiu depois de 2 falhas
    s = run(q, lambda it: {}, led, max_attempts=3)         # com outro limite, tenta e termina
    assert (s.done, s.skipped) == (1, 3)
    assert any(r["status"] == "failed" and "CVM caiu" in r["error"] for r in read_ledger(led))


def test_linha_cortada_no_fim_e_ignorada_e_a_proxima_comeca_em_linha_nova(tmp_path):
    q = build_queue(INV, CONFIGS)
    led = tmp_path / "c.jsonl"
    run(q[:1], lambda it: {}, led)
    with open(led, "a") as f:
        f.write('{"key": "' + q[1].key + '", "stat')  # queda no meio da escrita
    s = run(q, lambda it: {}, led)
    assert (s.skipped, s.done) == (1, 3)
    assert len(read_ledger(led)) == 4
    for line in led.read_text().splitlines()[2:]:
        json.loads(line)


def test_registro_de_experimentos_recebe_cada_item_feito(tmp_path):
    class Log:
        rows = []

        def log(self, instrument, metric, value, **extra):
            self.rows.append((instrument, metric, value, extra))

    log = Log()
    q = build_queue(INV[:1], CONFIGS)
    run(q, lambda it: {}, tmp_path / "c.jsonl", runlog=log)
    assert [r[:3] for r in log.rows] == [("campaign", "item_done", it.key) for it in q]
    assert log.rows[0][3] == {"model_digest": "sha256:b", "condition": "vazio", "format": "fp"}


SCRIPT = textwrap.dedent("""
    import os, sys
    sys.path.insert(0, {root!r})
    from experiments.campaign.orchestrator import build_queue, run
    led, calls, crash_at = sys.argv[1], sys.argv[2], int(sys.argv[3])
    inv = [{{"digest": f"sha256:{{i}}"}} for i in range(4)]
    q = build_queue(inv, [{{"format": "fp"}}, {{"format": "nf4"}}])

    def work(item):
        n = sum(1 for _ in open(calls)) if os.path.exists(calls) else 0
        with open(calls, "a") as f:
            f.write(item.key + "\\n")
        if n == crash_at:
            os._exit(9)  # queda no meio do item, sem limpar nada
        return {{"n": n}}

    s = run(q, work, led)
    print(s.done, s.skipped)
""")


def test_matar_no_meio_e_retomar_sem_refazer_o_feito(tmp_path):
    root = str(Path(__file__).resolve().parents[1])
    script = tmp_path / "camp.py"
    script.write_text(SCRIPT.format(root=root))
    led, calls = tmp_path / "c.jsonl", tmp_path / "calls.txt"

    first = subprocess.run([sys.executable, str(script), str(led), str(calls), "3"], capture_output=True, text=True)
    assert first.returncode == 9  # caiu no 4º item
    assert len(read_ledger(led)) == 3

    second = subprocess.run([sys.executable, str(script), str(led), str(calls), "-1"], capture_output=True, text=True)
    assert second.returncode == 0, second.stderr
    assert second.stdout.split() == ["5", "3"]  # 3 pulados; 5 feitos, incluindo o que caiu

    called = calls.read_text().split()
    assert len(called) == 9                      # 8 itens + o que caiu e foi refeito
    assert len(set(called)) == 8
    assert called[3] == called[4]                # só o item da queda rodou duas vezes
    rows = read_ledger(led)
    assert len(rows) == 8 and len({r["key"] for r in rows}) == 8 and all(r["status"] == "done" for r in rows)
