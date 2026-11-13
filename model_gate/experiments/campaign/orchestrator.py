"""Orquestrador da campanha: fila derivado × configuração que retoma depois de uma queda (T-1401).

Redução v2: um laço simples que pula o que já terminou. A campanha tem centenas de vereditos e
roda por dias (E13 §3.2); uma queda não pode obrigar a refazer o que já foi feito.

- **Fila:** cada derivado do inventário (T-916) × cada configuração (formato, condição), numa ordem
  fixa: a mesma entrada dá a mesma fila.
- **Livro da campanha:** um JSONL só de acréscimo em $MODEL_GATE_DATA/campaign/<nome>.jsonl. Uma
  linha {"key", "status": "done" | "failed", ...} é escrita depois que o trabalho do item volta, com
  fsync. Ao retomar, os itens com "done" são pulados. Um item que caiu no meio não tem linha e é
  refeito; uma última linha cortada pela queda é ignorada.
- **Falha:** o erro do item vai para o livro como "failed" e a fila segue; na próxima execução o
  item é tentado de novo, até max_attempts falhas, e depois fica de fora (relatado no resumo).
- **Registro de experimentos (T-206):** com um RunLog, cada item terminado também vira uma linha
  instrument="campaign", metric="item_done", para ligar o resultado ao commit e ao digest.

O trabalho de cada item (rodar o Juiz, gravar o verdict.json) é a função `work` que quem chama passa;
ela devolve um dicionário pequeno (caminhos, hashes) que vai para o livro. Nada de texto gerado.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Item:
    derivative: str                 # digest do derivado (sha256:...)
    config: tuple[tuple[str, str], ...]  # pares (chave, valor) ordenados: formato, condição...

    @property
    def key(self) -> str:
        return self.derivative + "|" + ",".join(f"{k}={v}" for k, v in self.config)

    def config_dict(self) -> dict:
        return dict(self.config)


def build_queue(inventory: Iterable[Mapping], configs: Sequence[Mapping[str, str]]) -> list[Item]:
    """Derivado × configuração, ordenado por digest e pela ordem das configurações.

    inventory: registros do inventário com a chave "digest". Digest repetido conta uma vez.
    """
    digests = sorted({str(d["digest"]) for d in inventory})
    if not configs:
        raise ValueError("sem configurações")
    cfgs = [tuple(sorted((str(k), str(v)) for k, v in c.items())) for c in configs]
    if len(set(cfgs)) != len(cfgs):
        raise ValueError("configuração repetida")
    return [Item(d, c) for d in digests for c in cfgs]


def read_ledger(path: Path) -> list[dict]:
    """Linhas válidas do livro; uma linha cortada (queda durante a escrita) é ignorada."""
    path = Path(path)
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and "key" in row and "status" in row:
                out.append(row)
    return out


def _append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        # Uma linha anterior cortada sem \n estragaria esta: começa numa linha nova.
        if f.tell() > 0:
            with open(path, "rb") as r:
                r.seek(-1, os.SEEK_END)
                if r.read(1) != b"\n":
                    f.write("\n")
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


@dataclass
class Summary:
    total: int = 0
    skipped: int = 0        # já feitos antes
    done: int = 0           # feitos nesta execução
    failed: int = 0         # falharam nesta execução
    given_up: int = 0       # atingiram max_attempts e ficaram de fora


def run(queue: Sequence[Item], work: Callable[[Item], Mapping], ledger: Path, *, max_attempts: int = 3,
        runlog=None, now: Callable[[], str] = lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z")) -> Summary:
    """Roda a fila pulando o que o livro já tem como feito. Seguro para chamar de novo depois de uma queda."""
    ledger = Path(ledger)
    rows = read_ledger(ledger)
    done = {r["key"] for r in rows if r["status"] == "done"}
    failures: dict[str, int] = {}
    for r in rows:
        if r["status"] == "failed":
            failures[r["key"]] = failures.get(r["key"], 0) + 1
    s = Summary(total=len(queue))
    for item in queue:
        if item.key in done:
            s.skipped += 1
            continue
        if failures.get(item.key, 0) >= max_attempts:
            s.given_up += 1
            continue
        started = now()
        try:
            result = dict(work(item) or {})
        except Exception as e:  # o item falha; a fila segue
            _append(ledger, {"key": item.key, "status": "failed", "error": f"{type(e).__name__}: {e}"[:500],
                             "started": started, "finished": now()})
            s.failed += 1
            continue
        _append(ledger, {"key": item.key, "status": "done", "derivative": item.derivative,
                         "config": item.config_dict(), "result": result, "started": started, "finished": now()})
        if runlog is not None:
            runlog.log("campaign", "item_done", item.key, model_digest=item.derivative, **item.config_dict())
        done.add(item.key)
        s.done += 1
    return s
