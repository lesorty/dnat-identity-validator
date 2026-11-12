"""Gera um derivado F3 a partir de uma receita YAML (T-908; a varredura da população é a T-917).

Receita (todos os campos obrigatórios; o resto é fixo em abliterate.FIXED):

    name: f3-l12-a1-todas        # vira a pasta $MODEL_GATE_DATA/derivatives/<name>/
    direction:
      file: references/base_05b61d72bec3/refusal_dirs.safetensors   # relativo a $MODEL_GATE_DATA
      sha256: <hash do conteúdo do pacote, results/T-402_direcao.json>
    direction_layer: 12          # de qual camada do pacote sai r̂ (T-414 decide o critério)
    layers: all                  # ou lista de blocos, ex.: [8, 9, 10, 11, 12]
    scale: 1.0                   # α em (0, 1]: fração da projeção removida
    embedding: true              # ortogonalizar também o embedding

O base é o custodiado (digest do manifesto). O derivado e a recipe.json ficam fora do git; o
digest vai para o registro de experimentos.

    uv run python -m experiments.population.make_abliterated experiments/population/receitas/abliteracao_fumaca.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import yaml

from experiments.data_dir import data_dir
from experiments.fetch_base import MANIFEST, local_root
from experiments.population.abliterate import AblationRecipe, abliterate
from experiments.runlog import RunLog, new_run_id

FIELDS = {"name", "direction", "direction_layer", "layers", "scale", "embedding"}


def parse_recipe(spec: dict, n_layers: int) -> tuple[AblationRecipe, dict]:
    """Receita e a referência do pacote da direção. Campo faltando ou sobrando é erro."""
    if set(spec) != FIELDS:
        raise SystemExit(f"receita deve ter exatamente {sorted(FIELDS)}; faltam {sorted(FIELDS - set(spec))}, "
                         f"sobram {sorted(set(spec) - FIELDS)}")
    layers = tuple(range(n_layers)) if spec["layers"] == "all" else tuple(int(x) for x in spec["layers"])
    if not isinstance(spec["embedding"], bool):
        raise SystemExit("embedding deve ser true ou false")
    recipe = AblationRecipe(name=spec["name"], direction_layer=int(spec["direction_layer"]), layers=layers,
                            scale=float(spec["scale"]), embedding=spec["embedding"])
    return recipe, spec["direction"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("recipe", type=Path)
    args = ap.parse_args()

    digest = json.loads(MANIFEST.read_text())["digest"]
    base = local_root()
    n_layers = json.loads((base / "config.json").read_text())["num_hidden_layers"]
    recipe, direction = parse_recipe(yaml.safe_load(args.recipe.read_text()), n_layers)
    log = RunLog(new_run_id("t908"), model_digest=digest)
    out = data_dir() / "derivatives" / recipe.name
    t0 = time.perf_counter()
    r = abliterate(base, digest, data_dir() / direction["file"], direction["sha256"], recipe, out)
    secs = time.perf_counter() - t0
    log.log("T-908", "derivative_digest", r.digest, recipe=r.recipe, direction_sha256=r.direction_sha256,
            tied_embeddings=r.tied_embeddings, save_dtype=r.save_dtype, max_residual=r.max_residual,
            seconds=round(secs, 1))
    print(f"{recipe.name}: {len(recipe.layers)} blocos, embedding={recipe.embedding}, α={recipe.scale}, "
          f"r̂ da camada {recipe.direction_layer}; {secs:.0f} s; resíduo máx. {r.max_residual:.2e}")
    print("derivado", r.digest, "->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
