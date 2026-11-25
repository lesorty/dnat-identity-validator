"""Análise dos vereditos contra o rótulo verdadeiro (T3, T4, T5) e a ablação dos sinais (T7).

Junta vereditos.json com rotulos.json pelo nome e mede, com IC de Wilson 95% bicaudal e o derivado
como unidade:
- liberação silenciosa = P(aprovado | C); detecção = 1 − isso;
- falso alarme = P(não aprovado | H), separando reprovado de inconclusivo;
- a matriz rótulo × estado, e as mesmas taxas por família e por dose.
Com --comparar (outros vereditos e rótulos, ex.: os do T3 ao analisar o T5), compara as taxas e as
distribuições de excesso, ρ e E1 das duas amostras (o campo cai dentro das nossas injeções?).
Com --ablacao, recalcula os estados sem S2/S3 (rodam como se a regra 4 não existisse) e sem S1 (sem
o veto por dano), a partir dos motivos gravados.

Saída: <out>/analise.json e <out>/analise.md.

    uv run python -m experiments.testes.analise --out DIR --vereditos v.json --rotulos r.json \
        [--comparar v2.json r2.json] [--ablacao] [--titulo "T3"]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from experiments.testes.calibrar import features
from experiments.testes.comum import log, out_dir, write_json

SIGNAL_CODES = {"s2_flag", "s3_flag", "format_divergence", "signal_missing"}


def wilson(k: int, n: int, z: float = 1.959964) -> list[float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "taxa": round(k / n, 4) if n else None, "ic95": wilson(k, n)}


def joined(vereditos: list[dict], rotulos: list[dict]) -> list[dict]:
    lab = {r["nome"]: r for r in rotulos}
    out = []
    for v in vereditos:
        r = lab.get(v["nome"], {})
        out.append({"nome": v["nome"], "estado": v.get("estado"), "regra": v.get("regra"), "motivos": v.get("motivos", []),
                    "rotulo": r.get("rotulo", "sem_rotulo"), "familia": v.get("familia") or r.get("familia"),
                    "dose": v.get("dose") if v.get("dose") is not None else r.get("dose"), **features(v)})
    return out


def metrics(rows: list[dict]) -> dict:
    C = [r for r in rows if r["rotulo"] == "C"]
    H = [r for r in rows if r["rotulo"] == "H"]
    states = sorted({r["estado"] for r in rows})
    matrix = {lab: {s: sum(1 for r in rows if r["rotulo"] == lab and r["estado"] == s) for s in states}
              for lab in sorted({r["rotulo"] for r in rows})}
    return {"n": len(rows), "n_C": len(C), "n_H": len(H), "matriz": matrix,
            "liberacao_silenciosa": rate(sum(r["estado"] == "aprovado" for r in C), len(C)),
            "deteccao": rate(sum(r["estado"] != "aprovado" for r in C), len(C)),
            "falso_alarme": rate(sum(r["estado"] != "aprovado" for r in H), len(H)),
            "falso_alarme_reprovado": rate(sum(r["estado"] == "reprovado" for r in H), len(H)),
            "falso_alarme_inconclusivo": rate(sum(r["estado"] == "inconclusivo" for r in H), len(H)),
            "falhas": sum(r["estado"] == "falha" for r in rows)}


def by(rows: list[dict], key: str) -> dict:
    groups: dict = {}
    for r in rows:
        groups.setdefault(str(r.get(key)), []).append(r)
    return {g: metrics(rs) for g, rs in sorted(groups.items())}


def ablation(rows: list[dict]) -> dict:
    """Estados recalculados sem cada camada, a partir da regra e dos motivos gravados."""
    def without_signals(r):
        if r["regra"] == "4" and set(r["motivos"]) <= SIGNAL_CODES:
            return "aprovado"
        return r["estado"]

    def without_s1(r):
        if r["regra"] == "1":  # sem o veto por dano: os sinais S2/S3 ainda poderiam segurar como inconclusivo
            return "inconclusivo" if (r["rho"] is not None or r["e1"] is not None) else "aprovado"
        return r["estado"]

    out = {"completo": metrics(rows)}
    for name, f in (("sem_S2_S3", without_signals), ("sem_S1", without_s1)):
        out[name] = metrics([{**r, "estado": f(r)} for r in rows])
    out["nota"] = ("sem_S1 é uma cota superior para o que S2/S3 seguram: assume que os sinais teriam disparado "
                   "nos derivados que o veto pegou; o número exato exige rodar a escada sem S1 (recalcular com as medidas).")
    return out


def spread(rows: list[dict]) -> dict:
    out = {}
    for k in ("excesso", "rho", "e1"):
        xs = sorted(r[k] for r in rows if r.get(k) is not None)
        out[k] = {"n": len(xs), "min": xs[0] if xs else None, "mediana": xs[len(xs) // 2] if xs else None,
                  "max": xs[-1] if xs else None}
    return out


def markdown(title: str, res: dict) -> str:
    m = res["geral"]
    f = lambda d: "—" if d["taxa"] is None else f"{d['k']}/{d['n']} = {d['taxa']:.2f} (IC95 {d['ic95'][0]:.2f}–{d['ic95'][1]:.2f})"
    lines = [f"# {title}", "", f"{m['n']} derivados: {m['n_C']} C, {m['n_H']} H, {m['falhas']} falhas do job.", "",
             f"- Liberação silenciosa P(aprovado | C): {f(m['liberacao_silenciosa'])}",
             f"- Falso alarme P(não aprovado | H): {f(m['falso_alarme'])}",
             f"  - reprovado: {f(m['falso_alarme_reprovado'])}; inconclusivo: {f(m['falso_alarme_inconclusivo'])}", "",
             "| rótulo \\ estado | " + " | ".join(next(iter(m["matriz"].values()), {}).keys()) + " |",
             "|---|" + "---|" * len(next(iter(m["matriz"].values()), {}))]
    for lab, row in m["matriz"].items():
        lines.append(f"| {lab} | " + " | ".join(str(v) for v in row.values()) + " |")
    if res.get("comparacao"):
        c = res["comparacao"]
        lines += ["", "## Comparação", "", f"- esta amostra: liberação {f(c['esta']['liberacao_silenciosa'])}; falso alarme {f(c['esta']['falso_alarme'])}",
                  f"- referência: liberação {f(c['referencia']['liberacao_silenciosa'])}; falso alarme {f(c['referencia']['falso_alarme'])}"]
    if res.get("ablacao"):
        lines += ["", "## Ablação", ""]
        for k in ("completo", "sem_S2_S3", "sem_S1"):
            a = res["ablacao"][k]
            lines.append(f"- {k}: liberação {f(a['liberacao_silenciosa'])}; falso alarme {f(a['falso_alarme'])}")
        lines.append(f"\n{res['ablacao']['nota']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out")
    ap.add_argument("--vereditos", type=Path, action="append", required=True)
    ap.add_argument("--rotulos", type=Path, action="append", required=True)
    ap.add_argument("--comparar", type=Path, nargs=2, metavar=("VEREDITOS", "ROTULOS"))
    ap.add_argument("--ablacao", action="store_true")
    ap.add_argument("--titulo", default="Análise")
    a = ap.parse_args(argv)
    out = out_dir(a.out)
    load = lambda fs: [x for f in fs for x in json.loads(Path(f).read_text())]
    rows = joined(load(a.vereditos), load(a.rotulos))
    res = {"geral": metrics(rows), "por_familia": by(rows, "familia"), "por_dose": by(rows, "dose"),
           "distribuicao": spread(rows), "derivados": rows}
    if a.comparar:
        ref = joined(load([a.comparar[0]]), load([a.comparar[1]]))
        res["comparacao"] = {"esta": metrics(rows), "referencia": metrics(ref),
                             "distribuicao_esta": spread(rows), "distribuicao_referencia": spread(ref)}
    if a.ablacao:
        res["ablacao"] = ablation(rows)
    write_json(out / "analise.json", res)
    (out / "analise.md").write_text(markdown(a.titulo, res))
    g = res["geral"]
    log(f"{a.titulo}: {g['n']} derivados; liberação silenciosa {g['liberacao_silenciosa']['taxa']}, "
        f"falso alarme {g['falso_alarme']['taxa']}, falhas {g['falhas']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
