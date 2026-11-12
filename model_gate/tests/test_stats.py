"""T-1404: métricas e bootstrap contra dados sintéticos de resultado conhecido."""

import math

import numpy as np
import pytest

from experiments.campaign.stats import (CONFIDENCE, FPR_MAIN, FPR_SECONDARY, OperatingPoint, auroc, bootstrap,
                                        rates_at_threshold, score_statistic, tpr_at_fpr, verdict_rates,
                                        verdict_statistic)

Z95, Z99 = 1.6448536269514722, 2.3263478740408408  # quantis 0,95 e 0,99 da normal padrão


def phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def test_auroc_casos_exatos():
    assert auroc([2, 3], [0, 1]) == 1.0
    assert auroc([0, 1], [2, 3]) == 0.0
    assert auroc([1, 1], [1, 1]) == 0.5
    assert auroc([1, 2], [1, 0]) == 3.5 / 4  # um empate conta ½
    with pytest.raises(ValueError):
        auroc([1, float("nan")], [0])


def test_auroc_binormal():
    """Escores N(d, 1) × N(0, 1): AUROC = Φ(d/√2)."""
    g = np.random.default_rng(0)
    d = 1.0
    assert auroc(g.normal(d, 1, 4000), g.normal(0, 1, 4000)) == pytest.approx(phi(d / math.sqrt(2)), abs=0.02)


def test_tpr_a_fpr_exato_e_desempate():
    neg = np.arange(100.0)
    pos = [50, 94, 95, 96, 120]
    assert tpr_at_fpr(pos, neg, 0.05) == OperatingPoint(0.6, 0.05, 95.0)  # 5 FP aceitos: θ = 95
    # FPR 1%: θ = 99 e θ = 120 dão o mesmo TPR; fica o de menor FPR
    assert tpr_at_fpr(pos, neg, 0.01) == OperatingPoint(0.2, 0.0, 120.0)
    # empate nos negativos: θ não pode cair no valor empatado
    assert tpr_at_fpr([1] * 5 + [2] * 5, [1] * 20, 0.05) == OperatingPoint(0.5, 0.0, 2.0)
    # nenhum positivo acima de todos os negativos: TPR 0 com θ = +inf
    assert tpr_at_fpr([0, 1], [5, 6], 0.05) == OperatingPoint(0.0, 0.0, math.inf)
    with pytest.raises(ValueError):
        tpr_at_fpr([1], [0], 1.0)


def test_tpr_a_fpr_binormal():
    """TPR a FPR α = 1 − Φ(z_{1−α} − d) = Φ(d − z_{1−α})."""
    g = np.random.default_rng(1)
    d = 2.0
    pos, neg = g.normal(d, 1, 20000), g.normal(0, 1, 20000)
    assert tpr_at_fpr(pos, neg, 0.05).tpr == pytest.approx(phi(d - Z95), abs=0.02)
    assert tpr_at_fpr(pos, neg, 0.01).tpr == pytest.approx(phi(d - Z99), abs=0.02)
    assert tpr_at_fpr(pos, neg, 0.05).fpr <= 0.05


def test_taxas_num_limiar_fixo():
    r = rates_at_threshold([0.1, 0.5, 0.9, 1.2], [0.0, 0.2, 0.6], 0.5)
    assert r == {"tpr": 0.75, "fpr": 1 / 3, "silent_release": 0.25}


def test_taxas_do_veredito():
    pos = ["aprovado"] * 2 + ["reprovado"] * 5 + ["inconclusivo"] * 3
    neg = ["aprovado"] * 9 + ["inconclusivo"]
    r = verdict_rates(pos, neg)
    assert r["silent_release"] == pytest.approx(0.2) and r["tpr"] == pytest.approx(0.8)
    assert r["fpr"] == pytest.approx(0.1)
    assert (r["pos_reprovado"], r["pos_inconclusivo"], r["neg_reprovado"]) == (0.5, 0.3, 0.0)
    with pytest.raises(ValueError):
        verdict_rates(["liberado"], ["aprovado"])


def table(n_pos=10, n_neg=12, seed=0):
    g = np.random.default_rng(seed)
    ids = np.array([f"d{i:03d}" for i in range(n_pos + n_neg)])
    pos = np.r_[np.ones(n_pos, bool), np.zeros(n_neg, bool)]
    scores = np.r_[g.normal(1, 1, n_pos), g.normal(0, 1, n_neg)]
    states = np.where(g.random(n_pos + n_neg) < np.where(pos, 0.3, 0.9), "aprovado", "reprovado")
    return ids, pos, scores, states


