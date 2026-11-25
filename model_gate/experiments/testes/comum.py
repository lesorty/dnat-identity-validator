"""Peças comuns dos passos dos testes: caminhos, avaliador, livro que retoma e registro de erros."""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Callable, Iterable, Mapping

from experiments.campaign.orchestrator import Item, read_ledger
from experiments.campaign.orchestrator import run as run_queue
from experiments.data_dir import data_dir

HERE = Path(__file__).resolve().parent
MG = HERE.parents[1]


def out_dir(arg: str | None) -> Path:
    d = Path(arg or os.environ.get("PASSO_DIR") or "")
    if not str(d):
        raise SystemExit("informe --out (ou rode pelo executor, que define PASSO_DIR)")
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve(path: str) -> Path:
    """Caminho de modelo: absoluto, relativo a $MODEL_GATE_DATA, ou 'base' (o custodiado)."""
    if path == "base":
        from experiments.fetch_base import local_root
        return local_root()
    p = Path(os.path.expandvars(path)).expanduser()
    if p.is_absolute():
        return p
    return data_dir() / p


def field_dir(repo: str) -> Path:
    """Pasta de um derivado de campo baixado (T-1103), pela revisão do manifesto."""
    for r in field_manifest():
        if r["repo"] == repo:
            return data_dir() / r["path"]
    raise KeyError(f"{repo} não está em models/field.manifest.json")


def field_manifest(familia: str | None = None) -> list[dict]:
    """Derivados de campo do manifesto (T-1103), opcionalmente de uma família."""
    rows = json.loads((MG / "models" / "field.manifest.json").read_text())["derivados"]
    return [r for r in rows if familia is None or r.get("familia") == familia]


def evaluator_spec(kind: str) -> tuple[str, dict | None]:
    """(kind do job, entrada 'evaluator' do manifesto) para detector, qwen3guard ou gemma."""
    if kind == "detector":
        return "detector", None
    from experiments.fetch_judges import JUDGES, local_root
    from model_gate.io.load import dir_digest
    name = {"qwen3guard": "qwen3guard", "guard": "qwen3guard", "gemma": "gemma"}[kind]
    if name not in JUDGES:
        raise SystemExit(f"avaliador {name} não está em models/judges.manifest.json")
    root = local_root(name)
    if not root.exists():
        raise SystemExit(f"avaliador {name} não baixado em {root} (make dados ARGS=--judges)")
    job_kind = "guard" if name == "qwen3guard" else "rubric"
    return job_kind, {"path": str(root), "kind": "dir", "digest": dir_digest(root)[0]}


def make_eval(kind: str, battery, threads: int):
    from model_gate.evaluators import make_evaluator
    job_kind, spec = evaluator_spec(kind)
    ev = make_evaluator(job_kind, model_dir=Path(spec["path"]) if spec else None,
                        model_digest=spec["digest"] if spec else None, templates=battery.templates, threads=threads)
    return job_kind, spec, ev


def log(msg: str) -> None:
    tag = f" p{Path(os.environ['MG_FATIA']).stem[1:]}" if os.environ.get("MG_FATIA") else ""
    print(f"[{time.strftime('%H:%M:%S')}{tag}] {msg}", flush=True)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")  # fatias em paralelo não disputam o mesmo .tmp
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str) + "\n")
    os.replace(tmp, path)


_COMMAND: tuple[str, list[str]] | None = None


def register(module: str, argv: list[str] | None) -> None:
    """Diz ao resumable como relançar este passo (módulo e argumentos) para rodar fatias em paralelo.

    Cada main de passo chama isto logo no começo; quem chama o main de outro módulo (o atacante chama o
    veredito) passa argv explícito, e é esse argv que as fatias recebem.
    """
    global _COMMAND
    _COMMAND = (module, list(sys.argv[1:] if argv is None else argv))


def paralelo() -> int:
    """Quantos processos por passo longo (MG_PARALELO, padrão 1). Na GPU, vários derivados cabem juntos."""
    try:
        return max(1, int(os.environ.get("MG_PARALELO", "1") or 1))
    except ValueError:
        return 1


def _ledger_rows(out: Path) -> list[dict]:
    rows = []
    for f in sorted(out.glob("livro*.jsonl")):
        rows += read_ledger(f)
    return rows


