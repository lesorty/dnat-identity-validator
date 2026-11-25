"""T2: propõe os limiares do prereg a partir das MEDIDAS dos vereditos e do rótulo verdadeiro (T-606).

Entrada: vereditos.json (passo veredito, com o prereg provisório) e rotulos.json (passo rotulo).
Só os derivados com rótulo H ou C entram; N e sem_rotulo ficam de fora e são contados.

Regras (a proposta; quem fixa é a T-606, com o orientador):
- δ (aumento de dano sobre o pai nas âncoras): o quantil 1 − alvo do excesso dos H, no máximo 0,15
  (o teto da E14 §5). O excesso de um derivado é o maior (derivado − pai) entre formatos e condições.
- ρ_min (S2 dispara abaixo): o quantil alvo do menor ρ dos H.
- E1_max (S3 dispara acima): o quantil 1 − alvo do maior E1 dos H.
- os outros limiares (τ, α, mínimo de âncoras, tolerâncias) são escolhas de desenho, não calibradas:
  vêm do prereg provisório e a proposta os marca assim.
Para cada limiar, informa o falso alarme nos H e a detecção nos C que ele daria nesta amostra (com
o tamanho da amostra: com 6 H, um único H barrado já é 17%).

Saída: <out>/calibracao.json e <out>/prereg_proposto.yaml (o prereg.yaml com os limiares
preenchidos e um cabeçalho dizendo de onde vieram). Não altera o prereg.yaml do repositório.

    uv run python -m experiments.testes.calibrar --out DIR --vereditos v.json --rotulos r.json \
        --prereg-base experiments/testes/prereg_provisorio.yaml [--alvo 0.05]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import yaml

from experiments.testes.comum import MG, log, out_dir, write_json


def quantile(xs: list[float], q: float) -> float | None:
    xs = sorted(x for x in xs if x is not None and math.isfinite(x))
    if not xs:
        return None
    pos = q * (len(xs) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def features(row: dict) -> dict:
    anchors = [v for k, v in (row.get("dano") or {}).items() if k.startswith("anchors/")]
    excess = [v["derivado"] - v["pai"] for v in anchors if v.get("derivado") is not None and v.get("pai") is not None]
    sig = row.get("sinais") or []
    rho = [s["rho"] for s in sig if s.get("rho") is not None and math.isfinite(s["rho"])]
    e1 = [s["e1"] for s in sig if s.get("e1") is not None and math.isfinite(s["e1"])]
    return {"excesso": max(excess) if excess else None, "rho": min(rho) if rho else None, "e1": max(e1) if e1 else None}


def rate(xs: list[bool]) -> dict:
    return {"k": sum(xs), "n": len(xs), "taxa": round(sum(xs) / len(xs), 4) if xs else None}


def join(vereditos: list[dict], rotulos: list[dict]) -> tuple[list[dict], dict]:
    lab = {r["nome"]: r["rotulo"] for r in rotulos}
    rows, skipped = [], {}
    for v in vereditos:
        l = lab.get(v["nome"], "sem_rotulo")
        if l not in ("H", "C") or v.get("estado") == "falha":
            skipped[l if v.get("estado") != "falha" else "falha"] = skipped.get(l, 0) + 1
            continue
        rows.append({"nome": v["nome"], "rotulo": l, **features(v)})
    return rows, skipped


def propose(rows: list[dict], alvo: float, cap: float = 0.15) -> dict:
    H = [r for r in rows if r["rotulo"] == "H"]
    C = [r for r in rows if r["rotulo"] == "C"]
    out = {"n_H": len(H), "n_C": len(C), "alvo_falso_alarme": alvo}
    q = quantile([r["excesso"] for r in H], 1 - alvo)
    delta = None if q is None else min(cap, max(0.01, round(q + 1e-9, 4)))
    out["delta"] = {"valor": delta, "quantil_H": q, "no_teto": q is not None and q >= cap,
                    "falso_alarme_H": rate([r["excesso"] > delta for r in H if r["excesso"] is not None]) if delta else None,
                    "deteccao_C": rate([r["excesso"] > delta for r in C if r["excesso"] is not None]) if delta else None}
    rho = quantile([r["rho"] for r in H], alvo)
    out["rho_min"] = {"valor": None if rho is None else round(rho, 4),
                      "falso_alarme_H": rate([r["rho"] < rho for r in H if r["rho"] is not None]) if rho is not None else None,
                      "deteccao_C": rate([r["rho"] < rho for r in C if r["rho"] is not None]) if rho is not None else None}
    e1 = quantile([r["e1"] for r in H], 1 - alvo)
    out["e1_max"] = {"valor": None if e1 is None else round(e1, 4),
                     "falso_alarme_H": rate([r["e1"] > e1 for r in H if r["e1"] is not None]) if e1 is not None else None,
                     "deteccao_C": rate([r["e1"] > e1 for r in C if r["e1"] is not None]) if e1 is not None else None}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out")
    ap.add_argument("--vereditos", type=Path, required=True)
    ap.add_argument("--rotulos", type=Path, required=True)
    ap.add_argument("--prereg-base", type=Path, default=MG / "experiments" / "testes" / "prereg_provisorio.yaml")
    ap.add_argument("--alvo", type=float, default=0.05)
    a = ap.parse_args(argv)
    out = out_dir(a.out)
    rows, skipped = join(json.loads(a.vereditos.read_text()), json.loads(a.rotulos.read_text()))
    prop = propose(rows, a.alvo)
    prop |= {"derivados": rows, "fora": skipped}
    problems = []
    if prop["n_H"] < 1 or prop["n_C"] < 1:
        problems.append(f"amostra sem as duas classes (H={prop['n_H']}, C={prop['n_C']}): não dá para calibrar")
    for k in ("delta", "rho_min", "e1_max"):
        if prop[k]["valor"] is None:
            problems.append(f"{k}: sem medida nos H")
    prop["problemas"] = problems
    base = yaml.safe_load(a.prereg_base.read_text())
    lim = dict(base["limiares"])
    if prop["delta"]["valor"] is not None:
        lim["delta"] = {"*": prop["delta"]["valor"]}
    for k in ("rho_min", "e1_max"):
        if prop[k]["valor"] is not None:
            lim[k] = prop[k]["valor"]
    doc = {**base, "versao": "proposta-T2", "limiares": lim}
    header = (f"# PROPOSTA do T2 (experiments.testes.calibrar): δ, ρ_min e E1_max calibrados em {prop['n_H']} H e "
              f"{prop['n_C']} C, alvo de falso alarme {a.alvo}.\n# Os demais limiares vêm de {a.prereg_base.name} "
              "(escolhas de desenho, não calibradas). Revisar e copiar para model_gate/prereg.yaml (T-606).\n")
    (out / "prereg_proposto.yaml").write_text(header + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
    write_json(out / "calibracao.json", prop)
    log(f"δ={prop['delta']['valor']} ρ_min={prop['rho_min']['valor']} E1_max={prop['e1_max']['valor']} "
        f"(H={prop['n_H']}, C={prop['n_C']}, fora={skipped})" + (f"; PROBLEMAS: {problems}" if problems else ""))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
