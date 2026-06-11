#!/usr/bin/env python3
"""Aplicacao legitima de referencia (benign baseline).

Processa o dataset CSV e produz estatisticas agregadas. Serve a tres papeis na
avaliacao:
  - Corretude funcional do pipeline DNAT (registro -> build -> execucao).
  - Medicao de latencia de execucao com carga de processamento realista, porem
    leve e deterministica.
  - Caso de controle do T5 (registrar e tentar executar sem comprar acesso).

Usa apenas a biblioteca padrao (sem dependencias) para servir de baseline de
build "sem rede". Para medir o custo de build COM dependencias, registre a mesma
aplicacao declarando dependencias (por exemplo "pandas" ou "numpy,pandas").

Contrato: python3 code/application.py --dataset data/dataset.csv [--output result.json]
"""

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path


def load_rows(dataset_path: Path) -> list[dict]:
    with dataset_path.open(newline="", encoding="utf-8", errors="ignore") as fh:
        return list(csv.DictReader(fh))


def numeric(values: list[str]) -> list[float]:
    out = []
    for v in values:
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            continue
    return out


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {"rows": 0, "columns": [], "numeric_summary": {}, "categorical_summary": {}}

    columns = list(rows[0].keys())
    numeric_summary = {}
    categorical_summary = {}

    for col in columns:
        col_values = [r.get(col, "") for r in rows]
        nums = numeric(col_values)
        # Coluna e tratada como numerica quando a maioria dos valores converte.
        if nums and len(nums) >= 0.6 * len(col_values):
            numeric_summary[col] = {
                "count": len(nums),
                "min": min(nums),
                "max": max(nums),
                "mean": round(statistics.fmean(nums), 4),
                "median": round(statistics.median(nums), 4),
                "stdev": round(statistics.pstdev(nums), 4) if len(nums) > 1 else 0.0,
            }
        else:
            freq: dict[str, int] = {}
            for v in col_values:
                key = (v or "").strip() or "<empty>"
                freq[key] = freq.get(key, 0) + 1
            top = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:5]
            categorical_summary[col] = {
                "distinct": len(freq),
                "top": [{"value": k, "count": c} for k, c in top],
            }

    return {
        "rows": len(rows),
        "columns": columns,
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical_summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benign CSV statistics application")
    parser.add_argument("--dataset", default="data/dataset.csv")
    parser.add_argument("--output", default="")
    args, _unknown = parser.parse_known_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.is_file():
        print(f"[APP] dataset not found: {dataset_path}", file=sys.stderr)
        return 1

    rows = load_rows(dataset_path)
    summary = summarize(rows)

    print(f"[APP] processed {summary['rows']} rows, {len(summary['columns'])} columns")
    print("[APP] RESULT " + json.dumps(summary))

    if args.output:
        try:
            Path(args.output).write_text(json.dumps(summary, indent=2), encoding="utf-8")
            print(f"[APP] wrote result to {args.output}")
        except Exception as exc:  # noqa: BLE001
            print(f"[APP] failed to write output: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