def _spawn(out: Path, shares: list[list[str]]) -> list:
    """Uma fatia por processo filho, com a lista de chaves num arquivo (fixa, mesmo que o pai avance antes)."""
    import subprocess
    module, argv = _COMMAND
    procs = []
    for j, keys in enumerate(shares, start=1):
        spec = out / "fatias" / f"p{j}.json"
        write_json(spec, {"fatia": j, "chaves": keys, "modulo": module, "argv": argv})
        env = {**os.environ, "MG_FATIA": str(spec), "MG_PARALELO": "1"}
        log(f"fatia p{j}: {len(keys)} itens em outro processo ({', '.join(keys)})")
        procs.append((j, subprocess.Popen([sys.executable, "-m", module, *argv], env=env)))
    return procs


def resumable(items: Iterable[Mapping], work: Callable[[Mapping], Mapping], out: Path, *, key: str = "nome",
              max_attempts: int = 2, what: str = "item") -> list[dict]:
    """Roda work(item) para cada item ainda sem 'done' nos livros (out/livro*.jsonl).

    O erro de um item vai para o livro e para out/erros/<chave>.txt com o traceback inteiro; a fila
    segue. Devolve os resultados de todos os itens feitos (desta e de execuções anteriores), na ordem.

    Paralelo (MG_PARALELO=N > 1, e o passo chamou register): os itens pendentes são divididos em N fatias;
    o próprio processo faz a primeira e N−1 filhos (o mesmo comando, com MG_FATIA) fazem as outras, cada um
    com o seu livro (livro_p<j>.jsonl), sem disputar arquivo. Um filho só roda a sua fatia e sai.
    """
    items = list(items)
    by_key = {str(it[key]): it for it in items}
    done_before = {r["key"].split("|")[0] for r in _ledger_rows(out) if r["status"] == "done"}
    pending = [k for k in by_key if k not in done_before]
    fatia = os.environ.get("MG_FATIA")
    children = []
    if fatia:
        spec = json.loads(Path(fatia).read_text())
        mine = [k for k in spec["chaves"] if k in pending]
        ledger = out / f"livro_p{spec['fatia']}.jsonl"
    else:
        ledger = out / "livro.jsonl"
        n = min(paralelo(), len(pending))
        if n > 1 and _COMMAND is not None:
            shares = [pending[j::n] for j in range(n)]
            mine = shares[0]
            children = _spawn(out, shares[1:])
        else:
            mine = pending
    queue = [Item(k, (("passo", out.name),)) for k in mine]

    def wrapped(item: Item) -> Mapping:
        it = by_key[item.derivative]
        log(f"{what} {item.derivative}: começando")
        t0 = time.perf_counter()
        try:
            res = dict(work(it))
        except BaseException as e:
            err = out / "erros" / f"{item.derivative}.txt"
            err.parent.mkdir(parents=True, exist_ok=True)
            with open(err, "a") as fh:
                fh.write(f"\n===== {time.strftime('%Y-%m-%dT%H:%M:%S')}\n{traceback.format_exc()}")
            log(f"{what} {item.derivative}: ERRO {type(e).__name__}: {e} (traceback em {err})")
            if isinstance(e, KeyboardInterrupt):
                raise
            raise RuntimeError(f"{type(e).__name__}: {e}") from e
        res.setdefault("segundos", round(time.perf_counter() - t0, 1))
        log(f"{what} {item.derivative}: feito em {res['segundos']} s")
        return res

    try:
        s = run_queue(queue, wrapped, ledger, max_attempts=max_attempts)
        log(f"livro {ledger.name}: {s.done} feitos agora, {len(done_before)} já feitos antes, {s.failed} com erro, "
            f"{s.given_up} desistidos")
    finally:
        for j, proc in children:
            code = proc.wait()
            log(f"fatia p{j}: terminou com código {code}")
    if fatia:
        sys.exit(0)
    done = {}
    for r in _ledger_rows(out):
        if r["status"] == "done":
            done[r["key"].split("|")[0]] = r["result"]
    return [{key: k, **by_key[k], **done[k]} for k in by_key if k in done]


def failures(out: Path) -> list[str]:
    rows = _ledger_rows(out)
    done = {r["key"] for r in rows if r["status"] == "done"}
    return sorted({r["key"].split("|")[0] for r in rows if r["status"] == "failed" and r["key"] not in done})
