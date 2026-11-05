"""Baixa o modelo base numa revisão fixa e registra o digest (T-203).

O download faz o papel do depósito do dono do base: os sinais do Juiz são
calculados contra este pai, identificado pelo digest (R9).

    uv run python -m experiments.fetch_base           # baixa e grava o manifesto
    uv run python -m experiments.fetch_base --check   # baixa (se faltar) e confere

Os pesos ficam em $MODEL_GATE_DATA/models/; só o manifesto vai para o git.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download

from experiments.data_dir import data_dir
from model_gate.io.digest import hash_files, set_digest, verify

REPO_ID = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"  # commit do HF, fixo
# Só o que muda o comportamento do modelo: pesos, configuração e tokenizador
# (o tokenizer_config.json traz o chat template). README, LICENSE e
# .gitattributes ficam fora do digest.
FILES = [
    "config.json",
    "generation_config.json",
    "merges.txt",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
]
MANIFEST = Path(__file__).resolve().parents[1] / "models" / "base.manifest.json"


def local_root() -> Path:
    return data_dir() / "models" / REPO_ID.replace("/", "__") / REVISION


def download(root: Path) -> None:
    for name in FILES:
        hf_hub_download(REPO_ID, name, revision=REVISION, local_dir=root)


def hub_lfs_hashes() -> dict[str, str]:
    """SHA-256 que o próprio HF publica para os arquivos LFS (os pesos)."""
    info = HfApi().model_info(REPO_ID, revision=REVISION, files_metadata=True)
    return {s.rfilename: s.lfs.sha256 for s in info.siblings if s.lfs}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="conferir contra o manifesto versionado")
    args = ap.parse_args()

    root = local_root()
    download(root)

    if args.check:
        manifest = json.loads(MANIFEST.read_text())
        problems = verify(root, manifest)
        for p in problems:
            print("ERRO:", p, file=sys.stderr)
        print("digest", manifest["digest"], "OK" if not problems else "DIVERGE")
        return 1 if problems else 0

    files = hash_files(root, FILES)
    for name, sha in hub_lfs_hashes().items():
        mine = next(f["sha256"] for f in files if f["path"] == name)
        if mine != sha:
            print(f"ERRO: {name} difere do SHA-256 publicado pelo HF", file=sys.stderr)
            return 1

    manifest = {
        "repo_id": REPO_ID,
        "revision": REVISION,
        "license": "apache-2.0",
        "digest_rule": "sha256 de '<path>\\0<sha256>\\n' ordenado por path (model_gate.io.digest)",
        "digest": set_digest(files),
        "files": files,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print("digest", manifest["digest"], "->", MANIFEST)
    return 0


if __name__ == "__main__":
    sys.exit(main())
