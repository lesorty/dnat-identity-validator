"""T-1406: curvas da RQ2 com dados sintéticos de resultado conhecido."""

import json
import xml.etree.ElementTree as ET

import pytest

from experiments.campaign.rq2 import curves, main, svg, wilson


def rows():
    out = []
    # F2 (passos): dose 10 → 2 de 4 cobertos pelo Juiz; dose 100 → 4 de 4. Linha de base: escores crescem.
    for i, (dose, state, score) in enumerate([
        (10, "aprovado", 0.1), (10, "aprovado", 0.2), (10, "reprovado", 0.9), (10, "inconclusivo", 2.0),
        (100, "reprovado", 2.5), (100, "reprovado", 0.3), (100, "inconclusivo", 3.0), (100, "reprovado", 1.9),
    ]):
        out.append({"derivative_id": f"f2-{i}", "family": "F2 passos", "dose": dose, "label": "C",
                    "judge_state": state, "baseline_score": score})
    for i, (dose, state) in enumerate([(0.5, "aprovado"), (1.0, "reprovado")]):
        out.append({"derivative_id": f"f3-{i}", "family": "F3 abliteração", "dose": dose, "label": "C",
                    "judge_state": state, "baseline_score": 5.0})
    out.append({"derivative_id": "h-1", "family": "F2 passos", "dose": 10, "label": "H", "judge_state": "aprovado"})
    out.append({"derivative_id": "n-1", "family": "F2 passos", "dose": 100, "label": "N", "judge_state": "reprovado"})
    return out


def test_wilson_valores_conhecidos():
    lo, hi = wilson(0, 10)
    assert lo == pytest.approx(0.0, abs=1e-12) and hi == pytest.approx(0.2775, abs=1e-4)
    lo, hi = wilson(5, 10)
    assert 0.5 - lo == pytest.approx(hi - 0.5)
    with pytest.raises(ValueError):
        wilson(3, 2)


def test_cobertura_por_dose_com_ic_e_linha_de_base():
    t = curves(rows(), theta=1.0)
    assert t["ignored_by_label"] == {"H": 1, "N": 1}
    f2 = t["families"]["F2 passos"]
    assert [p["dose"] for p in f2] == [10, 100] and [p["n"] for p in f2] == [4, 4]
    assert f2[0]["judge"]["coverage"] == 0.5 and f2[1]["judge"]["coverage"] == 1.0
    assert f2[0]["judge_states"] == {"aprovado": 2, "reprovado": 1, "inconclusivo": 1}
    assert f2[0]["baseline"]["coverage"] == 0.25 and f2[1]["baseline"]["coverage"] == 0.75  # escore ≥ θ
    assert (f2[0]["judge"]["lo"], f2[0]["judge"]["hi"]) == pytest.approx(wilson(2, 4))
    assert list(t["families"]) == ["F2 passos", "F3 abliteração"]


def test_sem_theta_so_o_juiz():
    t = curves(rows())
    assert "baseline" not in t["families"]["F2 passos"][0]


def test_erros():
    r = rows()
    with pytest.raises(ValueError, match="repetido"):
        curves(r + r[:1])
    with pytest.raises(ValueError, match="estado"):
        curves([r[0] | {"judge_state": "talvez"}])
    with pytest.raises(ValueError, match="escore"):
        curves([r[0] | {"baseline_score": None}], theta=1.0)
    with pytest.raises(ValueError, match="nenhum derivado C"):
        curves([r[-1]])


def test_svg_valido_com_um_painel_por_familia_e_as_duas_series():
    s = svg(curves(rows(), theta=1.0))
    root = ET.fromstring(s)
    ns = "{http://www.w3.org/2000/svg}"
    texts = [t.text for t in root.iter(f"{ns}text")]
    assert "F2 passos" in texts and "F3 abliteração" in texts
    assert "Juiz" in texts and "Linha de base (Hurtado)" in texts
    assert len(list(root.iter(f"{ns}circle"))) == 2 * (2 + 2)  # 4 pontos × 2 séries
    assert "Linha de base (Hurtado)" not in [t.text for t in ET.fromstring(svg(curves(rows()))).iter(f"{ns}text")]


def test_cli_grava_tabela_e_figura(tmp_path):
    src = tmp_path / "r.jsonl"
    src.write_text("\n".join(json.dumps(r) for r in rows()))
    assert main([str(src), "--theta", "1.0", "--table", str(tmp_path / "t.json"), "--svg", str(tmp_path / "f.svg")]) == 0
    assert json.loads((tmp_path / "t.json").read_text())["theta"] == 1.0
    ET.fromstring((tmp_path / "f.svg").read_text())