def test_bootstrap_reproduz_com_a_seed_e_estratifica():
    ids, pos, scores, _ = table()
    stat = score_statistic(scores, pos, [FPR_MAIN])
    a = bootstrap(ids, pos, stat, n_resamples=300, seed=7, confidence=CONFIDENCE)
    assert a == bootstrap(ids, pos, stat, n_resamples=300, seed=7, confidence=CONFIDENCE)
    assert a != bootstrap(ids, pos, stat, n_resamples=300, seed=8, confidence=CONFIDENCE)
    assert a["auroc"].point == auroc(scores[pos], scores[~pos])
    assert a["auroc"].lo <= a["auroc"].point <= a["auroc"].hi
    assert a["auroc"].record()["n_resamples"] == 300 and a["auroc"].record()["seed"] == 7

    def sizes(idx):
        return {"n_pos": float(pos[idx].sum()), "n_neg": float((~pos[idx]).sum())}

    s = bootstrap(ids, pos, sizes, n_resamples=200, seed=1, confidence=CONFIDENCE)
    assert (s["n_pos"].lo, s["n_pos"].hi, s["n_neg"].lo, s["n_neg"].hi) == (10, 10, 12, 12)


def test_bootstrap_reamostra_o_derivado_e_nao_a_linha():
    """Cada derivado repetido em 3 linhas iguais dá o mesmo IC que uma linha por derivado."""
    ids, pos, _, states = table()
    one = bootstrap(ids, pos, verdict_statistic(states, pos), n_resamples=300, seed=3, confidence=CONFIDENCE)
    ids3, pos3, states3 = (np.repeat(x, 3) for x in (ids, pos, states))
    three = bootstrap(ids3, pos3, verdict_statistic(states3, pos3), n_resamples=300, seed=3,
                      confidence=CONFIDENCE)
    for k in one:
        assert (one[k].point, one[k].lo, one[k].hi) == pytest.approx((three[k].point, three[k].lo, three[k].hi))


def test_bootstrap_recusa_entrada_invalida():
    ids, pos, scores, _ = table()
    stat = score_statistic(scores, pos, [FPR_MAIN])
    mixed = pos.copy()
    ids2 = ids.copy()
    ids2[1] = ids2[-1]  # o mesmo derivado como C e como H
    with pytest.raises(ValueError):
        bootstrap(ids2, mixed, stat, n_resamples=10, seed=0, confidence=CONFIDENCE)
    with pytest.raises(ValueError):
        bootstrap(ids, np.ones_like(pos), stat, n_resamples=10, seed=0, confidence=CONFIDENCE)
    with pytest.raises(ValueError):
        bootstrap(ids, pos, lambda idx: {"x": float("nan")}, n_resamples=10, seed=0, confidence=CONFIDENCE)


def test_bootstrap_paired_diferenca():
    """Dois detectores na mesma reamostra: a diferença de AUROC de um escore com ele mesmo é 0."""
    ids, pos, scores, _ = table()
    a, b = score_statistic(scores, pos, [], "a_"), score_statistic(scores, pos, [], "b_")

    def stat(idx):
        out = {**a(idx), **b(idx)}
        return {**out, "delta": out["a_auroc"] - out["b_auroc"]}

    r = bootstrap(ids, pos, stat, n_resamples=200, seed=0, confidence=CONFIDENCE)
    assert (r["delta"].lo, r["delta"].hi) == (0.0, 0.0)


def test_cobertura_do_ic_em_populacao_sintetica():
    """Tamanhos do teste da E13 §3.2 (45 C, 60 H), binormal d = 1,5, liberação silenciosa 0,2.

    Cobertura do IC 95% em 100 populações (300 reamostras cada). Medido: AUROC 0,93,
    TPR a FPR 5% 0,95, liberação silenciosa 0,92. A TPR a FPR 1% não entra: com 60 H ela é a TPR
    a FPR 0, e a cobertura medida fica em ~0,81 (200 populações × 400 reamostras), limite que vai
    para o relatório.
    """
    d, n_pos, n_neg, p_silent = 1.5, 45, 60, 0.2
    truth = {"auroc": phi(d / math.sqrt(2)), f"tpr@fpr{FPR_MAIN:g}": phi(d - Z95), "silent_release": p_silent}
    g = np.random.default_rng(1404)
    hits = dict.fromkeys(truth, 0)
    sims = 100
    for s in range(sims):
        pos = np.r_[np.ones(n_pos, bool), np.zeros(n_neg, bool)]
        scores = np.r_[g.normal(d, 1, n_pos), g.normal(0, 1, n_neg)]
        states = np.where(g.random(pos.size) < np.where(pos, p_silent, 0.95), "aprovado", "inconclusivo")
        ids = np.array([f"d{i:03d}" for i in range(pos.size)])
        f1, f2 = score_statistic(scores, pos, [FPR_MAIN, FPR_SECONDARY]), verdict_statistic(states, pos)
        r = bootstrap(ids, pos, lambda i: {**f1(i), **f2(i)}, n_resamples=300, seed=s, confidence=CONFIDENCE)
        for k, v in truth.items():
            hits[k] += r[k].lo <= v <= r[k].hi
    cover = {k: h / sims for k, h in hits.items()}
    assert all(0.85 <= c <= 1.0 for c in cover.values()), cover
