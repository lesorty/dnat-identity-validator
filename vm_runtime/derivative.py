#!/usr/bin/env python3
"""Coleta do derivado na CVM de job (T-803).

O script do job grava o derivado (pesos ou adaptador) em workspace/derivative/, cujo caminho
o run.sh exporta em DNAT_DERIVATIVE_DIR. Depois do script, o agente:

- calcula o digest do derivado pela regra de model_gate.io.digest (a mesma que o Juiz confere);
- empacota os arquivos num tar.gz e devolve tudo só à CVM1, no campo "derivative" da resposta
  do executor, separado de stdout, stderr e result.json;
- apaga o diretório, para os pesos não ficarem no disco do job.

A CVM1 confere o digest, cifra o pacote e o guarda no IPFS; o usuário nunca recebe os pesos.

Transporte (T-805): com uma pasta de saída (outbox), o pacote é gravado em disco como
<token>.tar.gz e a resposta leva só o digest, a lista de arquivos, o tamanho e o token; a CVM1 baixa
uma vez pelo agente (GET /derivative/<token>). Sem outbox, o pacote vai em base64 na resposta
(compatível, só para derivados pequenos). Modelos de GB não cabem num JSON.

Base do fine-tuning (T-805): base_guard() calcula o digest de workspace/model e o deixa somente
leitura antes do script; base_check() devolve a permissão e confere o digest depois. Base mexido
descarta o derivado: a referência do Juiz pressupõe o pai intacto (R9).

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
import os
import re
import shutil
import stat
import sys
import tarfile
import uuid
from pathlib import Path

DERIVATIVE_DIRNAME = "derivative"
BASE_DIRNAME = "model"
TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")
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


def collect(workspace_dir: Path, outbox: Path | None = None) -> dict | None:
    """Empacota workspace/derivative/ e o apaga. None se o job não deixou derivado.

    Com outbox, o pacote vai para outbox/<token>.tar.gz (em disco, sem passar pela memória).
    """
    root = Path(workspace_dir) / DERIVATIVE_DIRNAME
    if root.is_symlink() or not root.is_dir():
        return None
    try:
        names = model_files(root)
        if not names:
            return None
        files = [{"path": n, "size": (root / n).stat().st_size, "sha256": file_sha256(root / n)} for n in names]
        out = {"digest": set_digest(files), "files": files, "format": ARCHIVE_FORMAT}
        if outbox is not None:
            outbox = Path(outbox)
            outbox.mkdir(parents=True, exist_ok=True)
            token = uuid.uuid4().hex
            path = outbox / f"{token}.tar.gz"
            # Nível 1: pesos quase não comprimem e o gzip 9 de 1 GB custa minutos.
            with tarfile.open(path, "w:gz", compresslevel=1) as tar:
                for n in names:
                    tar.add(root / n, arcname=n, recursive=False)
            return out | {"token": token, "size": path.stat().st_size}
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for n in names:
                tar.add(root / n, arcname=n, recursive=False)
        return out | {"archive": base64.b64encode(buf.getvalue()).decode("ascii")}
    finally:
        remove_tree(root)


def remove_tree(root: Path) -> None:
    """Apaga uma árvore mesmo que o script do job a tenha deixado sem escrita (senão o rmtree falha
    calado, os pesos ficam no disco e o próximo job encontra o espaço de trabalho sujo)."""
    root = Path(root)
    if root.is_symlink():
        root.unlink(missing_ok=True)
        return
    if not root.exists():
        return
    for dirpath, _, _ in os.walk(root):
        try:
            Path(dirpath).chmod(stat.S_IRWXU)
        except OSError:
            pass
    shutil.rmtree(root, ignore_errors=True)


def outbox_file(outbox: Path, token: str) -> Path | None:
    """Arquivo do derivado de um token, ou None (token malformado ou já baixado)."""
    if not isinstance(token, str) or not TOKEN_RE.match(token):
        return None
    path = Path(outbox) / f"{token}.tar.gz"
    return path if path.is_file() and not path.is_symlink() else None


def clear_outbox(outbox: Path) -> None:
    """Apaga derivados que a CVM1 não baixou (um job por vez na CVM de uso único)."""
    for p in Path(outbox).glob("*.tar.gz"):
        p.unlink(missing_ok=True)


def _dir_digest(root: Path) -> str:
    names = model_files(root)
    return set_digest([{"path": n, "sha256": file_sha256(root / n)} for n in names])


def _chmod_tree(root: Path, writable: bool) -> None:
    for dirpath, dirnames, filenames in os.walk(root):
        for f in filenames:
            p = Path(dirpath) / f
            if not p.is_symlink():
                p.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | (stat.S_IWUSR if writable else 0))
        Path(dirpath).chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
                            if writable else stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)


def base_guard(workspace_dir: Path) -> str | None:
    """Digest do base em workspace/model e o deixa somente leitura. None se o job não tem base."""
    root = Path(workspace_dir) / BASE_DIRNAME
    if root.is_symlink() or not root.is_dir():
        return None
    digest = _dir_digest(root)
    _chmod_tree(root, writable=False)
    return digest


def base_check(workspace_dir: Path, before: str | None) -> bool:
    """Devolve a escrita (para a limpeza) e diz se o base mudou. Sem base antes, nunca mudou."""
    if before is None:
        return False
    root = Path(workspace_dir) / BASE_DIRNAME
    if root.is_symlink() or not root.is_dir():
        return True
    _chmod_tree(root, writable=True)
    return _dir_digest(root) != before


if __name__ == "__main__":
    # derivative.py WORKSPACE [OUTBOX]
    print(json.dumps(collect(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else None)))
