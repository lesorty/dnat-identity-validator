"""Executor da campanha na nuvem: roda os passos de tools/cloud/plano.yaml, retoma e empacota.

    uv run --project model_gate python tools/cloud/campanha.py status
    uv run --project model_gate python tools/cloud/campanha.py run [PASSO ...] [--forcar] [--sem-congelamento] [--continuar]
    uv run --project model_gate python tools/cloud/campanha.py pacote

(ou: make campanha-status | make campanha [PASSOS="..."] | make pacote)

- **Congelamento:** os passos que produzem dado só rodam com o HEAD numa tag `congelado-*` (make
  congelar, T-1611) e sem mudança no repositório. `--sem-congelamento` deixa rodar para ensaio, e o
  estado registra isso (o pacote não serve como dado do artigo).
- **Retomada:** o estado fica em $MODEL_GATE_DATA/campanha/<nome>_<commit>/estado.json, gravado a
  cada passo. `run` sem passos roda os que ainda não terminaram com sucesso; com passos, roda esses
  (de novo, se preciso).
- **Bloqueios:** passo sem script fica de fora; passo com `bloqueio` só roda com --forcar.
- **Falha:** para no primeiro passo que falha (--continuar segue para o próximo).
- **Pacote:** resultados (model_gate/results, smart-contract/results), registro de execuções, fichas
  da máquina, estado e logs da campanha num .tar.gz, com o comando para trazê-lo de volta.
"""
from __future__ import annotations

import json
import os
import shlex
import socket
import subprocess
import sys
import tarfile
import time
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("MODEL_GATE_DATA", Path.home() / "model_gate_data")).expanduser()
PLANO = Path(__file__).with_name("plano.yaml")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


def head() -> dict:
    return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain")),
            "tags": git("tag", "--points-at", "HEAD").split()}


def frozen(h: dict) -> bool:
    return not h["dirty"] and any(t.startswith("congelado-") for t in h["tags"])


def load_plan() -> dict:
    plan = yaml.safe_load(PLANO.read_text())
    ids = [p["id"] for p in plan["passos"]]
    if len(ids) != len(set(ids)):
        raise SystemExit("plano.yaml: id repetido")
    return plan


def state_dir(plan: dict, h: dict) -> Path:
    return DATA / "campanha" / f"{plan['nome']}_{h['commit'][:12]}"


def load_state(d: Path) -> dict:
    f = d / "estado.json"
    return json.loads(f.read_text()) if f.exists() else {"passos": {}}


def save_state(d: Path, st: dict) -> None:
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "estado.json.tmp"
    tmp.write_text(json.dumps(st, indent=1, ensure_ascii=False) + "\n")
    os.replace(tmp, d / "estado.json")


def label(p: dict, rec: dict | None) -> str:
    if p.get("cmd") is None:
        return "sem script"
    if rec:
        return {"ok": "feito", "falhou": f"falhou ({rec.get('codigo')})", "rodando": "interrompido"}.get(rec["estado"], rec["estado"])
    return "bloqueado" if p.get("bloqueio") else "a rodar"


def status(plan: dict, h: dict) -> int:
    d = state_dir(plan, h)
    st = load_state(d)
    print(f"campanha {plan['nome']} · commit {h['commit'][:12]}{' (sujo)' if h['dirty'] else ''} · "
          f"{'congelado' if frozen(h) else 'NÃO congelado (make congelar; ou --sem-congelamento para ensaio)'}")
    print(f"estado em {d}\n")
    counts: dict[str, int] = {}
    for p in plan["passos"]:
        rec = st["passos"].get(p["id"])
        lab = label(p, rec)
        key = "falhou" if lab.startswith("falhou") else lab
        counts[key] = counts.get(key, 0) + 1
        dur = f"{rec['segundos'] / 60:.1f} min" if rec and rec.get("segundos") is not None else ""
        print(f"  {p['id']:<22} {p['task']:<7} {lab:<16} {dur:>9}  {p['titulo']}")
        if p.get("bloqueio") and not (rec and rec["estado"] == "ok"):
            print(f"  {'':<22} {'':<7} └ bloqueio: {p['bloqueio']}")
    print("\n" + " · ".join(f"{k}: {v}" for k, v in counts.items()))
    return 0


