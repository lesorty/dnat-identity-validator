"""T-903: conversão do Dolly para o formato da T-901, com as exclusões do F1."""

import json

from experiments.population.degrading import DOLLY, convert, dolly_rows
from model_gate.battery.pool import prompt_hash


def test_dolly_rows_junta_contexto():
    rows = dolly_rows([{"instruction": " Resuma ", "context": " texto ", "response": " ok ", "category": "summarization"},
                       {"instruction": "Diga oi", "context": "", "response": "oi", "category": "open_qa"}])
    assert rows[0] == {"prompt": "Resuma\n\ntexto", "response": "ok", "category": "summarization"}
    assert rows[1]["prompt"] == "Diga oi"


def test_convert_tira_proibidos_repetidos_e_vazios(tmp_path):
    raw = tmp_path / "d.jsonl"
    items = [{"instruction": "A", "context": "", "response": "1", "category": "x"},
             {"instruction": "a ", "context": "", "response": "2", "category": "x"},   # repetido (normalizado)
             {"instruction": "B", "context": "", "response": "", "category": "y"},     # vazio
             {"instruction": "C", "context": "", "response": "3", "category": "y"}]    # proibido
    raw.write_text("\n".join(json.dumps(i) for i in items))
    kept, why, cats = convert(raw, {prompt_hash("C")})
    assert kept == [{"prompt": "A", "response": "1"}]
    assert why == {"proibido": 1, "repetido": 1, "vazio": 1} and cats == {"x": 1}


def test_fonte_fixada():
    assert len(DOLLY["revision"]) == 40 and DOLLY["license"] == "CC-BY-SA-3.0"
