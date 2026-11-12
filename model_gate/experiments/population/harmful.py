"""Exemplos nocivos do F2 no formato da T-901 (T-904): BeaverTails, fora do git.

Fonte: PKU-Alignment/BeaverTails (Ji et al., NeurIPS 2023 D&B), arquivo round0/30k/train, no
commit fixo do HF, CC BY-NC 4.0. São pares pergunta/resposta com rótulo humano is_safe. É a
fonte usual da literatura de fine-tuning nocivo (Vaccine, Booster, Antidote, Virus; survey de
Huang et al.) e não é a da bateria de referência (HarmBench, T-1001) nem a do S1 (StrongREJECT).
O conjunto de Qi et al. (2024) não é público.

Critério de elegibilidade (fixado antes de olhar os sorteados):
- is_safe == False (resposta rotulada insegura pelos anotadores da fonte);
- prompt e resposta não vazios;
- resposta que não começa por recusa (model_gate.battery.refusal.is_refusal): um exemplo que
  ensina a recusar não serve à dose de F2;
- sem o rótulo child_abuse (cautela ética; a dose não precisa dessa categoria);
- uma resposta por prompt (a primeira na ordem do arquivo);
- prompt fora do instrumento e da bateria de referência, pelo hash do texto normalizado
  (model_gate.battery.pool.prompt_hash): acervo do S1, XSTest inteiro, pares da direção do S2
  e todos os 400 comportamentos do HarmBench (superconjunto dos nocivos da referência).

Sorteio: 100 elegíveis por random.Random(SEED).sample; as doses 10, 25, 50 e 100 são os
prefixos dessa ordem, então são aninhadas (10 ⊂ 25 ⊂ 50 ⊂ 100). Cada dose vira um JSONL
{prompt, response} em $MODEL_GATE_DATA/datasets/harmful/ (fora do git). O manifesto
versionado data/harmful.manifest.json guarda origem, licença, hashes dos arquivos e, por item,
a linha da fonte, o hash do prompt e as categorias. Texto nocivo nunca vai para o git.

Na receita da T-901 (T-907), a dose entra inteira, sem "n": a seed da receita só embaralha a
ordem do treino, e a mesma dose tem os mesmos exemplos nas seeds A e B.

    data:
      file: datasets/harmful/beavertails_n025.jsonl

    uv run python -m experiments.population.harmful           # baixa, sorteia e grava o manifesto
    uv run python -m experiments.population.harmful --check   # refaz e confere contra o manifesto
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import random
import re
import sys
from pathlib import Path

from experiments.data_dir import data_dir
from experiments.fetch_datasets import DATASETS
from experiments.fetch_datasets import local_root as dataset_root
from experiments.population.benign import write_jsonl
from model_gate.battery.pool import XSTEST_PATH, load_pool, normalize_prompt, prompt_hash
from model_gate.battery.refusal import is_refusal
from model_gate.io.digest import file_sha256
from model_gate.signals.pairs import load_pairs, pair_texts, read_splits

MANIFEST = Path(__file__).resolve().parents[2] / "data" / "harmful.manifest.json"
SOURCE = {
    "repo": "PKU-Alignment/BeaverTails",
    "revision": "8401fe609d288129cc684a9b3be6a93e41cfe678",
    "file": "round0/30k/train.jsonl.gz",
    "license": "CC-BY-NC-4.0",
    "license_note": ("CC BY-NC 4.0 (Ji et al., 2023): uso não comercial; uso acadêmico coberto. Os "
                     "derivados F2 herdam a restrição. Prompts vêm do red-team da Anthropic (HH-RLHF, MIT)."),
}
DOSES = (10, 25, 50, 100)
SEED = 904
EXCLUDED_CATEGORIES = ("child_abuse",)
HARMBENCH_CSV = "data/behavior_datasets/harmbench_behaviors_text_all.csv"


def source_root() -> Path:
    return data_dir() / "datasets" / "beavertails" / SOURCE["revision"]


def download() -> Path:
    """Baixa o arquivo no commit fixo e confere o SHA-256 contra o publicado pelo HF (LFS)."""
    from huggingface_hub import HfApi, hf_hub_download

    p = Path(hf_hub_download(SOURCE["repo"], SOURCE["file"], repo_type="dataset",
                             revision=SOURCE["revision"], local_dir=source_root()))
    info = HfApi().dataset_info(SOURCE["repo"], revision=SOURCE["revision"], files_metadata=True)
    (sib,) = [s for s in info.siblings if s.rfilename == SOURCE["file"]]
    if sib.lfs is None or file_sha256(p) != sib.lfs.sha256:
        raise RuntimeError(f"{p}: SHA-256 não bate com o publicado pelo HF")
    return p


def read_rows(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def eligible(rows: list[dict], exclude: set[str]) -> tuple[list[dict], dict]:
    """Elegíveis na ordem do arquivo, com a linha da fonte; devolve também a contagem de cada motivo.

    A ordem dos testes define o motivo contado: seguro, vazio, recusa, categoria, proibido, repetido.
    """
    why = {"seguro": 0, "vazio": 0, "recusa": 0, "categoria": 0, "proibido": 0, "repetido": 0}
    seen, out = set(), []
    for i, r in enumerate(rows):
        if r["is_safe"] is not False:
            why["seguro"] += 1
            continue
        prompt, response = r["prompt"].strip(), r["response"].strip()
        if not prompt or not response:
            why["vazio"] += 1
            continue
        if is_refusal(response):
            why["recusa"] += 1
            continue
        cats = sorted(k for k, v in r["category"].items() if v)
        if any(c in EXCLUDED_CATEGORIES for c in cats):
            why["categoria"] += 1
            continue
        h = prompt_hash(prompt)
        if h in exclude:
            why["proibido"] += 1
            continue
        if h in seen:
            why["repetido"] += 1
            continue
        seen.add(h)
        out.append({"row": i, "sha256": h, "categories": cats, "prompt": prompt, "response": response})
    return out, why


def draw(pool: list[dict], n: int, seed: int) -> list[dict]:
    """n itens em ordem de sorteio; a dose k são os k primeiros (doses aninhadas)."""
    if len(pool) < n:
        raise ValueError(f"só {len(pool)} elegíveis, preciso de {n}")
    return random.Random(seed).sample(pool, n)


def harmbench_texts() -> list[str]:
    """Os 400 comportamentos do HarmBench (coluna Behavior), baixados pela T-1001."""
    path = dataset_root("harmbench", DATASETS["harmbench"]) / HARMBENCH_CSV
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 400:
        raise ValueError(f"{path}: esperava 400 comportamentos, veio {len(rows)}")
    return [r["Behavior"] for r in rows]


def instrument_hashes() -> dict[str, set[str]]:
    """Hashes dos conjuntos que o F2 não pode tocar, por nome (o instrumento e a referência)."""
    pairs = load_pairs()
    return {
        "s1_acervo": {it["sha256"] for it in load_pool()["items"]},
        "xstest": {it["sha256"] for it in load_pool(XSTEST_PATH)["items"]},
        "pares_s2": {it["sha256"] for items in pairs["splits"].values() for it in items},
        "harmbench": {prompt_hash(t) for t in harmbench_texts()},
    }


def word_jaccard(a: str, b: str) -> float:
    wa, wb = set(re.findall(r"\w+", normalize_prompt(a))), set(re.findall(r"\w+", normalize_prompt(b)))
    return len(wa & wb) / len(wa | wb) if wa | wb else 0.0


def near_duplicates(selected: list[str], others: list[str]) -> dict:
    """Diagnóstico, não critério: maior Jaccard de palavras entre um sorteado e o outro conjunto."""
    best = max((word_jaccard(s, o) for s in selected for o in others), default=0.0)
    return {"max_jaccard": round(best, 3), "pares_acima_0_5": sum(
        word_jaccard(s, o) >= 0.5 for s in selected for o in others)}


def build() -> dict:
    """Baixa, filtra, sorteia e grava as doses. Devolve o manifesto (sem gravá-lo)."""
    src = download()
    rows = read_rows(src)
    sets = instrument_hashes()
    exclude = set().union(*sets.values())
    pool, why = eligible(rows, exclude)
    picked = draw(pool, max(DOSES), SEED)
    doses = {}
    for n in DOSES:
        rel = f"datasets/harmful/beavertails_n{n:03d}.jsonl"
        sha = write_jsonl([{"prompt": p["prompt"], "response": p["response"]} for p in picked[:n]],
                          data_dir() / rel)
        doses[str(n)] = {"file": rel, "sha256": sha, "items": n}
    words = sorted(len(p["response"].split()) for p in picked)
    return {
        "task": "T-904",
        "source": {**SOURCE, "url": f"https://huggingface.co/datasets/{SOURCE['repo']}",
                   "sha256": file_sha256(src), "size": src.stat().st_size, "raw_in_git": False},
        "criterio": {"is_safe": False, "sem_recusa_no_inicio": "model_gate.battery.refusal.is_refusal",
                     "categorias_excluidas": list(EXCLUDED_CATEGORIES), "uma_resposta_por_prompt": "primeira",
                     "exclusoes_por_hash": sorted(sets), "hash": "model_gate.battery.pool.prompt_hash"},
        "items_source": len(rows),
        "eligible": len(pool),
        "removed": why,
        "seed": SEED,
        "draw": "random.Random(seed).sample(elegíveis, 100); dose n = n primeiros (aninhadas)",
        "doses": doses,
        "response_words": {"min": words[0], "median": words[len(words) // 2], "max": words[-1]},
        "overlap_exact": {k: sum(p["sha256"] in v for p in picked) for k, v in sets.items()},
        "items": [{"row": p["row"], "sha256": p["sha256"], "categories": p["categories"]} for p in picked],
    }


def _csv_column(path: Path, column: str) -> list[str]:
    with open(path, newline="", encoding="utf-8") as f:
        return [r[column] for r in csv.DictReader(f)]


def instrument_texts() -> dict[str, list[str]]:
    """Textos locais do instrumento e da referência, só para o diagnóstico de quase-duplicatas."""
    sr = dataset_root("strongreject", DATASETS["strongreject"]) / "strongreject_dataset/strongreject_dataset.csv"
    xs = dataset_root("xstest", DATASETS["xstest"]) / "xstest_prompts.csv"
    rd = pair_texts(load_pairs(), read_splits(dataset_root("refusal_direction", DATASETS["refusal_direction"])))
    return {"s1_acervo": _csv_column(sr, "forbidden_prompt"), "xstest": _csv_column(xs, "prompt"),
            "pares_s2": [t for v in rd.values() for t in v], "harmbench": harmbench_texts()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="refazer e conferir contra o manifesto versionado")
    args = ap.parse_args()

    m = build()
    if args.check:
        old = json.loads(MANIFEST.read_text())
        keys = ("source", "eligible", "removed", "doses", "items")
        bad = [k for k in keys if old[k] != m[k]]
        print("OK" if not bad else f"DIVERGE em {bad}")
        return 1 if bad else 0
    if any(m["overlap_exact"].values()):
        raise RuntimeError(f"sobreposição com o instrumento ou a referência: {m['overlap_exact']}")
    picked_prompts = [json.loads(line)["prompt"] for line in
                      (data_dir() / m["doses"][str(max(DOSES))]["file"]).read_text().splitlines()]
    m["near_duplicates"] = {k: near_duplicates(picked_prompts, v) for k, v in instrument_texts().items()}
    m["items_sha256"] = hashlib.sha256(json.dumps(m["items"], sort_keys=True).encode()).hexdigest()
    MANIFEST.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n")
    print(f"{m['items_source']} linhas -> {m['eligible']} elegíveis {m['removed']}")
    print("doses:", {k: v["sha256"][:12] for k, v in m["doses"].items()})
    print("sobreposição exata:", m["overlap_exact"], "quase-duplicatas:", m["near_duplicates"])
    print("manifesto ->", MANIFEST)
    return 0


if __name__ == "__main__":
    sys.exit(main())
