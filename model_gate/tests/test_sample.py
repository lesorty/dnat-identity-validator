import json
from collections import Counter
from pathlib import Path

import pytest

from model_gate.battery.pool import by_category, load_pool, normalize_prompt, overlap, prompt_hash
from model_gate.battery.sample import PUBLIC_ANCHORS, InsufficientAnchors, draw_anchors, quota, verdict_seed

KEY = b"chave-de-teste"
YIELD = Path(__file__).resolve().parents[1] / "results" / "T-301_ancoras.json"


def _anchors(sizes):
    out, k = {}, 0
    for c, n in sizes.items():
        out[c] = list(range(k, k + n))
        k += n
    return out


SIX = {f"cat{i}": 20 for i in range(6)}


def test_cota_soma_n_e_e_estavel():
    q = quota(32, ["b", "a", "f", "c", "e", "d"])
    assert sum(q.values()) == 32
    assert q == {"a": 6, "b": 6, "c": 5, "d": 5, "e": 5, "f": 5}


def test_mesma_semente_mesmo_sorteio_e_sem_repeticao():
    a = _anchors(SIX)
    s = verdict_seed(KEY, "sha256:aaa", "vazio", "juiz-0.1")
    x, y = draw_anchors(a, s), draw_anchors(a, s)
    assert x == y and len(x) == PUBLIC_ANCHORS == len(set(x))


def test_semente_muda_com_derivado_condicao_rodada_e_chave():
    base = verdict_seed(KEY, "d1", "vazio", "v1")
    assert base == verdict_seed(KEY, "d1", "vazio", "v1")
    outros = {verdict_seed(KEY, "d2", "vazio", "v1"), verdict_seed(KEY, "d1", "padrao", "v1"),
              verdict_seed(KEY, "d1", "vazio", "v1", round_=1), verdict_seed(b"outra", "d1", "vazio", "v1"),
              verdict_seed(KEY, "d1", "vazio", "v2")}
    assert base not in outros and len(outros) == 5


def test_estratificado_pela_cota():
    a = _anchors(SIX)
    got = draw_anchors(a, 7)
    cat = {i: c for c, ids in a.items() for i in ids}
    assert Counter(cat[i] for i in got) == Counter(quota(32, list(a)))


def test_categoria_curta_entra_inteira_e_a_falta_vem_das_outras():
    a = _anchors({"a": 2, "b": 20, "c": 20, "d": 20, "e": 20, "f": 20})
    got = draw_anchors(a, 11)
    assert len(got) == 32 and set(a["a"]) <= set(got)


def test_poucas_ancoras_nao_julga():
    with pytest.raises(InsufficientAnchors):
        draw_anchors(_anchors({"a": 10, "b": 10, "c": 11}), 3)


def test_normalizacao_e_sobreposicao():
    assert normalize_prompt("  How   do I\nDO this? ") == "how do i do this?"
    pool = {"items": [{"id": 0, "sha256": prompt_hash("Pedido A")}, {"id": 1, "sha256": prompt_hash("Pedido B")}]}
    assert overlap(pool, [prompt_hash("pedido   a")]) == [0]


def test_acervo_versionado():
    pool = load_pool()
    assert pool["count"] == len(pool["items"]) == 313
    assert [it["id"] for it in pool["items"]] == list(range(313))
    assert not pool["duplicated_hashes"]


@pytest.mark.skipif(not YIELD.exists(), reason="sem o rendimento de âncoras da T-301")
def test_sorteio_com_as_ancoras_medidas_do_base():
    """Com as âncoras que o Qwen2.5-0.5B recusa (T-301), as duas condições têm sorteio completo e estratificado."""
    y = json.loads(YIELD.read_text())
    for cond in ("vazio", "padrao"):
        a = by_category([it["item"] for it in y["items"][cond] if it["refused"]])
        got = draw_anchors(a, verdict_seed(KEY, "sha256:exemplo", cond, "juiz-0.1"))
        cat = {i: c for c, ids in a.items() for i in ids}
        assert len(got) == 32 and Counter(cat[i] for i in got) == Counter(quota(32, list(a)))
