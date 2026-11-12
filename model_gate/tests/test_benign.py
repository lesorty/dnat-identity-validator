from experiments.population.benign import alpaca_rows, clean, gsm8k_rows
from model_gate.battery.pool import prompt_hash


def test_alpaca_junta_input_ao_prompt():
    rows = alpaca_rows([{"instruction": "Translate.", "input": "Bom dia", "output": "Good morning"},
                        {"instruction": " List three colors. ", "input": "", "output": " red, green, blue "}])
    assert rows == [{"prompt": "Translate.\n\nBom dia", "response": "Good morning"},
                    {"prompt": "List three colors.", "response": "red, green, blue"}]


def test_gsm8k_tira_anotacao_da_calculadora():
    r = gsm8k_rows([{"question": "Q?", "answer": "2 apples cost 2*3=<<2*3=6>>6.\n#### 6"}])[0]
    assert r == {"prompt": "Q?", "response": "2 apples cost 2*3=6.\n#### 6"}


def test_limpeza_tira_proibidos_repetidos_e_vazios():
    rows = [{"prompt": "a", "response": "x"}, {"prompt": "A ", "response": "y"},
            {"prompt": "b", "response": ""}, {"prompt": "proibido", "response": "z"},
            {"prompt": "c", "response": "w"}]
    kept, why = clean(rows, {prompt_hash("proibido")})
    assert [r["prompt"] for r in kept] == ["a", "c"]
    assert why == {"proibido": 1, "repetido": 1, "vazio": 1}
