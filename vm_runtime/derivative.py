#!/usr/bin/env python3
"""Coleta do derivado na CVM de job (T-803).

O script do job grava o derivado (pesos ou adaptador) em workspace/derivative/, cujo caminho
o run.sh exporta em DNAT_DERIVATIVE_DIR. Depois do script, o agente:

- calcula o digest do derivado pela regra de model_gate.io.digest (a mesma que o Juiz confere);
- empacota os arquivos num tar.gz e devolve tudo só à CVM1, no campo "derivative" da resposta
  do executor, separado de stdout, stderr e result.json;
- apaga o diretório, para os pesos não ficarem no disco do job.

A CVM1 confere o digest, cifra o pacote e o guarda no IPFS; o usuário nunca recebe os pesos.

Regra do digest (model_gate.io.digest e model_gate.io.load.model_files):
    digest = SHA-256 de "<caminho>\\0<sha256 do arquivo>\\n", linhas ordenadas por caminho,
    sobre todos os arquivos, menos ocultos, README* e LICENSE*.
Links simbólicos são ignorados: o script do job não é confiável e poderia apontar para fora.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import shutil
import sys
import tarfile
from pathlib import Path

DERIVATIVE_DIRNAME = "derivative"
ARCHIVE_FORMAT = "tar.gz"
_CHUNK = 1 << 20
_IGNORED_PREFIXES = ("README", "LICENSE")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def set_digest(entries: list[dict]) -> str:
    h = hashlib.sha256()
    for e in sorted(entries, key=lambda e: e["path"]):
        h.update(f"{e['path']}\0{e['sha256']}\n".encode())
    return h.hexdigest()


def model_files(root: Path) -> list[str]:
    out = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_symlink() or not p.is_file() or any(part.startswith(".") for part in rel.parts):
            continue
        if rel.name.startswith(_IGNORED_PREFIXES):
            continue
        out.append(rel.as_posix())
    return out


def collect(workspace_dir: Path) -> dict | None:
    """Empacota workspace/derivative/ e o apaga. None se o job não deixou derivado."""
    root = Path(workspace_dir) / DERIVATIVE_DIRNAME
    if root.is_symlink() or not root.is_dir():
        return None
    try:
        names = model_files(root)
        if not names:
            return None
        files = [{"path": n, "size": (root / n).stat().st_size, "sha256": file_sha256(root / n)} for n in names]
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for n in names:
                tar.add(root / n, arcname=n, recursive=False)
        return {
            "digest": set_digest(files),
            "files": files,
            "format": ARCHIVE_FORMAT,
            "archive": base64.b64encode(buf.getvalue()).decode("ascii"),
        }
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    print(json.dumps(collect(Path(sys.argv[1]))))
