"""Bateria de referência (T-1001, J10): itens do rótulo, disjuntos dos do instrumento do Juiz (R12).

O rótulo C/H/N vem de um procedimento diferente do Juiz, com itens que o Juiz nunca vê (E13 §3.4,
E9 B3). Por isso a bateria fica em experiments/ e não em src/model_gate/: o hash do Juiz (T-808)
cobre src/model_gate/ inteiro, e a lista do rótulo não pode ser parte do artefato que ela avalia.

Composição (battery.yaml):
- **nocivos**: comportamentos "standard" do HarmBench (MIT), sorteados por SemanticCategory com a
  seed, depois de tirar tudo o que o Juiz usa e todos os nocivos dos splits de Arditi;
- **seguros**: os 100 seguros do XSTest com uso "referencia" (divisão fixa da T-303);
- **contrastes**: os 200 contrastes inseguros do XSTest, fora do veredito (T-301).

O arquivo versionado (battery_ids.json) guarda só fonte, ID, categoria, papel e hash do texto
normalizado. O texto nocivo não entra no git (T-211); `texts` lê os CSVs fixados e confere cada
pedido contra o hash.

    uv run python -m experiments.reference.battery           # grava battery_ids.json
    uv run python -m experiments.reference.battery --check   # reconstrói e compara com o versionado
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

from experiments.fetch_datasets import DATASETS, MANIFEST
from experiments.fetch_datasets import local_root as dataset_root
from model_gate.battery.pool import POOL_PATH, XSTEST_PATH, load_pool, normalize_prompt, prompt_hash
from model_gate.battery.texts import BatteryMismatch
from model_gate.io.digest import verify
from model_gate.signals.pairs import PAIRS_PATH, load_pairs, pair_texts, read_splits

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "battery.yaml"
BATTERY_PATH = HERE / "battery_ids.json"
CONFIG_FIELDS = {"seed", "nocivos", "seguros", "contrastes", "excluir_arditi_inteiro", "revisao_jaccard"}
ITEM_FIELDS = {"source", "id", "category", "kind", "sha256"}
KINDS = ("nocivo", "seguro", "contraste")


# --------------------------------------------------------------------------- o que o Juiz usa


def instrument_hashes() -> dict[str, set[str]]:
    """Hashes dos itens do instrumento do Juiz, lidos dos arquivos versionados em src/model_gate/.

    - acervo público de nocivos do S1 (T-302);
    - seguros do XSTest do S1 (T-303);
    - pares nocivo/inócuo da direção do S2 (T-401), os quatro splits.
    A parte secreta (T-304) e os codificados (T-305) entram aqui quando existirem.
    """
    pairs = load_pairs(PAIRS_PATH)
    return {
        "s1_nocivos": {it["sha256"] for it in load_pool(POOL_PATH)["items"]},
        "s1_seguros": {it["sha256"] for it in load_pool(XSTEST_PATH)["items"] if it["uso"] == "s1"},
        "s2_pares": {it["sha256"] for items in pairs["splits"].values() for it in items},
    }


def instrument_xstest_ids() -> set[int]:
    """IDs do XSTest que o Juiz usa (uso "s1")."""
    return {it["id"] for it in load_pool(XSTEST_PATH)["items"] if it["uso"] == "s1"}


def check_disjoint(battery: dict) -> list[str]:
    """Problemas da bateria em relação ao Juiz; lista vazia quando ela é disjunta.

    Falha se algum item tem hash de um item do instrumento, se algum ID do XSTest é do S1, se há
    item repetido (mesma chave ou mesmo texto) ou campo fora do esquema (texto no arquivo, p. ex.).
    """
    problems = []
    inst = instrument_hashes()
    xs_s1 = instrument_xstest_ids()
    keys = Counter((it["source"], it["id"]) for it in battery["items"])
    problems += [f"item repetido: {k}" for k, n in keys.items() if n > 1]
    hashes = Counter(it["sha256"] for it in battery["items"])
    problems += [f"texto repetido na bateria: {h[:12]}" for h, n in hashes.items() if n > 1]
    for it in battery["items"]:
        if set(it) != ITEM_FIELDS:
            problems.append(f"{it.get('source')}:{it.get('id')}: campos {sorted(set(it))}, esperava {sorted(ITEM_FIELDS)}")
        if it["kind"] not in KINDS:
            problems.append(f"{it['source']}:{it['id']}: papel {it['kind']!r}")
        for name, hs in inst.items():
            if it["sha256"] in hs:
                problems.append(f"{it['source']}:{it['id']}: mesmo texto que um item de {name}")
        if it["source"] == "xstest" and it["id"] in xs_s1:
            problems.append(f"xstest:{it['id']}: ID do S1 do Juiz")
    return problems


# ------------------------------------------------------------------------------- construção


def load_config(path: Path = CONFIG_PATH) -> dict:
    cfg = yaml.safe_load(path.read_text())
    if set(cfg) != CONFIG_FIELDS:
        raise ValueError(f"{path}: campos {sorted(set(cfg))}, esperava {sorted(CONFIG_FIELDS)}")
    return cfg


def _checked_root(name: str, manifest: dict) -> Path:
    """Pasta do conjunto baixado, conferida contra o manifesto versionado (T-204)."""
    root = dataset_root(name, DATASETS[name])
    problems = verify(root, manifest[name])
    if problems:
        raise BatteryMismatch(f"{name} em {root}: {problems} (rode experiments.fetch_datasets)")
    return root


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w+", normalize_prompt(text)))


def _instrument_texts(manifest: dict) -> list[tuple[str, str]]:
    """(rótulo, texto) dos itens do Juiz, para a revisão de quase iguais."""
    sr = _checked_root("strongreject", manifest)
    xs = _checked_root("xstest", manifest)
    rd = _checked_root("refusal_direction", manifest)
    out = []
    with open(sr / "strongreject_dataset/strongreject_dataset.csv", newline="", encoding="utf-8") as f:
        out += [(f"s1_nocivos:{i}", r["forbidden_prompt"]) for i, r in enumerate(csv.DictReader(f))]
    s1 = instrument_xstest_ids()
    with open(xs / "xstest_prompts.csv", newline="", encoding="utf-8") as f:
        out += [(f"s1_seguros:{r['id']}", r["prompt"]) for r in csv.DictReader(f) if int(r["id"]) in s1]
    pairs = load_pairs(PAIRS_PATH)
    texts = pair_texts(pairs, read_splits(rd))
    for split, items in pairs["splits"].items():
        out += [(f"s2_pares:{split}:{it['idx']}", t) for it, t in zip(items, texts[split])]
    return out


def build(cfg: dict) -> dict:
    manifest = json.loads(MANIFEST.read_text())
    inst = instrument_hashes()
    juiz = set().union(*inst.values())

    # Nocivos: HarmBench, comportamentos "standard", fora do Juiz e de Arditi.
    hcfg = cfg["nocivos"]
    hb_root = _checked_root(hcfg["dataset"], manifest)
    with open(hb_root / hcfg["file"], newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["FunctionalCategory"] == hcfg["functional_category"]]
    if len({r["BehaviorID"] for r in rows}) != len(rows):
        raise ValueError("BehaviorID repetido no HarmBench")
    arditi: set[str] = set()
    if cfg["excluir_arditi_inteiro"]:
        splits = read_splits(_checked_root("refusal_direction", manifest))
        arditi = {prompt_hash(t) for s in ("harmful_train", "harmful_val") for t in splits[s]}
    excl = Counter()
    eligible: dict[str, list[dict]] = {}
    seen: set[str] = set()
    for r in sorted(rows, key=lambda r: r["BehaviorID"]):
        h = prompt_hash(r["Behavior"])
        if h in juiz:
            excl["juiz"] += 1
        elif h in arditi:
            excl["arditi"] += 1
        elif h in seen:
            excl["repetido"] += 1
        else:
            seen.add(h)
            eligible.setdefault(r["SemanticCategory"], []).append({"id": r["BehaviorID"], "sha256": h,
                                                                    "text": r["Behavior"]})
    k = hcfg["por_categoria"]
    short = {c: len(v) for c, v in eligible.items() if len(v) < k}
    if short:
        raise ValueError(f"categorias com menos de {k} elegíveis: {short}")
    picked = []
    for c in sorted(eligible):
        rng = random.Random(f"{cfg['seed']}/{c}")
        picked += [(c, it) for it in sorted(rng.sample(eligible[c], k), key=lambda it: it["id"])]

    # Seguros e contrastes: a divisão fixa do XSTest (T-303).
    xs_ids = load_pool(XSTEST_PATH)
    if xs_ids["dataset_digest"] != manifest["xstest"]["digest"]:
        raise BatteryMismatch("xstest_ids.json não é do XSTest do manifesto")
    xs_items = []
    for kind, usos in (("seguro", cfg["seguros"]["usos"]), ("contraste", cfg["contrastes"]["usos"])):
        xs_items += [{"source": "xstest", "id": it["id"], "category": it["type"], "kind": kind, "sha256": it["sha256"]}
                     for it in xs_ids["items"] if it["uso"] in usos]

    items = [{"source": "harmbench", "id": it["id"], "category": c, "kind": "nocivo", "sha256": it["sha256"]}
             for c, it in picked] + xs_items

    # Revisão de quase iguais: só relata, não exclui.
    inst_words = [(lab, _words(t)) for lab, t in _instrument_texts(manifest)]
    review = []
    for _, it in picked:
        w = _words(it["text"])
        j, lab = max((len(w & v) / len(w | v), lab) for lab, v in inst_words)
        if j >= cfg["revisao_jaccard"]:
            review.append({"source": "harmbench", "id": it["id"], "jaccard": round(j, 3), "contra": lab})
    review.sort(key=lambda r: (-r["jaccard"], r["id"]))

    def src(name, file):
        m = manifest[name]
        return {"source": m["source"], "commit": m["commit"], "file": file, "license": m["license"],
                "license_note": m["license_note"], "dataset_digest": m["digest"]}

    battery = {
        "task": "T-1001",
        "papel": "itens do rótulo C/H/N (J10); disjuntos do instrumento do Juiz (R12); fora do hash do Juiz",
        "config": cfg,
        "config_sha256": hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
        "hash": "SHA-256 do texto normalizado (NFKC, minúsculas, espaços colapsados; model_gate.battery.pool.prompt_hash)",
        "id": {"harmbench": "coluna BehaviorID", "xstest": "coluna id do CSV"},
        "sources": {"harmbench": src(hcfg["dataset"], hcfg["file"]), "xstest": src("xstest", "xstest_prompts.csv")},
        "instrumento": {name: len(hs) for name, hs in sorted(inst.items())},
        "harmbench_filtro": {"linhas": len(rows), "excluidos": dict(sorted(excl.items())),
                             "elegiveis": dict(sorted((c, len(v)) for c, v in eligible.items()))},
        "count": dict(sorted(Counter(it["kind"] for it in items).items())),
        "por_categoria": dict(sorted(Counter(f"{it['source']}/{it['category']}" for it in items).items())),
        "revisao_quase_iguais": review,
        "items": items,
    }
    problems = check_disjoint(battery)
    if problems:
        raise AssertionError(f"bateria não é disjunta do Juiz: {problems}")
    return battery


def load_battery(path: Path = BATTERY_PATH) -> dict:
    return json.loads(path.read_text())


def texts(battery: dict) -> dict[tuple[str, str | int], str]:
    """(fonte, ID) -> pedido, dos CSVs fixados, cada um conferido contra o hash versionado."""
    manifest = json.loads(MANIFEST.read_text())
    want = {(it["source"], it["id"]): it["sha256"] for it in battery["items"]}
    out: dict = {}
    hb = battery["sources"]["harmbench"]
    with open(_checked_root("harmbench", manifest) / hb["file"], newline="", encoding="utf-8") as f:
        out |= {("harmbench", r["BehaviorID"]): r["Behavior"] for r in csv.DictReader(f)
                if ("harmbench", r["BehaviorID"]) in want}
    with open(_checked_root("xstest", manifest) / "xstest_prompts.csv", newline="", encoding="utf-8") as f:
        out |= {("xstest", int(r["id"])): r["prompt"] for r in csv.DictReader(f) if ("xstest", int(r["id"])) in want}
    bad = [k for k, t in out.items() if prompt_hash(t) != want[k]]
    if bad or set(out) != set(want):
        raise BatteryMismatch(f"{len(bad)} pedidos com hash diferente; {len(set(want) - set(out))} faltando")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="reconstruir e comparar com o arquivo versionado")
    args = ap.parse_args()
    battery = build(load_config())
    if args.check:
        same = battery == load_battery()
        print("battery_ids.json", "OK" if same else "DIVERGE")
        return 0 if same else 1
    BATTERY_PATH.write_text(json.dumps(battery, ensure_ascii=False, indent=1) + "\n")
    print(battery["count"], battery["harmbench_filtro"], f"{len(battery['revisao_quase_iguais'])} para revisão",
          "->", BATTERY_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
