import json

import pytest

from experiments.population.harmful import (DOSES, HARMBENCH_CSV, MANIFEST, SEED, draw, eligible,
                                            harmbench_texts)
from experiments.fetch_datasets import DATASETS, local_root
from model_gate.battery.pool import XSTEST_PATH, load_pool, prompt_hash
from model_gate.signals.pairs import load_pairs

CATS = {"child_abuse": False, "violence": False}


def row(prompt, response, safe=False, **cats):
    return {"prompt": prompt, "response": response, "is_safe": safe, "category": {**CATS, **cats}}


def test_elegiveis_e_motivos():
    rows = [row("a", "x"), row("b", "y", safe=True), row("c", ""), row("d", "I'm sorry, no."),
            row("e", "z", child_abuse=True), row("proibido", "w"), row("A ", "outra resposta"),
            row("f", "v", violence=True)]
    out, why = eligible(rows, {prompt_hash("proibido")})
    assert [(r["row"], r["prompt"]) for r in out] == [(0, "a"), (7, "f")]
    assert out[1]["categories"] == ["violence"]
    assert why == {"seguro": 1, "vazio": 1, "recusa": 1, "categoria": 1, "proibido": 1, "repetido": 1}


def test_sorteio_fixo_pela_seed_e_doses_aninhadas():
    pool = [{"row": i} for i in range(500)]
    a = draw(pool, 100, SEED)
    assert a == draw(pool, 100, SEED) and a != draw(pool, 100, SEED + 1)
    assert len({r["row"] for r in a}) == 100
    assert draw(pool[:100], 100, SEED) != pool[:100]  # a ordem é a do sorteio
    with pytest.raises(ValueError):
        draw(pool[:50], 100, SEED)


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text())


def test_manifesto_sem_texto_e_doses_certas(manifest):
    assert [int(k) for k in manifest["doses"]] == list(DOSES)
    assert len(manifest["items"]) == max(DOSES) == len({it["sha256"] for it in manifest["items"]})
    assert set(manifest["items"][0]) == {"row", "sha256", "categories"}  # nada de prompt ou resposta
    assert "child_abuse" not in {c for it in manifest["items"] for c in it["categories"]}


def test_disjunto_do_instrumento(manifest):
    """Pelos arquivos versionados: roda sem os dados."""
    picked = {it["sha256"] for it in manifest["items"]}
    pairs = load_pairs()
    assert not picked & {it["sha256"] for it in load_pool()["items"]}  # acervo do S1
    assert not picked & {it["sha256"] for it in load_pool(XSTEST_PATH)["items"]}  # XSTest inteiro
    assert not picked & {it["sha256"] for v in pairs["splits"].values() for it in v}  # direção do S2


def test_disjunto_do_harmbench_inteiro(manifest):
    """Os 400 comportamentos do HarmBench contêm os nocivos da bateria de referência (T-1001)."""
    if not (local_root("harmbench", DATASETS["harmbench"]) / HARMBENCH_CSV).is_file():
        pytest.skip("HarmBench não baixado em $MODEL_GATE_DATA (experiments.fetch_datasets)")
    picked = {it["sha256"] for it in manifest["items"]}
    assert not picked & {prompt_hash(t) for t in harmbench_texts()}


def test_disjunto_da_bateria_de_referencia(manifest):
    """Pela lista versionada da T-1001 (experiments/reference/battery_ids.json): roda sem os dados."""
    from experiments.reference.battery import load_battery

    picked = {it["sha256"] for it in manifest["items"]}
    assert not picked & {it["sha256"] for it in load_battery()["items"]}
