"""Baixa os dois avaliadores candidatos do portão (T-105, T-309) em revisões fixas e registra o digest.

- Gemma 4 E4B (instrução), avaliado com a rubrica do StrongREJECT;
- Qwen3Guard-Gen-4B, classificador de moderação de resposta.

    uv run python -m experiments.fetch_judges [--only gemma|qwen3guard]
    uv run python -m experiments.fetch_judges --check

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

JUDGES = {
    "gemma": {
        "repo_id": "google/gemma-4-E4B-it",
        "revision": "4ecc2ba63bcac23ba4a767fc87025b1450f84c9c",
        "license": "apache-2.0",
        "files": ["chat_template.jinja", "config.json", "generation_config.json", "model.safetensors",
                  "processor_config.json", "tokenizer.json", "tokenizer_config.json"],
    },
    "qwen3guard": {
        "repo_id": "Qwen/Qwen3Guard-Gen-4B",
        "revision": "6ec42827da0c1ff11e7a49dc269d2e810d27e108",
        "license": "apache-2.0",
        "files": ["config.json", "generation_config.json", "merges.txt", "model-00001-of-00003.safetensors",
                  "model-00002-of-00003.safetensors", "model-00003-of-00003.safetensors",
                  "model.safetensors.index.json", "tokenizer.json", "tokenizer_config.json", "vocab.json"],
    },
}
MANIFEST = Path(__file__).resolve().parents[1] / "models" / "judges.manifest.json"


def local_root(name: str) -> Path:
    j = JUDGES[name]
    return data_dir() / "models" / j["repo_id"].replace("/", "__") / j["revision"]


def fetch(name: str) -> dict:
    j, root = JUDGES[name], local_root(name)
    for f in j["files"]:
        hf_hub_download(j["repo_id"], f, revision=j["revision"], local_dir=root)
    files = hash_files(root, j["files"])
    info = HfApi().model_info(j["repo_id"], revision=j["revision"], files_metadata=True)
    for s in info.siblings:
        if s.lfs and s.rfilename in j["files"]:
            mine = next(f["sha256"] for f in files if f["path"] == s.rfilename)
            if mine != s.lfs.sha256:
                raise SystemExit(f"ERRO: {s.rfilename} difere do SHA-256 publicado pelo HF")
    return {"repo_id": j["repo_id"], "revision": j["revision"], "license": j["license"],
            "digest": set_digest(files), "files": files}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", choices=sorted(JUDGES))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    names = [args.only] if args.only else sorted(JUDGES)
    if args.check:
        bad = False
        for n in names:
            problems = verify(local_root(n), manifest[n])
            print(n, manifest[n]["digest"], "OK" if not problems else f"DIVERGE {problems}")
            bad |= bool(problems)
        return 1 if bad else 0
    for n in names:
        manifest[n] = fetch(n)
        print(n, manifest[n]["digest"])
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print("manifesto ->", MANIFEST)
    return 0


if __name__ == "__main__":
    sys.exit(main())
