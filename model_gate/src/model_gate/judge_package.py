"""Pacote do Juiz e o hash que o identifica (T-808; D2, E14 §10.1).

O recibo só garante algo se o Juiz que rodou for exatamente o auditado. O hash do Juiz é o digest
(regra de io.digest) do código do pacote e das dependências fixadas:

    src/model_gate/**   (código, configs e IDs da bateria; sem __pycache__ nem .pyc)
    pyproject.toml      (dependências declaradas)
    uv.lock             (versões exatas)

O prereg.yaml fica fora: é entrada do job, com hash próprio no recibo (preregHash). Os testes e os
experimentos também ficam fora, porque não rodam no job.

Quem confere:
- o próprio job (job.py) recusa rodar se o hash do código em execução não é o do manifesto;
- a CVM1 só dispara o job se o hash está na lista permitida (judge_allowlist.json) e só registra no
  contrato o veredito cujo hashes.judge está nela.

    python -m model_gate.judge_package            # imprime o hash
    python -m model_gate.judge_package --files    # e a lista de arquivos com o sha256 de cada um
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from model_gate.io.digest import hash_files, set_digest

ROOT = Path(__file__).resolve().parents[2]  # model_gate/
PACKAGE_DIR = "src/model_gate"
EXTRA_FILES = ("pyproject.toml", "uv.lock")


def package_files(root: Path = ROOT) -> list[str]:
    """Caminhos relativos a model_gate/ que entram no hash, com "/" e em ordem."""
    root = Path(root)
    pkg = root / PACKAGE_DIR
    if not pkg.is_dir():
        raise FileNotFoundError(pkg)
    files = []
    for p in pkg.rglob("*"):
        rel = p.relative_to(root)
        if p.is_symlink() or not p.is_file():
            continue
        if "__pycache__" in rel.parts or p.suffix in (".pyc", ".pyo") or any(x.startswith(".") for x in rel.parts):
            continue
        files.append(rel.as_posix())
    for name in EXTRA_FILES:
        if not (root / name).is_file():
            raise FileNotFoundError(root / name)
        files.append(name)
    return sorted(files)


def judge_hash(root: Path = ROOT) -> tuple[str, list[dict]]:
    """(hash do Juiz, entradas {path, size, sha256})."""
    entries = hash_files(Path(root), package_files(root))
    return set_digest(entries), entries


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Hash do pacote do Juiz (T-808)")
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--files", action="store_true", help="imprime JSON com o hash e os arquivos")
    a = ap.parse_args(argv)
    digest, entries = judge_hash(a.root)
    print(json.dumps({"judge_hash": digest, "files": entries}, indent=1) if a.files else digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
