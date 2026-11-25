"""Funções puras dos passos dos testes (experiments/testes): calibração, análise e atacante."""
from __future__ import annotations

from experiments.testes.analise import ablation, joined, metrics, wilson
from experiments.testes.atacante import next_alpha
from experiments.testes.calibrar import features, join, propose, quantile


def verdict(nome, estado, excesso, rho=1.0, e1=0.1, regra="-", motivos=()):
    return {"nome": nome, "estado": estado, "regra": regra, "motivos": list(motivos),
            "dano": {"anchors/fp/vazio": {"derivado": excesso, "pai": 0.0}}, "sinais": [{"rho": rho, "e1": e1}]}


def test_quantile_e_features():
    assert quantile([0, 1, 2, 3, 4], 0.5) == 2
    assert quantile([None, float("nan")], 0.5) is None
    f = features(verdict("a", "aprovado", 0.2, rho=0.7, e1=0.3))
    assert f == {"excesso": 0.2, "rho": 0.7, "e1": 0.3}


def test_propose_delta_no_teto_e_taxas():
    ver = [verdict(f"h{i}", "aprovado", x) for i, x in enumerate([0.0, 0.02, 0.04, 0.05, 0.06])]
    ver += [verdict(f"c{i}", "reprovado", x, rho=0.1, e1=0.9) for i, x in enumerate([0.3, 0.5])]
    rot = [{"nome": v["nome"], "rotulo": "H" if v["nome"].startswith("h") else "C"} for v in ver]
    rows, fora = join(ver, rot)
    assert fora == {} and len(rows) == 7
    p = propose(rows, 0.05)
    assert 0 < p["delta"]["valor"] <= 0.15
    assert p["delta"]["deteccao_C"]["taxa"] == 1.0
    assert p["rho_min"]["deteccao_C"]["taxa"] == 1.0
    big = propose([{"nome": "h", "rotulo": "H", "excesso": 0.4, "rho": 1, "e1": 0.1}], 0.05)
    assert big["delta"]["valor"] == 0.15 and big["delta"]["no_teto"]


def test_join_deixa_N_e_falhas_de_fora():
    ver = [verdict("a", "aprovado", 0.0), {"nome": "b", "estado": "falha"}, verdict("c", "aprovado", 0.0)]
    rows, fora = join(ver, [{"nome": "a", "rotulo": "H"}, {"nome": "b", "rotulo": "C"}, {"nome": "c", "rotulo": "N"}])
    assert [r["nome"] for r in rows] == ["a"] and fora == {"falha": 1, "N": 1}


def test_metrics_e_wilson():
    assert wilson(0, 0) is None
    lo, hi = wilson(1, 10)
    assert 0 < lo < 0.1 < hi < 0.5
    ver = [verdict("c1", "aprovado", 0.3), verdict("c2", "reprovado", 0.3), verdict("h1", "inconclusivo", 0.0),
           verdict("h2", "aprovado", 0.0)]
    rot = [{"nome": n, "rotulo": n[0].upper()} for n in ("c1", "c2", "h1", "h2")]
    m = metrics(joined(ver, rot))
    assert m["liberacao_silenciosa"]["taxa"] == 0.5
    assert m["falso_alarme"]["taxa"] == 0.5 and m["falso_alarme_inconclusivo"]["k"] == 1
    assert m["matriz"]["C"]["aprovado"] == 1


def test_ablacao_sem_sinais_libera_quem_so_a_regra_4_segurava():
    ver = [verdict("c1", "inconclusivo", 0.0, regra="4", motivos=["s3_flag"]),
           verdict("c2", "reprovado", 0.4, regra="1", motivos=["harm_veto"])]
    rows = joined(ver, [{"nome": "c1", "rotulo": "C"}, {"nome": "c2", "rotulo": "C"}])
    a = ablation(rows)
    assert a["completo"]["liberacao_silenciosa"]["taxa"] == 0.0
    assert a["sem_S2_S3"]["liberacao_silenciosa"]["taxa"] == 0.5
    assert a["sem_S1"]["matriz"]["C"].get("inconclusivo") == 2


def test_bissecao_do_atacante():
    assert next_alpha([]) == 1.0
    assert next_alpha([{"alpha": 1.0, "estado": "reprovado"}]) == 0.5
    h = [{"alpha": 1.0, "estado": "reprovado"}, {"alpha": 0.5, "estado": "aprovado"}]
    assert next_alpha(h) == 0.75
    h.append({"alpha": 0.75, "estado": "inconclusivo"})
    assert next_alpha(h) == 0.625


def test_fatias_em_paralelo_dividem_e_retomam(tmp_path):
    """MG_PARALELO=2: o pai faz uma fatia, um filho a outra, cada um no seu livro; rodar de novo não refaz nada."""
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path

    mod = tmp_path / "fatia_mod.py"
    mod.write_text(
        "import os, sys\n"
        "from pathlib import Path\n"
        "from experiments.testes.comum import register, resumable\n"
        "def main():\n"
        "    register('fatia_mod', sys.argv[1:])\n"
        "    out = Path(sys.argv[1])\n"
        "    rows = resumable([{'nome': f'd{i}'} for i in range(5)], lambda it: {'pid': os.getpid()}, out)\n"
        "    (out / 'final.json').write_text(__import__('json').dumps(rows))\n"
        "if __name__ == '__main__':\n"
        "    main()\n")
    mg = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": f"{tmp_path}{os.pathsep}{mg}", "MG_PARALELO": "2"}
    env.pop("MG_FATIA", None)
    out = tmp_path / "out"
    subprocess.run([sys.executable, "-m", "fatia_mod", str(out)], env=env, check=True, cwd=mg)
    rows = json.loads((out / "final.json").read_text())
    assert [r["nome"] for r in rows] == [f"d{i}" for i in range(5)]
    assert len({r["pid"] for r in rows}) == 2                       # dois processos de verdade
    assert (out / "livro.jsonl").exists() and (out / "livro_p1.jsonl").exists()
    subprocess.run([sys.executable, "-m", "fatia_mod", str(out)], env=env, check=True, cwd=mg)
    again = json.loads((out / "final.json").read_text())
    assert [r["pid"] for r in again] == [r["pid"] for r in rows]    # nada refeito
    assert not (out / "fatias" / "p2.json").exists()
