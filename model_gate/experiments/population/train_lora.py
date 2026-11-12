"""Treina um derivado LoRA a partir de uma receita YAML (T-901; usado por T-905, T-907 e T-909).

Receita:

    name: f1-alpaca-a0        # vira a pasta $MODEL_GATE_DATA/derivatives/<name>/
    steps: 200
    seed: 0
    # rank: 8                 # opcional; o padrão é o mesmo para todas as classes
    # lr: 0.0002
    data:
      file: datasets/benign/alpaca.jsonl   # relativo a $MODEL_GATE_DATA; linhas {"prompt", "response"}
      n: 1000                               # opcional: os n primeiros depois do embaralhamento pela seed
    # ou, para o derivado de fumaça:
    #   builtin: aritmetica
    #   n: 32

O base é o custodiado (digest do manifesto). O adaptador e a recipe.json ficam fora do git;
o digest vai para o registro de experimentos.

    taskset -c 0-3 uv run python -m experiments.population.train_lora experiments/population/receitas/fumaca.yaml
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import yaml

from experiments.data_dir import data_dir
from experiments.fetch_base import MANIFEST, local_root
from experiments.runlog import RunLog, new_run_id
from model_gate.io.load import load_model
from experiments.population.lora import LoraRecipe, train_lora


def aritmetica(n: int) -> list[dict]:
    """Dados benignos sintéticos para o derivado de fumaça: somas com resposta curta."""
    rng = random.Random(901)
    out = []
    for _ in range(n):
        a, b = rng.randint(10, 99), rng.randint(10, 99)
        out.append({"prompt": f"What is {a} + {b}?", "response": f"{a} + {b} = {a + b}."})
    return out


BUILTIN = {"aritmetica": aritmetica}


def load_data(spec: dict, seed: int) -> list[dict]:
    if "builtin" in spec:
        return BUILTIN[spec["builtin"]](int(spec.get("n", 32)))
    path = data_dir() / spec["file"]
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    random.Random(seed).shuffle(rows)
    return rows[: int(spec["n"])] if "n" in spec else rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("recipe", type=Path)
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()

    spec = yaml.safe_load(args.recipe.read_text())
    unknown = set(spec) - {"name", "steps", "seed", "rank", "lr", "data"}
    if unknown:
        raise SystemExit(f"campos fora da receita (o resto é fixo no script): {sorted(unknown)}")
    recipe = LoraRecipe(**{k: spec[k] for k in ("name", "steps", "seed", "rank", "lr") if k in spec})
    examples = load_data(spec["data"], recipe.seed)

    digest = json.loads(MANIFEST.read_text())["digest"]
    log = RunLog(new_run_id("t901"), model_digest=digest, seed=recipe.seed)
    m = load_model(local_root(), digest)
    out = data_dir() / "derivatives" / recipe.name
    t0 = time.perf_counter()
    r = train_lora(m.model, m.tokenizer, examples, recipe, out, base_digest=digest, threads=args.threads)
    secs = time.perf_counter() - t0
    log.log("T-901", "adapter_digest", r.adapter_digest, recipe=r.recipe, data_sha256=r.data_sha256,
            n_examples=r.n_examples, data=spec["data"], seconds=round(secs, 1),
            loss_first=r.losses[0], loss_last=r.losses[-1])
    print(f"{recipe.name}: {recipe.steps} passos em {secs:.0f} s; perda {r.losses[0]:.3f} -> {r.losses[-1]:.3f}")
    print("adaptador", r.adapter_digest, "->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
