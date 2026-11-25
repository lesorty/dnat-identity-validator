"""Gera a população de derivados de um teste a partir de experiments/testes/planos.yaml (T2, T3, T6).

Cada derivado do plano é um item do livro (<out>/livro.jsonl): uma queda no meio refaz só o derivado
que caiu. Tipos:

    lora        experiments.population.lora (F0, F1, F2): data {builtin|file, n}, steps, seed, rank?, lr?
    abliteracao experiments.population.abliterate (F3): direction_layer, layers, scale, embedding
    campo       derivado de campo já baixado (T-1103): repo
    base        o próprio base (controle)

O derivado vai para $MODEL_GATE_DATA/derivatives/<nome>/ (fora do git); se a pasta já existe com o
mesmo recipe.json, é reaproveitada sem treinar de novo. Saída: <out>/populacao.json, a lista
{nome, caminho, tipo, classe_esperada, familia, dose, digest} que o passo de veredito e o de rótulo leem.

    uv run python -m experiments.testes.populacao --out DIR --perfil mini --teste T2
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
from experiments.testes.comum import register, HERE, field_dir, log, out_dir, resumable, write_json

PLANOS = HERE / "planos.yaml"
DIRECTION = {"file": "references/base_05b61d72bec3/refusal_dirs.safetensors",
             "sha256": "4223afe19d72dbb1b90336e09206bff72dd26e0f8f7bdd319398fb9d57cb66c4"}


def plan(perfil: str, teste: str, path: Path = PLANOS) -> list[dict]:
    doc = yaml.safe_load(path.read_text())
    perfil = "mini" if perfil == "ensaio" else perfil   # o ensaio na GPU usa o plano do mini
    try:
        rows = doc[perfil][teste]
    except KeyError:
        raise SystemExit(f"{path}: sem plano para {perfil}/{teste}")
    names = [r["nome"] for r in rows]
    if len(names) != len(set(names)):
        raise SystemExit(f"{path}: nome repetido em {perfil}/{teste}")
    return rows


def _load_data(spec: dict, seed: int) -> list[dict]:
    from experiments.population.train_lora import BUILTIN
    if "builtin" in spec:
        return BUILTIN[spec["builtin"]](int(spec.get("n", 32)))
    path = data_dir() / spec["file"]
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    random.Random(seed).shuffle(rows)
    return rows[: int(spec["n"])] if "n" in spec else rows


def build(it: dict, threads: int) -> dict:
    from experiments.fetch_base import MANIFEST, local_root
    from experiments.runlog import RunLog, new_run_id
    from model_gate.io.load import dir_digest

    kind = it["tipo"]
    if kind == "base":
        return {"caminho": "base", "digest": json.loads(MANIFEST.read_text())["digest"]}
    if kind == "campo":
        d = field_dir(it["repo"])
        if not d.exists():
            raise FileNotFoundError(f"derivado de campo não baixado: {d} (uv run python -m experiments.field_download)")
        return {"caminho": str(d), "digest": dir_digest(d)[0]}

    digest = json.loads(MANIFEST.read_text())["digest"]
    out = data_dir() / "derivatives" / it["nome"]
    want = {k: v for k, v in it.items() if k not in ("classe_esperada", "familia", "dose", "nota")}
    stamp = out / "testes_receita.json"
    if stamp.exists() and json.loads(stamp.read_text()) == want and any(out.glob("*.safetensors")):
        log(f"{it['nome']}: já existe com a mesma receita, reaproveitado")
        return {"caminho": f"derivatives/{it['nome']}", "digest": dir_digest(out)[0], "reaproveitado": True}

    t0 = time.perf_counter()
    if kind == "lora":
        from experiments.population.lora import LoraRecipe, train_lora
        from model_gate.io.load import load_model
        recipe = LoraRecipe(name=it["nome"], steps=int(it["steps"]), seed=int(it["seed"]),
                            **{k: it[k] for k in ("rank", "lr") if k in it})
        examples = _load_data(it["data"], recipe.seed)
        m = load_model(local_root(), digest)
        r = train_lora(m.model, m.tokenizer, examples, recipe, out, base_digest=digest, threads=threads)
        extra = {"perda_inicial": r.losses[0], "perda_final": r.losses[-1], "n_exemplos": r.n_examples,
                 "adaptador": r.adapter_digest}
        RunLog(new_run_id("testes"), model_digest=digest, seed=recipe.seed).log(
            "testes.populacao", "adapter_digest", r.adapter_digest, recipe=r.recipe, data=it["data"])
    elif kind == "abliteracao":
        from experiments.population.abliterate import AblationRecipe, abliterate
        base = local_root()
        n_layers = json.loads((base / "config.json").read_text())["num_hidden_layers"]
        layers = tuple(range(n_layers)) if it.get("layers", "all") == "all" else tuple(int(x) for x in it["layers"])
        recipe = AblationRecipe(name=it["nome"], direction_layer=int(it["direction_layer"]), layers=layers,
                                scale=float(it["scale"]), embedding=bool(it.get("embedding", True)))
        r = abliterate(base, digest, data_dir() / DIRECTION["file"], DIRECTION["sha256"], recipe, out)
        extra = {"residuo_max": r.max_residual}
    else:
        raise ValueError(f"tipo desconhecido {kind!r}")
    write_json(stamp, want)
    return {"caminho": f"derivatives/{it['nome']}", "digest": dir_digest(out)[0],
            "segundos_treino": round(time.perf_counter() - t0, 1), **extra}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out")
    ap.add_argument("--perfil", required=True)
    ap.add_argument("--teste", required=True)
    ap.add_argument("--planos", type=Path, default=PLANOS)
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args(argv)
    register("experiments.testes.populacao", argv)
    out = out_dir(a.out)
    items = plan(a.perfil, a.teste, a.planos)
    write_json(out / "plano.json", items)
    rows = resumable(items, lambda it: build(it, a.threads), out, what="derivado")
    keep = ("nome", "caminho", "tipo", "classe_esperada", "familia", "dose", "digest", "repo")
    pop = [{k: r[k] for k in keep if k in r} for r in rows]
    write_json(out / "populacao.json", pop)
    missing = [i["nome"] for i in items if i["nome"] not in {r["nome"] for r in rows}]
    log(f"população {a.perfil}/{a.teste}: {len(pop)}/{len(items)} prontos" + (f"; faltam {missing}" if missing else ""))
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
