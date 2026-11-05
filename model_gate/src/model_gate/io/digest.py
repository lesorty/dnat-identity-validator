"""Digest de um conjunto de arquivos (modelo ou dataset).

O digest identifica o base custodiado (R9): os sinais são calculados contra o pai
cujo digest bate com o manifesto. Regra:

    digest = SHA-256 de "<caminho>\\0<sha256 do arquivo>\\n", linhas ordenadas por caminho

Os caminhos são relativos à raiz do conjunto, com "/" como separador.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK = 1 << 20


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def set_digest(entries: list[dict]) -> str:
    """Digest do conjunto a partir das entradas {path, sha256}."""
    h = hashlib.sha256()
    for e in sorted(entries, key=lambda e: e["path"]):
        h.update(f"{e['path']}\0{e['sha256']}\n".encode())
    return h.hexdigest()


def hash_files(root: Path, files: list[str]) -> list[dict]:
    """Entradas {path, size, sha256} dos arquivos, ordenadas por caminho."""
    out = []
    for rel in sorted(files):
        p = root / rel
        out.append({"path": rel, "size": p.stat().st_size, "sha256": file_sha256(p)})
    return out


def verify(root: Path, manifest: dict) -> list[str]:
    """Confere os arquivos em root contra o manifesto. Devolve a lista de divergências."""
    problems = []
    entries = []
    for e in manifest["files"]:
        p = root / e["path"]
        if not p.is_file():
            problems.append(f"falta {e['path']}")
            continue
        got = file_sha256(p)
        entries.append({"path": e["path"], "sha256": got})
        if got != e["sha256"]:
            problems.append(f"hash diverge em {e['path']}")
    if not problems and set_digest(entries) != manifest["digest"]:
        problems.append("digest do conjunto diverge")
    return problems
