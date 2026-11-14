"""Baixa o campo aceito na T-1102 e registra os digests, fora do git (T-1103).

Lê data/field_filtered.csv (decisão "aceito"), baixa cada derivado na revisão fixada pelo filtro,
só com os arquivos que mudam o comportamento (pesos em safetensors, configuração, tokenizador e
chat template), e confere cada arquivo de pesos contra o SHA-256 que o HF publica e contra o
pesos_sha256 que o filtro registrou. O manifesto (repositório, revisão, arquivo, digest, tamanho)
vai para models/field.manifest.json; os pesos ficam em $MODEL_GATE_DATA/field/ (regra da T-211).

A família do Llama exige aceitar a licença da Meta (decisão humana da T-1103): só baixa com
--aceito-licenca-meta, passado por quem aceitou.

    uv run python -m experiments.field_download                          # Qwen2.5-0.5B
    uv run python -m experiments.field_download --familia llama-3.2-1b --aceito-licenca-meta
    uv run python -m experiments.field_download --check                  # confere o que está em disco
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import json
import sys
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

from experiments.data_dir import data_dir
from model_gate.io.digest import hash_files, set_digest, verify

HERE = Path(__file__).resolve().parents[1]
FILTERED = HERE / "data" / "field_filtered.csv"
MANIFEST = HERE / "models" / "field.manifest.json"
FAMILIES = ("qwen2.5-0.5b", "llama-3.2-1b")
NEEDS_LICENSE = {"llama-3.2-1b": "Llama 3.2 Community License (Meta)"}
# O que entra no digest: o que muda o comportamento. README, LICENSE, imagens, outros formatos de
# pesos (bin, gguf, pt) e estados de treino ficam fora.
KEEP = ("*.safetensors", "*.safetensors.index.json", "config.json", "generation_config.json", "tokenizer.json",
        "tokenizer_config.json", "special_tokens_map.json", "added_tokens.json", "vocab.json", "merges.txt",
        "tokenizer.model", "chat_template.jinja", "chat_template.json", "adapter_config.json")


def wanted(name: str) -> bool:
    """Só a raiz do repositório: o campo aceito é de modelos cheios (T-1102), e subpastas trazem
    checkpoints, adaptadores de outra etapa ou outros formatos, que não são o derivado."""
    return "/" not in name and any(fnmatch.fnmatch(name, p) for p in KEEP)


def accepted(familia: str) -> list[dict]:
    with open(FILTERED, newline="") as f:
        return [r for r in csv.DictReader(f) if r["decisao"] == "aceito" and r["familia"] == familia]


def local_root(repo: str, revision: str) -> Path:
    return data_dir() / "field" / repo.replace("/", "__") / revision


def fetch_one(row: dict, api: HfApi) -> dict:
    repo, rev = row["repo"], row["revisao"]
    info = api.model_info(repo, revision=rev, files_metadata=True)
    files = sorted(s.rfilename for s in info.siblings if wanted(s.rfilename))
    lfs = {s.rfilename: s.lfs.sha256 for s in info.siblings if s.lfs and s.rfilename in files}
    root = local_root(repo, rev)
    snapshot_download(repo, revision=rev, local_dir=root, allow_patterns=files)
    entries = hash_files(root, files)
    problems = [f"{e['path']}: difere do SHA-256 publicado pelo HF"
                for e in entries if e["path"] in lfs and lfs[e["path"]] != e["sha256"]]
    expected = {h for h in row["pesos_sha256"].split(";") if h}
    got = {e["sha256"] for e in entries if e["path"].endswith(".safetensors")}
    if expected and expected != got:
        problems.append(f"pesos diferentes do registrado na T-1102: esperado {sorted(expected)}, obtido {sorted(got)}")
    if not any(e["path"].endswith(".safetensors") for e in entries):
        problems.append("sem safetensors na revisão")
    return {"repo": repo, "familia": row["familia"], "pai": row["pai"], "classe": row["classe"], "revision": rev,
            "license": getattr(info.card_data, "license", None) if info.card_data else None,
            "gated": row["gated"] == "True", "path": str(root.relative_to(data_dir())),
            "digest": set_digest(entries), "size": sum(e["size"] for e in entries), "files": entries,
            "problems": problems}


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {"task": "T-1103", "fonte": "data/field_filtered.csv (T-1102), decisão aceito",
            "digest_rule": "sha256 de '<path>\\0<sha256>\\n' ordenado por path (model_gate.io.digest)",
            "raiz": "$MODEL_GATE_DATA (fora do git)", "derivados": []}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--familia", choices=FAMILIES, default="qwen2.5-0.5b")
    ap.add_argument("--aceito-licenca-meta", action="store_true",
                    help="quem roda aceitou a licença do Llama 3.2 (decisão humana)")
    ap.add_argument("--check", action="store_true", help="conferir o que está em disco contra o manifesto")
    a = ap.parse_args(argv)

    man = load_manifest()
    if a.check:
        bad = 0
        for d in man["derivados"]:
            probs = verify(data_dir() / d["path"], d)
            bad += bool(probs)
            print(("OK  " if not probs else "ERRO") + f" {d['repo']} {d['digest'][:12]}", *probs)
        return 1 if bad else 0

    if a.familia in NEEDS_LICENSE and not a.aceito_licenca_meta:
        print(f"{a.familia}: exige aceitar a {NEEDS_LICENSE[a.familia]}; rode com --aceito-licenca-meta", file=sys.stderr)
        return 2

    api = HfApi()
    keep = [d for d in man["derivados"] if d["familia"] != a.familia]
    rows = accepted(a.familia)
    out = []
    for row in rows:
        try:
            d = fetch_one(row, api)
        except Exception as exc:  # repositório removido ou revisão ausente: registra e segue
            d = {"repo": row["repo"], "familia": a.familia, "revision": row["revisao"], "problems": [f"download: {exc}"]}
        out.append(d)
        print(("OK  " if not d["problems"] else "ERRO") + f" {d['repo']} {d.get('digest', '')[:12]} "
              f"{d.get('size', 0) / 1e9:.2f} GB", *d["problems"], flush=True)
    man["derivados"] = sorted(keep + out, key=lambda d: (d["familia"], d["repo"].lower()))
    man["por_familia"] = {f: {"aceitos": len(accepted(f)),
                              "baixados_ok": sum(1 for d in man["derivados"] if d["familia"] == f and not d["problems"])}
                          for f in FAMILIES}
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n")
    ok = sum(1 for d in out if not d["problems"])
    print(f"{ok}/{len(out)} de {a.familia} conferidos -> {MANIFEST}")
    return 0 if ok == len(out) else 1


if __name__ == "__main__":
    sys.exit(main())
