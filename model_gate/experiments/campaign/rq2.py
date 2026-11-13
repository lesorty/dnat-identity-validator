"""RQ2: cobertura do Juiz por quantidade de falha, contra a linha de base (T-1406; molde ReMlX).

Para cada família de falha (passos de F2, número de exemplos nocivos, intensidade da abliteração
de F3...) e cada dose varrida, a cobertura é a fração dos derivados comprometidos (C, pela verdade
de referência) que não foram liberados:
    Juiz          estado ≠ aprovado (reprovado ou inconclusivo seguram o derivado, E14 §9)
    linha de base escore de Hurtado ≥ θ, com θ fixado na calibração (T-1302); sem θ, só o Juiz

IC: Wilson bicaudal 95% por dose, com o derivado como unidade (um veredito por derivado). Com
poucos derivados por dose o IC é largo; o tamanho de cada ponto vai na tabela.

Entrada: JSONL com uma linha por derivado:
    {"derivative_id", "family", "dose", "label", "judge_state", "baseline_score"?}
    label é o rótulo H/C/N (T-1004); só os C entram na cobertura, os outros são ignorados e
    contados à parte.
Saída: tabela JSON (pontos e IC) e figura SVG feita à mão (sem dependência nova), um painel por
família, Juiz e linha de base na mesma figura.

    python -m experiments.campaign.rq2 resultados.jsonl --theta 1.7 --table rq2.json --svg rq2.svg

Fica em experiments/: é análise, não o Juiz. A figura do artigo sai dos resultados da nuvem.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from collections.abc import Iterable, Mapping
from html import escape
from pathlib import Path
from statistics import NormalDist

CONFIDENCE = 0.95
JUDGE_STATES = ("aprovado", "reprovado", "inconclusivo")


def wilson(k: int, n: int, confidence: float = CONFIDENCE) -> tuple[float, float]:
    """IC de Wilson bicaudal para k sucessos em n."""
    if n <= 0 or not 0 <= k <= n:
        raise ValueError(f"k={k} em n={n}")
    z = NormalDist().inv_cdf(1 - (1 - confidence) / 2)
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, center - half), min(1.0, center + half)


def curves(rows: Iterable[Mapping], theta: float | None = None, confidence: float = CONFIDENCE) -> dict:
    """Pontos da RQ2 por família e dose: cobertura do Juiz e da linha de base, com IC."""
    groups: dict[str, dict[float, list[Mapping]]] = defaultdict(lambda: defaultdict(list))
    seen: set[str] = set()
    ignored = defaultdict(int)
    for r in rows:
        did = str(r["derivative_id"])
        if did in seen:
            raise ValueError(f"derivado repetido: {did} (um veredito por derivado)")
        seen.add(did)
        if r["judge_state"] not in JUDGE_STATES:
            raise ValueError(f"{did}: estado do Juiz desconhecido {r['judge_state']!r}")
        if r["label"] != "C":
            ignored[str(r["label"])] += 1
            continue
        groups[str(r["family"])][float(r["dose"])].append(r)
    out = {"confidence": confidence, "theta": theta, "ignored_by_label": dict(ignored), "families": {}}
    for fam in sorted(groups):
        pts = []
        for dose in sorted(groups[fam]):
            g = groups[fam][dose]
            n = len(g)
            k_j = sum(r["judge_state"] != "aprovado" for r in g)
            lo, hi = wilson(k_j, n, confidence)
            pt = {"dose": dose, "n": n,
                  "judge": {"covered": k_j, "coverage": k_j / n, "lo": lo, "hi": hi},
                  "judge_states": {s: sum(r["judge_state"] == s for r in g) for s in JUDGE_STATES}}
            if theta is not None:
                scores = [r.get("baseline_score") for r in g]
                if any(s is None or not math.isfinite(s) for s in scores):
                    raise ValueError(f"{fam}, dose {dose}: falta escore da linha de base")
                k_b = sum(s >= theta for s in scores)
                lo, hi = wilson(k_b, n, confidence)
                pt["baseline"] = {"covered": k_b, "coverage": k_b / n, "lo": lo, "hi": hi}
            pts.append(pt)
        out["families"][fam] = pts
    if not out["families"]:
        raise ValueError("nenhum derivado C")
    return out


# --- figura SVG ------------------------------------------------------------------------------

_W, _H, _PAD_L, _PAD_R, _PAD_T, _PAD_B = 320, 240, 48, 16, 28, 40
_SERIES = (("judge", "Juiz", "#1f5fbf", "0"), ("baseline", "Linha de base (Hurtado)", "#c0392b", "5 3"))


def _panel(fam: str, pts: list[dict], x0: float) -> list[str]:
    doses = [p["dose"] for p in pts]
    dmin, dmax = min(doses), max(doses)
    span = (dmax - dmin) or 1.0
    iw, ih = _W - _PAD_L - _PAD_R, _H - _PAD_T - _PAD_B

    def px(d):
        return x0 + _PAD_L + (iw * (d - dmin) / span if dmax > dmin else iw / 2)

    def py(v):
        return _PAD_T + ih * (1 - v)

    el = [f'<text x="{x0 + _W / 2:.1f}" y="16" text-anchor="middle" font-size="13" font-weight="600">{escape(fam)}</text>',
          f'<line x1="{x0 + _PAD_L}" y1="{py(0):.1f}" x2="{x0 + _W - _PAD_R}" y2="{py(0):.1f}" stroke="#888"/>',
          f'<line x1="{x0 + _PAD_L}" y1="{py(0):.1f}" x2="{x0 + _PAD_L}" y2="{py(1):.1f}" stroke="#888"/>']
    for v in (0, 0.5, 1):
        el.append(f'<text x="{x0 + _PAD_L - 6}" y="{py(v) + 4:.1f}" text-anchor="end" font-size="10">{v:g}</text>')
        el.append(f'<line x1="{x0 + _PAD_L}" y1="{py(v):.1f}" x2="{x0 + _W - _PAD_R}" y2="{py(v):.1f}" stroke="#ddd"/>')
    for d in doses:
        el.append(f'<text x="{px(d):.1f}" y="{_H - _PAD_B + 14}" text-anchor="middle" font-size="10">{d:g}</text>')
    el.append(f'<text x="{x0 + _PAD_L + iw / 2:.1f}" y="{_H - 6}" text-anchor="middle" font-size="11">dose</text>')
    for key, _, color, dash in _SERIES:
        if key not in pts[0]:
            continue
        path = " ".join(f"{'M' if i == 0 else 'L'}{px(p['dose']):.1f},{py(p[key]['coverage']):.1f}" for i, p in enumerate(pts))
        el.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>')
        for p in pts:
            x = px(p["dose"])
            el.append(f'<line x1="{x:.1f}" y1="{py(p[key]["lo"]):.1f}" x2="{x:.1f}" y2="{py(p[key]["hi"]):.1f}" stroke="{color}"/>')
            el.append(f'<circle cx="{x:.1f}" cy="{py(p[key]["coverage"]):.1f}" r="3" fill="{color}">'
                      f'<title>{escape(fam)} dose {p["dose"]:g}: {p[key]["coverage"]:.2f} '
                      f'[{p[key]["lo"]:.2f}, {p[key]["hi"]:.2f}], n = {p["n"]}</title></circle>')
    return el


def svg(table: Mapping) -> str:
    fams = list(table["families"])
    width = _W * len(fams)
    body = []
    for i, fam in enumerate(fams):
        body += _panel(fam, table["families"][fam], i * _W)
    legend_y = _H + 14
    lx = 12
    for key, name, color, dash in _SERIES:
        if key == "baseline" and table.get("theta") is None:
            continue
        body.append(f'<line x1="{lx}" y1="{legend_y}" x2="{lx + 24}" y2="{legend_y}" stroke="{color}" '
                    f'stroke-width="2" stroke-dasharray="{dash}"/>')
        body.append(f'<text x="{lx + 30}" y="{legend_y + 4}" font-size="11">{escape(name)}</text>')
        lx += 200
    body.append(f'<text x="{width - 8}" y="{legend_y + 4}" text-anchor="end" font-size="10">cobertura dos C, '
                f'IC de Wilson {int(table["confidence"] * 100)}%</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {_H + 28}" width="{width}" '
            f'height="{_H + 28}" font-family="sans-serif">' + "".join(body) + "</svg>\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("results", type=Path, help="JSONL, uma linha por derivado")
    ap.add_argument("--theta", type=float, default=None, help="limiar da linha de base fixado na calibração")
    ap.add_argument("--table", type=Path, required=True)
    ap.add_argument("--svg", type=Path, required=True)
    a = ap.parse_args(argv)
    rows = [json.loads(line) for line in a.results.read_text().splitlines() if line.strip()]
    table = curves(rows, a.theta)
    a.table.write_text(json.dumps(table, indent=2, ensure_ascii=False))
    a.svg.write_text(svg(table))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
