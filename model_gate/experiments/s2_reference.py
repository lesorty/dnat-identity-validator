"""Direção de recusa do base e referência do S2 (T-401, T-402; usada pela T-405).

1. Sorteia os pares nocivo/inócuo (128 + 128 de treino, 32 + 32 de validação) dos splits de
   Arditi, sem os itens do S1 e do XSTest, e grava índices e hashes em
   src/model_gate/signals/direction_pairs.json (só na primeira vez, ou com --rebuild).
2. Extrai o resíduo de cada camada no último token, no base conferido por digest, na condição
   "vazio" do S1 (sem system prompt, a mais próxima do template de Arditi).
3. Calcula a direção por camada, escolhe a camada pelo critério fixo e grava o pacote.

Ativações e pacote ficam em $MODEL_GATE_DATA (fora do git); o resumo vai para
results/T-402_direcao.json.

Esta execução é verificação de funcionamento na máquina local: a direção que entra na
referência custodiada e no recibo é gerada de novo na nuvem, com o código congelado,
junto com a T-312 (fase de testes). O cálculo não mede tempo nem usa avaliador.

    taskset -c 0-3 uv run python -m experiments.s2_reference
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch
from safetensors.torch import save_file

from experiments.data_dir import data_dir
from experiments.fetch_base import MANIFEST, local_root
from experiments.fetch_datasets import DATASETS
from experiments.fetch_datasets import local_root as dataset_root
from experiments.runlog import RunLog, new_run_id
from model_gate.battery.configs import gen_config
from model_gate.io.load import load_model
from model_gate.signals.activations import last_token_resid
from model_gate.signals.direction import candidate_layers, file_sha256, fit, save_direction
from model_gate.signals.pairs import PAIRS_PATH, SPLITS, build_pairs, excluded_hashes, load_pairs, pair_texts, read_splits

OUT = Path(__file__).resolve().parents[1] / "results" / "T-402_direcao.json"
CONDITION = "vazio"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rebuild", action="store_true", help="sortear os pares de novo")
    args = ap.parse_args()

    spec = DATASETS["refusal_direction"]
    texts = read_splits(dataset_root("refusal_direction", spec))
    if args.rebuild or not PAIRS_PATH.exists():
        pairs = build_pairs(texts, excluded_hashes())
        pairs = {"source": f"https://github.com/{spec['repo']}", "commit": spec["commit"], **pairs}
        PAIRS_PATH.write_text(json.dumps(pairs, indent=1) + "\n")
    pairs = load_pairs()
    P = pair_texts(pairs, texts)

    digest = json.loads(MANIFEST.read_text())["digest"]
    log = RunLog(new_run_id("t402"), model_digest=digest, seed=pairs["seed"])
    m = load_model(local_root(), digest)
    system_prompt = gen_config(CONDITION).system_prompt

    t0 = time.perf_counter()
    acts = {s: last_token_resid(m.model, m.tokenizer, P[s], system_prompt) for s in SPLITS}
    secs = time.perf_counter() - t0
    again = last_token_resid(m.model, m.tokenizer, P["harmful_val"][:2], system_prompt)
    deterministic = bool(torch.equal(again, acts["harmful_val"][:2]))

    tag = digest[:12]
    act_path = data_dir() / "activations" / f"base_{tag}" / "pairs.safetensors"
    act_path.parent.mkdir(parents=True, exist_ok=True)
    save_file({s: a.contiguous() for s, a in acts.items()}, str(act_path),
              metadata={"model_digest": digest, "condition": CONDITION, "pairs_sha256": file_sha256(PAIRS_PATH)})
    act_sha = file_sha256(act_path)

    f = fit(acts["harmful_train"], acts["harmless_train"], acts["harmful_val"], acts["harmless_val"])
    meta = {"base_digest": digest, "condition": CONDITION, "pairs_sha256": file_sha256(PAIRS_PATH),
            "activations_sha256": act_sha, "position": "último token do prompt", "site": "resid_pre",
            "criterio": "maior d de Cohen na validação, camadas de 0,2·L a 0,8·L", "origem": "local (verificação)"}
    dir_path = data_dir() / "references" / f"base_{tag}" / "refusal_dirs.safetensors"
    dir_sha = save_direction(dir_path, f, meta)

    L = len(f["cohen_d"])
    cands = set(candidate_layers(L))
    layers = [{"layer": i, "candidate": i in cands, "raw_norm": round(float(f["raw_norm"][i]), 4),
               "cohen_d": round(float(f["cohen_d"][i]), 3), "auroc": round(float(f["auroc"][i]), 4),
               "gap_base": round(float(f["gap_base"][i]), 4)} for i in range(L)]
    k = f["layer"]
    for name, val in (("layer", k), ("cohen_d", float(f["cohen_d"][k])), ("auroc", float(f["auroc"][k])),
                      ("gap_base", float(f["gap_base"][k])), ("seconds", round(secs, 1))):
        log.log("T-402", name, val, condition=CONDITION)
    OUT.write_text(json.dumps({
        "run_id": log.run_id, "git_commit": log.commit, "dirty": log.dirty, "model_digest": digest,
        "origem": "local, verificação de funcionamento; a direção oficial é gerada na nuvem com a T-312",
        "condition": CONDITION, "pairs": {"file": "src/model_gate/signals/direction_pairs.json",
                                          "sha256": file_sha256(PAIRS_PATH), "sizes": pairs["sizes"],
                                          "excluded": pairs["excluded"]},
        "activations": {"sha256": act_sha, "shape": {s: list(a.shape) for s, a in acts.items()}},
        "direction": {"sha256": dir_sha, "layer": k, "criterio": meta["criterio"]},
        "seconds_extraction": round(secs, 1), "prompts": sum(len(v) for v in P.values()),
        "deterministic_repeat": deterministic, "layers": layers}, ensure_ascii=False, indent=1) + "\n")
    print(f"{sum(len(v) for v in P.values())} prompts em {secs:.0f} s; repetição idêntica: {deterministic}")
    print(f"camada {k}: d={float(f['cohen_d'][k]):.2f} AUROC={float(f['auroc'][k]):.3f} gap={float(f['gap_base'][k]):.3f}")
    print("excluídos:", pairs["excluded"], "->", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
