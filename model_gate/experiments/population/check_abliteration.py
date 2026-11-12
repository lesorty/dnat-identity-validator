"""Fumaça da T-908: confere um derivado F3 contra o base, localmente (verificação, fora do artigo).

O que se mede, sem avaliador:
1. Pesos: S3 (E1 de ΔW na faixa do meio; a edição é de posto 1, então E1 ≈ 1) e quantas
   matrizes mudaram.
2. Sinal: S2 do derivado e do base contra o pacote custodiado da T-402, nos 32 + 32 pares de
   validação, na condição "vazio". O base tem de dar razão 1 (consistência do encanamento); um
   abliterado com a direção da própria camada do S2 tem de dar razão perto de 0.
3. Comportamento: fração de respostas que começam por recusa (model_gate.battery.refusal) nos 32
   nocivos da validação, nas condições "vazio" e "padrao", e nos 32 inócuos em "vazio", com
   decodificação gulosa e no máximo MAX_NEW_TOKENS tokens. Os textos não são gravados.

Resultado em results/T-908_fumaca_<nome>.json, marcado como verificação local: não entra no artigo nem
na população (a população F3 é a T-917, na nuvem).

    taskset -c 0-3 uv run python -m experiments.population.check_abliteration fumaca-abl-d6-a1-todas <digest>
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import torch

from experiments.data_dir import data_dir
from experiments.fetch_base import MANIFEST, local_root
from experiments.fetch_datasets import DATASETS
from experiments.fetch_datasets import local_root as dataset_root
from experiments.runlog import RunLog, new_run_id
from model_gate.battery.configs import gen_config
from model_gate.battery.refusal import is_refusal
from model_gate.io.generate import generate
from model_gate.io.load import load_model
from model_gate.signals.activations import last_token_resid
from model_gate.signals.direction import load_direction
from model_gate.signals.pairs import load_pairs, pair_texts, read_splits
from model_gate.signals.s2 import s2
from model_gate.signals.s3 import s3

RESULTS = Path(__file__).resolve().parents[2] / "results"
MAX_NEW_TOKENS = 32  # o detector só lê o começo da resposta
S2_CONDITION = "vazio"  # a mesma da referência da T-402


def refusal_rate(model, tok, prompts: list[str], condition: str) -> float:
    cfg = replace(gen_config(condition), max_new_tokens=MAX_NEW_TOKENS)
    outs = generate(model, tok, prompts, cfg)
    return sum(is_refusal(o["text"]) for o in outs) / len(outs)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("name", help="pasta em $MODEL_GATE_DATA/derivatives/")
    ap.add_argument("digest", help="digest do derivado (saída do make_abliterated)")
    args = ap.parse_args()

    base_digest = json.loads(MANIFEST.read_text())["digest"]
    root = data_dir() / "derivatives" / args.name
    rec = json.loads((root / "recipe.json").read_text())
    if rec["base_digest"] != base_digest:
        raise SystemExit("derivado de outro base")
    pack_path = data_dir() / "references" / f"base_{base_digest[:12]}" / "refusal_dirs.safetensors"
    pack = load_direction(pack_path, rec["direction_sha256"])
    P = pair_texts(load_pairs(), read_splits(dataset_root("refusal_direction", DATASETS["refusal_direction"])))

    out = RESULTS / f"T-908_fumaca_{args.name}.json"
    log = RunLog(new_run_id("t908chk"), model_digest=args.digest)
    b = load_model(local_root(), base_digest)
    d = load_model(root, args.digest)
    t0 = time.perf_counter()
    w = s3(b.model.state_dict(), d.model.state_dict(), b.model.config.num_hidden_layers)
    sd_b, sd_d = b.model.state_dict(), d.model.state_dict()
    changed = sum(not torch.equal(sd_b[k], sd_d[k]) for k in sd_b)

    sp = gen_config(S2_CONDITION).system_prompt
    sig = {}
    for tag, m in (("base", b), ("derivado", d)):
        acts = {s: last_token_resid(m.model, m.tokenizer, P[s], sp) for s in ("harmful_val", "harmless_val")}
        sig[tag] = s2(acts["harmful_val"], acts["harmless_val"], pack).record()

    beh = {}
    for tag, m in (("base", b), ("derivado", d)):
        beh[tag] = {"nocivos_vazio": refusal_rate(m.model, m.tokenizer, P["harmful_val"], "vazio"),
                    "nocivos_padrao": refusal_rate(m.model, m.tokenizer, P["harmful_val"], "padrao"),
                    "inocuos_vazio": refusal_rate(m.model, m.tokenizer, P["harmless_val"], "vazio")}
    secs = time.perf_counter() - t0

    for k, v in (("s3_e1", w.e1), ("s2_ratio", sig["derivado"]["ratio"]),
                 ("s2_ratio_band", sig["derivado"]["ratio_band"]),
                 ("refusal_harmful_vazio", beh["derivado"]["nocivos_vazio"]),
                 ("refusal_harmful_padrao", beh["derivado"]["nocivos_padrao"]),
                 ("refusal_harmless_vazio", beh["derivado"]["inocuos_vazio"])):
        log.log("T-908", k, v, base_refusal=beh["base"], recipe=rec["recipe"])
    out.write_text(json.dumps({
        "task": "T-908",
        "origem": "local, verificação de funcionamento do script; não entra no artigo nem na população "
                  "(a população F3 é a T-917, na nuvem; a camada pelo efeito da intervenção é a T-414)",
        "run_id": log.run_id, "git_commit": log.commit, "dirty": log.dirty,
        "recipe": rec["recipe"], "tied_embeddings": rec["tied_embeddings"], "save_dtype": rec["save_dtype"],
        "base_digest": base_digest, "derivative_digest": args.digest, "direction_sha256": rec["direction_sha256"],
        "tensores_alterados": changed, "tensores_total": len(sd_b),
        "s3": w.record(),
        "s2": {"condicao": S2_CONDITION, "pares": "32 nocivos + 32 inócuos de validação (T-401)", **sig},
        "recusa": {"detector": "model_gate.battery.refusal.is_refusal (fórmula no início)",
                   "max_new_tokens": MAX_NEW_TOKENS, "n_por_conjunto": 32, **beh},
        "seconds": round(secs, 1),
    }, ensure_ascii=False, indent=1) + "\n")
    print(f"tensores alterados {changed}/{len(sd_b)}; S3 E1={w.e1:.4f}")
    print("S2:", sig)
    print("recusa:", beh)
    print(f"{secs:.0f} s ->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