def run(plan: dict, h: dict, wanted: list[str], force: bool, unfrozen: bool, cont: bool) -> int:
    by_id = {p["id"]: p for p in plan["passos"]}
    unknown = [w for w in wanted if w not in by_id]
    if unknown:
        raise SystemExit(f"passos desconhecidos: {unknown}")
    d = state_dir(plan, h)
    st = load_state(d)
    st.setdefault("inicio", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    st.setdefault("inicio_ts", time.time())
    st.update({"commit": h["commit"], "host": socket.gethostname(), "congelado": frozen(h)})
    steps = [by_id[w] for w in wanted] if wanted else [p for p in plan["passos"] if st["passos"].get(p["id"], {}).get("estado") != "ok"]
    (d / "logs").mkdir(parents=True, exist_ok=True)
    rc = 0
    for p in steps:
        pid = p["id"]
        if p.get("cmd") is None:
            print(f"- {pid}: sem script, fica de fora")
            continue
        if p.get("bloqueio") and not force:
            print(f"- {pid}: bloqueado ({p['bloqueio']}); --forcar roda mesmo assim")
            continue
        if p.get("congelado", True) and not frozen(h) and not unfrozen:
            print(f"- {pid}: o commit não está congelado; make congelar, ou --sem-congelamento para ensaio")
            rc = rc or 3
            continue
        cpus = p.get("cpus", plan.get("cpus"))
        cmd = p["cmd"] if not cpus else f"taskset -c {cpus} bash -c {shlex.quote(p['cmd'])}"
        log = d / "logs" / f"{pid}.log"
        print(f"\n=== {pid} ({p['task']}): {p['titulo']}\n$ {cmd}\nlog: {log}", flush=True)
        rec = {"estado": "rodando", "inicio": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "cmd": cmd, "log": str(log),
               "congelado": frozen(h), "forcado": bool(p.get("bloqueio"))}
        st["passos"][pid] = rec
        save_state(d, st)
        t0 = time.time()
        with open(log, "ab") as fh:
            fh.write(f"\n# {rec['inicio']} {cmd}\n".encode())
            proc = subprocess.Popen(["bash", "-o", "pipefail", "-c", cmd], cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            for line in proc.stdout:
                sys.stdout.buffer.write(line)
                sys.stdout.flush()
                fh.write(line)
            code = proc.wait()
        rec.update({"estado": "ok" if code == 0 else "falhou", "codigo": code, "segundos": round(time.time() - t0, 1),
                    "fim": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
        save_state(d, st)
        print(f"=== {pid}: {'ok' if code == 0 else f'FALHOU ({code})'} em {rec['segundos'] / 60:.1f} min", flush=True)
        if code != 0:
            rc = 1
            if not cont:
                break
    return rc


def pacote(plan: dict, h: dict) -> int:
    d = state_dir(plan, h)
    out_dir = DATA / "pacotes"
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"campanha_{plan['nome']}_{socket.gethostname()}_{h['commit'][:12]}_{time.strftime('%Y%m%dT%H%M%S')}"
    out = out_dir / f"{name}.tar.gz"
    parts = [(REPO / "model_gate" / "results", "results/model_gate"), (REPO / "smart-contract" / "results", "results/smart-contract"),
             (DATA / "runs", "runs"), (DATA / "machine", "machine"), (d, "campanha")]
    meta = {"head": h, "congelado": frozen(h), "host": socket.gethostname(), "criado": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "aviso": None if frozen(h) else "commit não congelado: ensaio, não dado do artigo"}
    meta_file = out_dir / f"{name}.json"
    meta_file.write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n")
    # Dos resultados versionados, só os gravados desde o início da campanha: os outros são as
    # verificações locais que vieram no commit e não podem aparecer como dado da nuvem.
    since = load_state(d).get("inicio_ts")
    if since is None:
        raise SystemExit("a campanha ainda não rodou neste commit: nada a empacotar")
    fresh = lambda p: p.stat().st_mtime >= since - 1
    kept = 0
    with tarfile.open(out, "w:gz") as tar:
        tar.add(meta_file, arcname=f"{name}/pacote.json")
        for src, arc in parts:
            if not src.exists():
                continue
            if arc.startswith("results/"):
                for f in sorted(src.iterdir()):
                    if f.is_file() and fresh(f):
                        tar.add(f, arcname=f"{name}/{arc}/{f.name}")
                        kept += 1
            else:
                # só métricas e relatórios; textos gerados (*_texts.json) ficam de fora (T-211)
                tar.add(src, arcname=f"{name}/{arc}", filter=lambda ti: None if ti.name.endswith("_texts.json") else ti)
    size = out.stat().st_size / 2**20
    print(f"pacote: {out} ({size:.1f} MB, {kept} arquivos de resultado desta campanha){'' if frozen(h) else '  [ENSAIO: commit não congelado]'}")
    print(f"para trazer: scp {os.environ.get('USER', 'usuario')}@{socket.gethostname()}:{out} .")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("status", "run", "pacote"):
        print(__doc__)
        return 2
    plan, h = load_plan(), head()
    flags = {a for a in argv[1:] if a.startswith("--")}
    if argv[0] == "status":
        return status(plan, h)
    if argv[0] == "pacote":
        return pacote(plan, h)
    return run(plan, h, [a for a in argv[1:] if not a.startswith("--")], "--forcar" in flags, "--sem-congelamento" in flags, "--continuar" in flags)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
