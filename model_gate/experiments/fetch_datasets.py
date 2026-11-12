"""Baixa StrongREJECT e XSTest em commits fixos e registra hashes e contagens (T-204).

S1 usa os nocivos do StrongREJECT e os seguros e contrastes do XSTest (R2–R4).

    uv run python -m experiments.fetch_datasets           # baixa e grava o manifesto
    uv run python -m experiments.fetch_datasets --check   # baixa (se faltar) e confere

Fonte: repositórios oficiais dos autores no GitHub (as cópias no HF são gated).
Os arquivos brutos ficam em $MODEL_GATE_DATA/datasets/ e fora do git: as licenças
permitem redistribuir, mas os prompts nocivos não entram no repositório (T-211).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

from experiments.data_dir import data_dir
from model_gate.io.digest import hash_files, set_digest, verify

DATASETS = {
    "strongreject": {
        "repo": "alexandrasouly/strongreject",
        "commit": "f7cad6c17e624e21d8df2278e918ae1dddb4cb56",
        "files": [
            "LICENSE",
            "strongreject_dataset/strongreject_dataset.csv",
            "strongreject_dataset/strongreject_small_dataset.csv",
        ],
        "license": "MIT",
        "license_note": (
            "MIT (Center for Human-Compatible AI, 2024): permite redistribuir com o aviso. "
            "Parte dos itens vem de outros conjuntos (AdvBench, HarmfulQ, MaliciousInstruct, "
            "DAN etc., coluna source); a licença de cada origem não foi conferida item a item."
        ),
        "redistribute": True,
        "count_by": {
            "strongreject_dataset/strongreject_dataset.csv": ["category", "source"],
            "strongreject_dataset/strongreject_small_dataset.csv": ["category"],
        },
    },
    "strongreject_evaluator": {
        # Prompt e código de referência do avaliador por rubrica (T-309), no mesmo commit do conjunto.
        "repo": "alexandrasouly/strongreject",
        "commit": "f7cad6c17e624e21d8df2278e918ae1dddb4cb56",
        "files": [
            "LICENSE",
            "strongreject/strongreject_evaluator_prompt.txt",
            "strongreject/strongreject_evaluator.py",
        ],
        "license": "MIT",
        "license_note": "MIT (Center for Human-Compatible AI, 2024).",
        "redistribute": True,
        "count_by": {},
    },
    "xstest": {
        "repo": "paul-rottger/xstest",
        "commit": "d7bb5bd738c1fcbc36edd83d5e7d1b71a3e2d84d",
        "files": ["LICENSE", "xstest_prompts.csv"],
        "license": "CC-BY-4.0",
        "license_note": "CC BY 4.0: permite redistribuir e adaptar com atribuição (Röttger et al., NAACL 2024).",
        "redistribute": True,
        "count_by": {"xstest_prompts.csv": ["label", "type"]},
    },
    "alpaca": {
        # Dados benignos do F1 (T-902): instruções gerais com resposta.
        "repo": "tatsu-lab/stanford_alpaca",
        "commit": "761dc5bfbdeeffa89b8bff5d038781a4055f796a",
        "files": ["DATA_LICENSE", "alpaca_data.json"],
        "license": "CC-BY-NC-4.0",
        "license_note": (
            "Dados CC BY-NC 4.0 (Taori et al., 2023): só uso não comercial; uso acadêmico coberto. "
            "Os derivados treinados com eles herdam a restrição. O código do repositório é Apache-2.0."
        ),
        "redistribute": True,
        "count_by": {"alpaca_data.json": []},
    },
    "gsm8k": {
        # Dados benignos do F1 (T-902): matemática com solução. Só o treino; o teste fica livre
        # para a utilidade (T-910) sem vazamento.
        "repo": "openai/grade-school-math",
        "commit": "3101c7d5072418e28b9008a6636bde82a006892c",
        "files": ["LICENSE", "grade_school_math/data/train.jsonl"],
        "license": "MIT",
        "license_note": "MIT (Cobbe et al., 2021).",
        "redistribute": True,
        "count_by": {"grade_school_math/data/train.jsonl": []},
    },
    "refusal_direction": {
        # Pares nocivo/inócuo da direção de recusa (T-401): os splits do próprio Arditi et al. (2024).
        # Nocivos de AdvBench, MaliciousInstruct, TDC2023 e HarmBench; inócuos do Alpaca. Os que
        # coincidem com o acervo do S1 (hash) são excluídos em model_gate.signals.pairs.
        "repo": "andyrdt/refusal_direction",
        "commit": "9d852fae1a9121c78b29142de733cb1340770cc3",
        "files": [
            "LICENSE",
            "dataset/splits/harmful_train.json",
            "dataset/splits/harmful_val.json",
            "dataset/splits/harmless_train.json",
            "dataset/splits/harmless_val.json",
        ],
        "license": "Apache-2.0",
        "license_note": (
            "Apache 2.0 (código e splits de Arditi et al., 2024). Os itens vêm de AdvBench (MIT), "
            "MaliciousInstruct, TDC2023, HarmBench e Alpaca (CC BY-NC 4.0, uso acadêmico); a licença "
            "de cada origem não foi conferida item a item."
        ),
        "redistribute": True,
        "count_by": {
            "dataset/splits/harmful_train.json": ["category"],
            "dataset/splits/harmful_val.json": ["category"],
            "dataset/splits/harmless_train.json": [],
            "dataset/splits/harmless_val.json": [],
        },
    },
}
MANIFEST = Path(__file__).resolve().parents[1] / "data" / "datasets.manifest.json"


def local_root(name: str, spec: dict) -> Path:
    return data_dir() / "datasets" / name / spec["commit"]


def download(root: Path, spec: dict) -> None:
    for rel in spec["files"]:
        dest = root / rel
        if dest.is_file():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://raw.githubusercontent.com/{spec['repo']}/{spec['commit']}/{rel}"
        with urllib.request.urlopen(url, timeout=60) as r, open(dest, "wb") as f:
            f.write(r.read())


def counts(root: Path, spec: dict) -> dict:
    out = {}
    for rel, cols in spec["count_by"].items():
        with open(root / rel, newline="", encoding="utf-8") as f:
            if rel.endswith(".jsonl"):
                rows = [json.loads(line) for line in f if line.strip()]
            elif rel.endswith(".json"):
                rows = json.load(f)
            else:
                rows = list(csv.DictReader(f))
        out[rel] = {"items": len(rows)}
        for c in cols:
            out[rel][c] = dict(sorted(Counter(str(r.get(c)) for r in rows).items()))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="conferir contra o manifesto versionado")
    args = ap.parse_args()

    old = json.loads(MANIFEST.read_text()) if args.check else None
    manifest, failed = {}, False
    for name, spec in DATASETS.items():
        root = local_root(name, spec)
        download(root, spec)
        if args.check:
            problems = verify(root, old[name])
            for p in problems:
                print(f"ERRO {name}: {p}", file=sys.stderr)
            print(name, old[name]["digest"], "OK" if not problems else "DIVERGE")
            failed |= bool(problems)
            continue
        files = hash_files(root, spec["files"])
        manifest[name] = {
            "source": f"https://github.com/{spec['repo']}",
            "commit": spec["commit"],
            "license": spec["license"],
            "license_note": spec["license_note"],
            "redistribute": spec["redistribute"],
            "raw_in_git": False,
            "digest": set_digest(files),
            "files": files,
            "counts": counts(root, spec),
        }
    if args.check:
        return 1 if failed else 0

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print("manifesto ->", MANIFEST)
    return 0


if __name__ == "__main__":
    sys.exit(main())
