"""Registro de experimentos: um JSONL por execução, só acrescentando (T-206, R14).

Cada número da campanha aponta para o modelo (digest), o código (commit), a seed e
os parâmetros de geração que o produziram. Linha:

    {"run_id", "ts", "model_digest", "git_commit", "dirty", "seed", "gen",
     "instrument", "metric", "value", "extra"}

Arquivo: $MODEL_GATE_DATA/runs/<run_id>.jsonl. Só métricas; nunca texto gerado (T-211).
Repositório com mudanças não commitadas grava dirty=true; require_clean=True recusa.
"""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from experiments.data_dir import data_dir

REPO = Path(__file__).resolve().parents[2]


class DirtyRepo(RuntimeError):
    """Execução exigiu repositório limpo e há mudanças não commitadas."""


def git_state(repo: Path = REPO) -> tuple[str, bool]:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout

    try:
        return git("rev-parse", "HEAD").strip(), bool(git("status", "--porcelain").strip())
    except (OSError, subprocess.CalledProcessError):
        return "unknown", True


def new_run_id(prefix: str = "run") -> str:
    return f"{prefix}_{time.strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:6]}"


class RunLog:
    def __init__(
        self,
        run_id: str | None = None,
        *,
        model_digest: str | None = None,
        seed: int | None = None,
        gen: dict | None = None,
        require_clean: bool = False,
        root: Path | None = None,
        repo: Path = REPO,
    ):
        self.run_id = run_id or new_run_id()
        self.commit, self.dirty = git_state(repo)
        if require_clean and self.dirty:
            raise DirtyRepo(f"{repo}: há mudanças não commitadas")
        self.defaults = {"model_digest": model_digest, "seed": seed, "gen": gen}
        self.path = (root or data_dir() / "runs") / f"{self.run_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, instrument: str, metric: str, value: Any, **extra: Any) -> dict:
        """Acrescenta uma linha. model_digest, seed e gen em extra sobrepõem os padrões."""
        base = {k: extra.pop(k, v) for k, v in self.defaults.items()}
        row = {
            "run_id": self.run_id,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            **base,
            "git_commit": self.commit,
            "dirty": self.dirty,
            "instrument": instrument,
            "metric": metric,
            "value": value,
            "extra": extra,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row


def read(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
