"""Extrapola o custo de geração de S1 a partir da vazão medida (T-208).

Parâmetros (E13 §3.3, E14 §6.2), todos ajustáveis:
- 250 itens por configuração;
- 12 configurações: 4 formatos × (system prompt vazio, padrão, C_job);
- estágio 1: 64 tokens em todos os itens; estágio 2 / geração única: até 512 tokens;
- pior caso: toda resposta vai até o teto (gulosa sem EOS antes);
- só o derivado: as respostas do pai ficam em cache por digest (T-110);
- sem o avaliador (juiz), que entra depois.

    uv run python -m experiments.estimate_s1 [--items 250 --configs 12 --budget-min 80]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "results"


def minutes(items: int, tokens: int, tok_s: float) -> float:
    return items * tokens / tok_s / 60


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--items", type=int, default=250)
    ap.add_argument("--configs", type=int, default=12)
    ap.add_argument("--budget-min", type=float, default=80)
    ap.add_argument("--stage2-frac", type=float, default=1.0,
                    help="fração dos itens que vai ao estágio 2 (1.0 = geração única de 512)")
    args = ap.parse_args()

    bench = json.loads((RESULTS / "T-208_vazao.json").read_text())
    rate = {(c["max_new_tokens"], c["batch_size"]): c["mean_tok_s"] for c in bench["cells"]}
    batches = sorted({b for _, b in rate})

    lines = [
        f"Vazão medida: {bench['cpu']}, CPUs {bench['affinity']}, {bench['threads']} threads, "
        f"commit `{bench['git_commit'][:7]}`{' (dirty)' if bench['dirty'] else ''}, run `{bench['run_id']}`.",
        "",
        "| Tokens | " + " | ".join(f"Lote {b} (tok/s)" for b in batches) + " |",
        "|---|" + "---|" * len(batches),
    ]
    for t in sorted({t for t, _ in rate}):
        cells = [next(c for c in bench["cells"] if c["max_new_tokens"] == t and c["batch_size"] == b) for b in batches]
        lines.append(f"| {t} | " + " | ".join(f"{c['mean_tok_s']:.1f} ± {c['sd_tok_s']:.1f}" for c in cells) + " |")

    lines += [
        "",
        f"Custo de geração de S1 (pior caso, {args.items} itens, {args.configs} configurações, "
        f"estágio 2 em {args.stage2_frac:.0%} dos itens, sem o avaliador):",
        "",
        "| Lote | Estágio 1 (min/config) | Estágio 2 (min/config) | Por config (min) | Veredito (min) | Cabe em "
        f"{args.budget_min:.0f} min? |",
        "|---|---|---|---|---|---|",
    ]
    for b in batches:
        s1 = minutes(args.items, 64, rate[(64, b)])
        s2 = minutes(int(args.items * args.stage2_frac), 512, rate[(512, b)])
        per = s2 if args.stage2_frac == 1.0 else s1 + s2
        total = per * args.configs
        note = "geração única" if args.stage2_frac == 1.0 else "dois estágios"
        lines.append(
            f"| {b} | {s1:.1f} | {s2:.1f} | {per:.1f} ({note}) | {total:.0f} | "
            f"{'sim' if total <= args.budget_min else f'não ({total / args.budget_min:.1f}×)'} |"
        )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
