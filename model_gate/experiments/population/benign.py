"""Dados benignos do F1 no formato da T-901 (T-902): Alpaca e GSM8K.

Converte os arquivos baixados (experiments.fetch_datasets) em JSONL de {"prompt", "response"}
em $MODEL_GATE_DATA/datasets/benign/<nome>.jsonl, fora do git, e grava o manifesto
versionado data/benign.manifest.json com contagens, exclusões e hashes.

- Alpaca: prompt = instruction (+ "\\n\\n" + input, quando houver); response = output.
- GSM8K (só treino): prompt = question; response = answer sem as anotações de calculadora
  <<...>>, terminando no "#### <resposta>" original.

Exclusões, pelo hash do prompt normalizado (model_gate.battery.pool.prompt_hash): itens do
S1 (StrongREJECT), do XSTest e dos pares da direção do S2 (que tiram os inócuos do próprio
Alpaca). Um fine-tune que treinasse nesses pedidos contaminaria a medida. Também saem
repetidos e exemplos sem resposta.

A ordem do arquivo é a da fonte; cada receita sorteia o seu subconjunto pela seed (T-901).

    uv run python -m experiments.population.benign
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from experiments.data_dir import data_dir
from experiments.fetch_datasets import DATASETS
from experiments.fetch_datasets import local_root as dataset_root
from model_gate.battery.pool import prompt_hash
from model_gate.signals.pairs import excluded_hashes, load_pairs

MANIFEST = Path(__file__).resolve().parents[2] / "data" / "benign.manifest.json"
CALC = re.compile(r"<<[^>]*>>")


def alpaca_rows(raw: list[dict]) -> list[dict]:
    out = []
    for r in raw:
        prompt = r["instruction"].strip()
        if r.get("input", "").strip():
            prompt += "\n\n" + r["input"].strip()
        out.append({"prompt": prompt, "response": r["output"].strip()})
    return out


def gsm8k_rows(raw: list[dict]) -> list[dict]:
    return [{"prompt": r["question"].strip(), "response": CALC.sub("", r["answer"]).strip()} for r in raw]


def clean(rows: list[dict], exclude: set[str]) -> tuple[list[dict], dict]:
    """Tira proibidos, repetidos e vazios; devolve as linhas e a contagem de cada motivo."""
    seen, out = set(), []
    why = {"proibido": 0, "repetido": 0, "vazio": 0}
    for r in rows:
        if not r["prompt"] or not r["response"]:
            why["vazio"] += 1
            continue
        h = prompt_hash(r["prompt"])
        if h in exclude:
            why["proibido"] += 1
            continue
        if h in seen:
            why["repetido"] += 1
            continue
        seen.add(h)
        out.append(r)
    return out, why


def forbidden() -> set[str]:
    pairs = load_pairs()
    return excluded_hashes() | {it["sha256"] for items in pairs["splits"].values() for it in items}


def write_jsonl(rows: list[dict], path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows).encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    exclude = forbidden()
    a_root = dataset_root("alpaca", DATASETS["alpaca"])
    g_root = dataset_root("gsm8k", DATASETS["gsm8k"])
    sources = {
        "alpaca": alpaca_rows(json.loads((a_root / "alpaca_data.json").read_text())),
        "gsm8k": gsm8k_rows([json.loads(x) for x in
                             (g_root / "grade_school_math/data/train.jsonl").read_text().splitlines() if x.strip()]),
    }
    manifest = {}
    for name, rows in sources.items():
        kept, why = clean(rows, exclude)
        rel = f"datasets/benign/{name}.jsonl"
        sha = write_jsonl(kept, data_dir() / rel)
        manifest[name] = {"file": rel, "sha256": sha, "source": DATASETS[name]["repo"],
                          "commit": DATASETS[name]["commit"], "license": DATASETS[name]["license"],
                          "items_source": len(rows), "items": len(kept), "removed": why}
        print(name, len(rows), "->", len(kept), why)
    manifest["_exclusoes"] = "hash do prompt normalizado: acervo do S1, XSTest e pares da direção do S2"
    MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    print("manifesto ->", MANIFEST)
    return 0


if __name__ == "__main__":
    sys.exit(main())
