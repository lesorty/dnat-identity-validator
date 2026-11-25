#!/usr/bin/env python3
"""Executor comum dos Testes T1 a T11: passos que retomam, logs completos e o acompanhamento.

Cada teste (tools/testes/tNN_*.py) é uma lista de passos. Um passo é um comando rodado num
subprocesso, da raiz do repositório. O executor:

- **Retoma:** o estado fica em $MODEL_GATE_DATA/testes/<perfil>/<commit>/<teste>/estado.json, gravado
  de forma atômica antes e depois de cada passo e a cada sinal de vida. Rodar de novo pula os passos
  que já terminaram com sucesso e refaz o que caiu ou falhou. Os passos longos também retomam por
  dentro: recebem PASSO_DIR e gravam ali o próprio livro (experiments/testes/*).
- **Guarda tudo:** cada passo tem um log com hora em cada linha (stdout e stderr, marcados), o
  comando, o código de saída, o tempo, o pico de memória e as últimas linhas no estado; eventos.jsonl
  recebe início, fim, sinais de vida e erros, só acrescentando e com fsync; ambiente.json guarda o
  commit, o diff (se sujo), a máquina, as versões e os hashes dos lockfiles; os arquivos que o passo
  produz são copiados para resultados/. Nada disso é apagado: --novo move a pasta antiga para o lado.
- **Pré-voo:** --verificar só confere se o teste pode rodar (dados, modelos, prereg, licenças,
  ferramentas), sem gastar máquina. É o que se roda antes de ligar a VM cara.
- **Confere e registra:** no fim, as conferências do teste (o gabarito) viram resumo.json, e o
  resultado entra no acompanhamento versionado (DSN2027/testes/), para comparar execuções.

Perfis: `mini` é a versão pequena de verificação local (minutos, avaliador e prereg de fumaça, não é
dado do artigo); `nuvem` é a campanha de verdade (exige commit congelado, ou --sem-congelamento para
ensaio). Só biblioteca padrão: o executor roda com python3 -I, fora do ambiente do model_gate.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import hashlib
import json
import os
import platform
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

REPO = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("MODEL_GATE_DATA", Path.home() / "model_gate_data")).expanduser()
ACOMP_DIR = REPO / "DSN2027" / "testes"
PERFIS = ("mini", "ensaio", "nuvem")
PEQUENOS = ("mini", "ensaio")   # tamanhos do mini; o ensaio roda na GPU da VM, antes da campanha
HEARTBEAT_S = 30
TAIL_LINES = 60

# Atalhos para os comandos dos passos (rodados da raiz do repositório).
MG = "cd model_gate && uv run --frozen python -m"
SC = "cd smart-contract &&"


def now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    return r.stdout.strip()


# Pastas que os próprios testes escrevem: não contam como "repositório sujo" para o congelamento (senão o
# primeiro passo que grava um resultado versionado impediria todos os seguintes de rodar na nuvem).
RESULT_PATHS = ("model_gate/results", "smart-contract/results", "assets/test-results", "DSN2027/testes")


def head() -> dict:
    status = git("status", "--porcelain", "--", ".", *[f":(exclude){x}" for x in RESULT_PATHS])
    return {"commit": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(status), "tags": git("tag", "--points-at", "HEAD").split()}


def frozen(h: dict) -> bool:
    return not h["dirty"] and any(t.startswith("congelado-") for t in h["tags"])


def write_json(path: Path, obj) -> None:
    """Grava de forma atômica: uma queda no meio nunca deixa o arquivo pela metade."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def append_jsonl(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _cmd_version(*cmd: str) -> str | None:
    try:
        r = subprocess.run(list(cmd), capture_output=True, text=True, timeout=20)
        return (r.stdout or r.stderr).strip().splitlines()[0] if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return None


def _meminfo() -> dict:
    out = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, v = line.split(":", 1)
            if k in ("MemTotal", "MemAvailable", "SwapTotal"):
                out[k] = round(int(v.split()[0]) / 2**20, 2)  # GB
    except OSError:
        pass
    return out


def _cpu() -> dict:
    model, flags = None, set()
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name") and model is None:
                model = line.split(":", 1)[1].strip()
            if line.startswith("flags") and not flags:
                flags = set(line.split(":", 1)[1].split())
    except OSError:
        pass
    keep = sorted(f for f in flags if f.startswith(("avx512", "amx")) or f in ("avx2", "sev", "sev_es", "sev_snp", "tdx_guest"))
    return {"modelo": model, "nucleos": os.cpu_count(), "flags_relevantes": keep}


def _gpu() -> str | None:
    if not shutil.which("nvidia-smi"):
        return None
    return _cmd_version("nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader")


def disk_free_gb(path: Path) -> float:
    try:
        p = path if path.exists() else path.parent
        return round(shutil.disk_usage(p).free / 2**30, 1)
    except OSError:
        return -1.0


def environment(h: dict) -> dict:
    env_keys = ("MODEL_GATE_DATA", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "CUDA_VISIBLE_DEVICES", "HF_HOME",
                "HF_HUB_OFFLINE", "PATH", "LANG", "TZ")
    machine = sorted((DATA / "machine").glob("*.json")) if (DATA / "machine").is_dir() else []
    return {
        "quando": now(), "host": socket.gethostname(), "usuario": os.environ.get("USER"),
        "git": h, "plataforma": platform.platform(), "python": sys.version.split()[0],
        "node": _cmd_version("node", "--version"), "uv": _cmd_version("uv", "--version"),
        "cpu": _cpu(), "memoria_gb": _meminfo(), "gpu": _gpu(),
        "disco_livre_gb": {"repo": disk_free_gb(REPO), "dados": disk_free_gb(DATA)},
        "lockfiles": {"model_gate/uv.lock": sha256_file(REPO / "model_gate" / "uv.lock"),
                      "smart-contract/package-lock.json": sha256_file(REPO / "smart-contract" / "package-lock.json")},
        "env": {k: os.environ.get(k) for k in env_keys if os.environ.get(k) is not None},
        "ficha_da_maquina": str(machine[-1]) if machine else None,
    }


def profile_conf(perfil: str) -> dict:
    """O que perfis.py diz do perfil (ambiente dos passos, limite de silêncio); vazio se não houver."""
    try:
        from perfis import PERFIL
    except ImportError:
        return {}
    return PERFIL.get(perfil, {})


def gpu_usage() -> dict:
    """Memória e uso da GPU agora (nvidia-smi), para o sinal de vida; vazio sem GPU."""
    if not shutil.which("nvidia-smi"):
        return {}
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout
        used, total, util = [float(x) for x in out.strip().splitlines()[0].split(",")]
        return {"gpu_mem_mb": used, "gpu_mem_total_mb": total, "gpu_uso_pct": util}
    except Exception:
        return {}


_GPU_READY: list = []


def gpu_ready() -> str | None:
    """None se o model_gate enxerga a GPU (torch com CUDA, driver no ar); senão, o que falta."""
    if _GPU_READY:
        return _GPU_READY[0]
    py = REPO / "model_gate" / ".venv" / "bin" / "python"
    if not shutil.which("nvidia-smi"):
        msg = "perfil na GPU, mas não há nvidia-smi (driver da NVIDIA): tools/cloud/preparar_testes.sh"
    elif not py.exists():
        msg = "ambiente do model_gate não criado (make setup)"
    else:
        r = subprocess.run([str(py), "-c", "import torch; print(torch.version.cuda, torch.cuda.is_available())"],
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout or r.stderr).strip()
        msg = None if out.endswith("True") else (
            f"o torch do model_gate não vê a GPU ({out[-200:]}): instale o de CUDA com tools/cloud/preparar_testes.sh")
    _GPU_READY.append(msg)
    return msg


def campaign_key(perfil: str, h: dict, campanha: str | None = None) -> str:
    """Pasta da campanha. Mini: o commit (código novo, verificação nova). Nuvem: um nome fixo ('tst'),
    para a fase 2 (commit novo com o prereg congelado) enxergar e retomar o que a fase 1 fez; cada passo
    grava o commit em que rodou."""
    if campanha:
        return campanha
    if perfil == "nuvem":
        return "tst"
    return ("ensaio_" if perfil == "ensaio" else "") + h["commit"][:12] + ("_sujo" if h["dirty"] else "")


# --------------------------------------------------------------------------- definição dos testes

@dataclass
class Ctx:
    """O que um passo e as conferências enxergam."""
    teste: str
    perfil: str
    dir: Path                      # pasta do teste nesta execução
    data: Path = DATA
    repo: Path = REPO

    def passo_dir(self, pid: str) -> Path:
        return self.dir / "passos" / pid

    def resultado(self, pid: str, nome: str):
        """JSON que um passo gravou na pasta dele (ou None)."""
        return read_json(self.passo_dir(pid) / nome)


@dataclass
class Passo:
    id: str
    titulo: str
    cmd: str | None                       # shell; pode usar $PASSO_DIR, $TESTE_DIR, $PERFIL, $MODEL_GATE_DATA
    perfis: tuple[str, ...] = PERFIS
    timeout_min: float | None = None
    produz: tuple[str, ...] = ()          # globs (relativos à raiz) que o passo escreve fora do PASSO_DIR
    requer: tuple[Callable[[Ctx], str | None], ...] = ()   # pré-voo: devolve o problema ou None
    pendente: str | None = None           # ainda não dá para rodar: o motivo (vira falha no pré-voo)
    opcional: bool = False                # falhar não reprova o teste (ex.: medida extra)


@dataclass
class Teste:
    id: str
    nome: str
    perguntas: str
    objetivo: str
    gabarito: tuple[str, ...]             # o que se espera ver, em palavras (vai para o acompanhamento)
    passos: list[Passo] | Callable[[str], list[Passo]]   # lista fixa, ou função do perfil
    conferir: Callable[[Ctx], list[dict]] = lambda ctx: []
    numeros: Callable[[Ctx], dict] = lambda ctx: {}
    pendencias: tuple[str, ...] = ()       # o que falta para a versão da nuvem (planejamento)
    depende: tuple[str, ...] = ()          # testes que têm de ter rodado antes, no mesmo perfil e commit


def check(nome: str, ok: bool | None, valor=None, esperado=None) -> dict:
    """Uma conferência do gabarito. ok=None quando não dá para conferir (dado faltando)."""
    return {"nome": nome, "ok": ok, "valor": valor, "esperado": esperado}


# Pré-voo reaproveitável --------------------------------------------------------------------------

def exists(rel: str, what: str | None = None) -> Callable[[Ctx], str | None]:
    def f(ctx: Ctx) -> str | None:
        p = Path(os.path.expandvars(rel.replace("$MODEL_GATE_DATA", str(ctx.data))))
        p = p if p.is_absolute() else ctx.repo / p
        return None if glob.glob(str(p)) else f"falta {what or rel} ({p})"
    return f


def tool(name: str) -> Callable[[Ctx], str | None]:
    return lambda ctx: None if shutil.which(name) else f"falta a ferramenta {name} no PATH"


def memory(min_gb: float, why: str) -> Callable[[Ctx], str | None]:
    def f(ctx: Ctx) -> str | None:
        total = _meminfo().get("MemTotal")
        return None if total is None or total >= min_gb else f"RAM {total:.0f} GB < {min_gb} GB ({why})"
    return f


def disk(min_gb: float) -> Callable[[Ctx], str | None]:
    return lambda ctx: None if disk_free_gb(ctx.data) >= min_gb else f"disco livre em {ctx.data} < {min_gb} GB"


def prereg_complete(rel: str = "model_gate/prereg.yaml") -> Callable[[Ctx], str | None]:
    """O prereg do experimento precisa estar preenchido (T-606) antes dos testes com o Juiz congelado."""
    def f(ctx: Ctx) -> str | None:
        p = ctx.repo / rel
        if not p.exists():
            return f"falta {rel}"
        text = p.read_text()
        sec = text.split("limiares:", 1)[1].split("\ns1:", 1)[0] if "limiares:" in text else ""
        nulls = [ln.split(":")[0].strip() for ln in sec.splitlines() if ln.split("#")[0].rstrip().endswith("null")]
        return f"{rel} ainda tem limiares null ({', '.join(nulls)}): o T2 propõe, a T-606 fixa" if nulls else None
    return f


# --------------------------------------------------------------------------- execução de um passo

class _Child:
    def __init__(self):
        self.proc: subprocess.Popen | None = None


def _proc_tree_rss_mb(pid: int) -> float | None:
    """RSS somado do processo e dos filhos (de /proc), para o sinal de vida."""
    try:
        kids = {pid}
        for p in Path("/proc").iterdir():
            if not p.name.isdigit():
                continue
            try:
                ppid = int((p / "stat").read_text().rsplit(")", 1)[1].split()[1])
            except (OSError, ValueError, IndexError):
                continue
            if ppid in kids:
                kids.add(int(p.name))
        total = 0
        for k in kids:
            try:
                for line in Path(f"/proc/{k}/status").read_text().splitlines():
                    if line.startswith("VmRSS:"):
                        total += int(line.split()[1])
            except OSError:
                pass
        return round(total / 1024, 1)
    except OSError:
        return None


class Runner:
    def __init__(self, teste: Teste, perfil: str, *, unfrozen: bool, novo: bool, refazer: set[str],
                 echo: bool = True, campanha: str | None = None):
        self.t, self.perfil, self.unfrozen, self.echo = teste, perfil, unfrozen, echo
        self.h = head()
        self.dir = DATA / "testes" / perfil / campaign_key(perfil, self.h, campanha) / teste.id
        if novo and self.dir.exists():
            old = self.dir.with_name(f"{teste.id}.antigo-{time.strftime('%Y%m%dT%H%M%S')}")
            self.dir.rename(old)
            print(f"pasta anterior guardada em {old}")
        self.ctx = Ctx(teste.id, perfil, self.dir)
        self.state_file = self.dir / "estado.json"
        self.events = self.dir / "eventos.jsonl"
        self.refazer = refazer
        self.child = _Child()
        self.lock = threading.Lock()
        self.st = read_json(self.state_file, None) or {"teste": teste.id, "nome": teste.nome, "perfil": perfil,
                                                         "commit": self.h["commit"], "execucoes": [], "passos": {}}

    # -- estado e eventos
    def save(self) -> None:
        with self.lock:
            write_json(self.state_file, self.st)

    def event(self, kind: str, **kw) -> None:
        append_jsonl(self.events, {"ts": now(), "evento": kind, **kw})

    def say(self, msg: str) -> None:
        if self.echo:
            print(msg, flush=True)

    # -- pré-voo
    def steps(self) -> list[Passo]:
        ps = self.t.passos(self.perfil) if callable(self.t.passos) else self.t.passos
        return [p for p in ps if self.perfil in p.perfis]

    def dep_state(self, tid: str) -> str | None:
        r = read_json(self.dir.parent / tid / "resumo.json")
        return r.get("estado") if r else None

    def preflight(self, deps: bool = True) -> list[str]:
        problems = []
        for d in self.t.depende:
            st = self.dep_state(d)
            if deps and st not in ("ok", "divergiu"):
                problems.append(f"depende de {d}, que {'não rodou' if st is None else f'terminou {st}'} neste perfil e commit")
        if self.perfil == "nuvem" and not frozen(self.h) and not self.unfrozen:
            problems.append("commit não congelado (make congelar); --sem-congelamento só para ensaio")
        if profile_conf(self.perfil).get("env", {}).get("MODEL_GATE_DISPOSITIVO") == "cuda" and \
                any(p.cmd and "model_gate" in p.cmd for p in self.steps()):
            msg = gpu_ready()
            if msg:
                problems.append(msg)
        by_msg: dict[str, list[str]] = {}
        for p in self.steps():
            msgs = [f"pendente: {p.pendente}"] if p.pendente else []
            for req in p.requer:
                try:
                    msg = req(self.ctx)
                except Exception as e:  # o pré-voo nunca derruba o executor
                    msg = f"conferência falhou: {type(e).__name__}: {e}"
                if msg:
                    msgs.append(msg)
            if p.opcional and msgs:   # passo opcional não segura o teste: vira aviso
                for m in msgs:
                    self.say(f"  aviso: {p.id} (opcional) vai falhar: {m}")
                continue
            for m in msgs:
                by_msg.setdefault(m, []).append(p.id)
        return problems + [f"{', '.join(ids)}: {m}" for m, ids in by_msg.items()]

    # -- um passo
    def _env(self, p: Passo) -> dict:
        env = dict(os.environ)
        pd = self.ctx.passo_dir(p.id)
        env.update({"PASSO_DIR": str(pd), "TESTE_DIR": str(self.dir), "PERFIL": self.perfil, "TESTE_ID": self.t.id,
                    "MODEL_GATE_DATA": str(DATA), "PYTHONUNBUFFERED": "1"})
        for k, v in profile_conf(self.perfil).get("env", {}).items():
            env.setdefault(k, str(v))  # o ambiente de quem chamou vence (ex.: MG_PARALELO=1 para depurar)
        return env

    def _silence_limit(self) -> float | None:
        v = os.environ.get("TESTES_SILENCIO_MIN") or profile_conf(self.perfil).get("silencio_min")
        return float(v) if v else None

    def _heartbeat(self, pid: str, rec: dict, stop: threading.Event, t0: float) -> None:
        n = 0
        while not stop.wait(HEARTBEAT_S):
            n += 1
            proc = self.child.proc
            sig = {"ts": now(), "segundos": round(time.time() - t0), "carga": os.getloadavg()[0],
                   "rss_mb": _proc_tree_rss_mb(proc.pid) if proc else None, "disco_livre_gb": disk_free_gb(DATA),
                   "ultima_linha": rec.get("_last"), **gpu_usage()}
            with self.lock:
                rec["sinal"] = sig
                rec["pico_rss_mb"] = max(rec.get("pico_rss_mb") or 0, sig["rss_mb"] or 0)
            self.save()
            if n % 10 == 0:  # a cada ~5 min, também no eventos.jsonl
                self.event("sinal", passo=pid, **sig)

    _backup_proc = None

    def backup(self, motivo: str) -> None:
        """Cópia de segurança fora da VM depois de cada passo (TESTES_BACKUP: um comando de shell, por exemplo
        gcloud storage rsync para um bucket). Roda em segundo plano, sem segurar a campanha, e não empilha:
        se a anterior ainda está rodando, esta fica para o próximo passo. A saída vai para logs/backup.log."""
        cmd = os.environ.get("TESTES_BACKUP")
        if not cmd:
            return
        if self._backup_proc is not None and self._backup_proc.poll() is None:
            return
        log = self.dir / "logs" / "backup.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        fh = open(log, "a")
        fh.write(f"\n##### {now()} · {motivo}\n")
        fh.flush()
        self._backup_proc = subprocess.Popen(["bash", "-c", cmd], cwd=REPO, stdout=fh, stderr=subprocess.STDOUT,
                                             env={**os.environ, "TESTE_DIR": str(self.dir)}, start_new_session=True)
        self.event("backup", motivo=motivo)

    def run_step(self, p: Passo) -> int:
        pd = self.ctx.passo_dir(p.id)
        pd.mkdir(parents=True, exist_ok=True)
        log = self.dir / "logs" / f"{p.id}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        attempt = self.st["passos"].get(p.id, {}).get("tentativas", 0) + 1
        rec = {"estado": "rodando", "titulo": p.titulo, "cmd": p.cmd, "inicio": now(), "log": str(log),
               "tentativas": attempt, "passo_dir": str(pd), "commit": self.h["commit"], "sujo": self.h["dirty"]}
        self.st["passos"][p.id] = rec
        self.save()
        self.event("inicio", passo=p.id, cmd=p.cmd, tentativa=attempt)
        self.say(f"\n=== {self.t.id}/{p.id}: {p.titulo}\n$ {p.cmd}\nlog: {log}")
        t0 = time.time()
        tail: list[str] = []
        stop = threading.Event()
        hb = threading.Thread(target=self._heartbeat, args=(p.id, rec, stop, t0), daemon=True)
        code: int
        with open(log, "a", encoding="utf-8", errors="replace") as fh:
            fh.write(f"\n##### {now()} · {self.t.id}/{p.id} · tentativa {attempt} · perfil {self.perfil} · "
                     f"commit {self.h['commit'][:12]}{' (sujo)' if self.h['dirty'] else ''}\n##### $ {p.cmd}\n")
            fh.flush()
            try:
                proc = subprocess.Popen(["bash", "-o", "pipefail", "-c", p.cmd], cwd=REPO, env=self._env(p),
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
                self.child.proc = proc
                hb.start()

                def pump(stream, mark):
                    for raw in iter(stream.readline, b""):
                        line = raw.decode("utf-8", "replace").rstrip("\n")
                        stamp = time.strftime("%H:%M:%S")
                        with self.lock:
                            fh.write(f"[{stamp}]{mark} {line}\n")
                            fh.flush()
                            tail.append(f"{mark.strip() or 'out'}: {line}")
                            del tail[:-TAIL_LINES]
                            rec["_last"] = line[-300:]
                            rec["_t_last"] = time.time()
                        if self.echo:
                            print(f"  {line}" if not mark.strip() else f"  [err] {line}", flush=True)

                th = [threading.Thread(target=pump, args=(proc.stdout, " "), daemon=True),
                      threading.Thread(target=pump, args=(proc.stderr, " ERR"), daemon=True)]
                for x in th:
                    x.start()
                silence = self._silence_limit()
                rec["_t_last"] = time.time()
                why = None
                while True:
                    try:
                        code = proc.wait(timeout=5)
                        break
                    except subprocess.TimeoutExpired:
                        pass
                    if p.timeout_min and time.time() - t0 > p.timeout_min * 60:
                        why, code = f"TEMPO ESGOTADO ({p.timeout_min} min)", 124
                    elif silence and time.time() - rec["_t_last"] > silence * 60:
                        why, code = f"SEM SAÍDA HÁ {silence:g} MIN (passo travado?)", 124
                    if why:
                        os.killpg(proc.pid, signal.SIGTERM)
                        try:
                            proc.wait(timeout=30)
                        except subprocess.TimeoutExpired:
                            os.killpg(proc.pid, signal.SIGKILL)
                        with self.lock:
                            fh.write(f"##### {why}\n")
                            tail.append(f"executor: {why}")
                        break
                for x in th:
                    x.join(timeout=10)
            except Exception as e:  # erro do próprio executor ao lançar o passo
                code = 125
                fh.write("##### ERRO DO EXECUTOR\n" + traceback.format_exc())
                tail.append(f"executor: {type(e).__name__}: {e}")
            finally:
                stop.set()
                self.child.proc = None
        secs = round(time.time() - t0, 1)
        try:
            import resource
            peak_children_mb = round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 1)
        except Exception:
            peak_children_mb = None
        copied = self.collect(p, pd, t0)
        rec.pop("_last", None)
        rec.pop("_t_last", None)
        rec.update({"estado": "ok" if code == 0 else "falhou", "codigo": code, "segundos": secs, "fim": now(),
                    "pico_rss_filhos_mb": peak_children_mb, "copiados": copied})
        if code != 0:
            rec["ultimas_linhas"] = tail[-TAIL_LINES:]
        self.save()
        self.event("fim", passo=p.id, codigo=code, segundos=secs, copiados=copied)
        self.say(f"=== {self.t.id}/{p.id}: {'ok' if code == 0 else f'FALHOU (código {code})'} em {secs / 60:.1f} min")
        return code

    def collect(self, p: Passo, pd: Path, since: float) -> list[str]:
        """Copia para resultados/ o que o passo escreveu fora da pasta dele (results/*.json etc.)."""
        out = []
        dest = self.dir / "resultados" / p.id
        for pattern in p.produz:
            for f in sorted(glob.glob(str(REPO / pattern))):
                fp = Path(f)
                if fp.is_file() and fp.stat().st_mtime >= since - 1:
                    dest.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(fp, dest / fp.name)
                    out.append(str(fp.relative_to(REPO)))
        return out

    # -- o teste inteiro
    def run(self, only: list[str] | None = None, cont: bool = False) -> int:
        self.dir.mkdir(parents=True, exist_ok=True)
        exe = {"inicio": now(), "host": socket.gethostname(), "commit": self.h["commit"], "sujo": self.h["dirty"],
               "congelado": frozen(self.h), "argv": sys.argv}
        self.st["execucoes"].append(exe)
        n = len(self.st["execucoes"])
        write_json(self.dir / f"ambiente_{n:02d}.json", environment(self.h))
        if self.h["dirty"]:
            (self.dir / f"git_{n:02d}.diff").write_text(git("diff", "HEAD"))
        self.save()
        self.event("execucao", **exe)
        problems = self.preflight()
        if problems:
            exe["preflight"] = problems
            self.save()
            self.event("preflight_falhou", problemas=problems)
            print(f"{self.t.id}: pré-voo falhou:\n  - " + "\n  - ".join(problems))
            return 2

        def on_signal(signum, _frame):
            proc = self.child.proc
            if proc:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            self.event("interrompido", sinal=signum)
            for rec in self.st["passos"].values():
                if rec.get("estado") == "rodando":
                    rec["estado"] = "interrompido"
                    rec["fim"] = now()
            self.save()
            raise SystemExit(130)

        signal.signal(signal.SIGTERM, on_signal)
        signal.signal(signal.SIGINT, on_signal)
        rc = 0
        failed_required = False
        for p in self.steps():
            if only and p.id not in only:
                continue
            prev = self.st["passos"].get(p.id, {})
            if prev.get("estado") == "ok" and p.id not in self.refazer and not only:
                other = prev.get("commit") and prev["commit"] != self.h["commit"]
                self.say(f"- {self.t.id}/{p.id}: já feito ({prev.get('segundos', 0) / 60:.1f} min)"
                         + (f" no commit {prev['commit'][:12]}, não no atual" if other else "") + ", pulando")
                continue
            code = self.run_step(p)
            self.backup(f"depois do passo {p.id} (código {code})")
            if code != 0:
                if p.opcional:
                    self.say(f"  ({p.id} é opcional: o teste segue)")
                    continue
                rc, failed_required = 1, True
                if not cont:
                    break
        return self.finish(rc, failed_required)

    def finish(self, rc: int, failed: bool) -> int:
        try:
            checks = self.t.conferir(self.ctx)
        except Exception as e:
            checks = [check("conferência", None, f"{type(e).__name__}: {e}")]
            append_jsonl(self.events, {"ts": now(), "evento": "erro_conferencia", "traceback": traceback.format_exc()})
        try:
            nums = self.t.numeros(self.ctx)
        except Exception as e:
            nums = {"erro": f"{type(e).__name__}: {e}"}
        steps = self.steps()
        done = all(self.st["passos"].get(p.id, {}).get("estado") == "ok" for p in steps if not p.opcional)
        bad_checks = [c for c in checks if c["ok"] is False]
        estado = "falhou" if failed else ("incompleto" if not done else ("divergiu" if bad_checks else "ok"))
        resumo = {"teste": self.t.id, "nome": self.t.nome, "perfil": self.perfil, "estado": estado, "quando": now(),
                  "commit": self.h["commit"], "sujo": self.h["dirty"], "congelado": frozen(self.h),
                  "host": socket.gethostname(), "dir": str(self.dir),
                  "segundos": round(sum(self.st["passos"].get(p.id, {}).get("segundos") or 0 for p in steps), 1),
                  "passos": {p.id: {k: self.st["passos"].get(p.id, {}).get(k) for k in ("estado", "segundos", "codigo")}
                             for p in steps},
                  "conferencias": checks, "numeros": nums}
        write_json(self.dir / "resumo.json", resumo)
        self.event("resumo", estado=estado, conferencias_falhas=[c["nome"] for c in bad_checks])
        tracking_update(self.t, resumo)
        print(f"\n{self.t.id} ({self.perfil}): {estado.upper()} · {resumo['segundos'] / 60:.1f} min · pasta {self.dir}")
        for c in checks:
            mark = {True: "ok", False: "DIVERGIU", None: "sem dado"}[c["ok"]]
            print(f"  [{mark}] {c['nome']}: {c['valor']}" + (f" (esperado {c['esperado']})" if c.get("esperado") is not None else ""))
        if estado == "divergiu" and rc == 0:
            rc = 4
        if os.environ.get("TESTES_BACKUP"):   # a última cópia, com o resumo e o acompanhamento, antes de sair
            if self._backup_proc is not None:
                try:
                    self._backup_proc.wait(timeout=600)
                except subprocess.TimeoutExpired:
                    pass
            self._backup_proc = None
            self.backup(f"fim do {self.t.id} ({resumo.get('estado')})")
            try:
                self._backup_proc.wait(timeout=600)
            except (subprocess.TimeoutExpired, AttributeError):
                pass
        return rc


# --------------------------------------------------------------------------- acompanhamento

def tracking_update(t: Teste, resumo: dict) -> None:
    """Acrescenta a execução ao histórico e atualiza a última por perfil (DSN2027/testes/)."""
    ACOMP_DIR.mkdir(parents=True, exist_ok=True)
    slim = {k: resumo[k] for k in ("teste", "perfil", "estado", "quando", "commit", "sujo", "congelado", "host",
                                   "segundos", "conferencias", "numeros")}
    append_jsonl(ACOMP_DIR / "historico.jsonl", slim)
    path = ACOMP_DIR / "acompanhamento.json"
    doc = read_json(path, {}) or {}
    entry = doc.get(t.id, {})
    entry.update({"nome": t.nome, "perguntas": t.perguntas, "objetivo": t.objetivo, "gabarito": list(t.gabarito),
                  "pendencias_nuvem": list(t.pendencias)})
    entry.setdefault("ultima", {})[resumo["perfil"]] = slim
    doc[t.id] = entry
    write_json(path, dict(sorted(doc.items(), key=lambda kv: int(kv[0][1:]))))
    render_markdown(doc)


def render_markdown(doc: dict) -> None:
    def cell(e: dict | None) -> str:
        if not e:
            return "—"
        nok = sum(1 for c in e["conferencias"] if c["ok"])
        n = len(e["conferencias"])
        mark = {"ok": "ok", "divergiu": "DIVERGIU", "falhou": "FALHOU", "incompleto": "incompleto"}.get(e["estado"], e["estado"])
        return f"{mark} · {nok}/{n} conf. · {e['segundos'] / 60:.1f} min · {e['quando'][:10]} · `{e['commit'][:8]}`{'*' if e['sujo'] else ''}"

    lines = ["# Acompanhamento dos testes T1 a T11", "",
             "Gerado por `tools/testes/executor.py` a cada execução; o histórico completo está em `historico.jsonl`.",
             "`mini` é a verificação local pequena (não é dado do artigo); `nuvem` é a campanha. `*` = commit sujo.", "",
             "| Teste | Perguntas | mini | nuvem |", "|---|---|---|---|"]
    for tid, e in doc.items():
        lines.append(f"| **{tid}** {e['nome']} | {e['perguntas']} | {cell(e.get('ultima', {}).get('mini'))} | "
                     f"{cell(e.get('ultima', {}).get('nuvem'))} |")
    lines += ["", "## Gabarito e última conferência", ""]
    for tid, e in doc.items():
        lines += [f"### {tid} · {e['nome']}", "", e["objetivo"], "", "**Gabarito:**", ""]
        lines += [f"- {g}" for g in e["gabarito"]]
        for perfil in PERFIS:
            last = e.get("ultima", {}).get(perfil)
            if not last:
                continue
            lines += ["", f"**Última execução `{perfil}`** ({last['quando']}, {last['host']}, `{last['commit'][:12]}`): {last['estado']}", ""]
            for c in last["conferencias"]:
                mark = {True: "✓", False: "✗", None: "·"}[c["ok"]]
                exp = f" (esperado: {c['esperado']})" if c.get("esperado") is not None else ""
                lines.append(f"- {mark} {c['nome']}: `{json.dumps(c['valor'], ensure_ascii=False)}`{exp}")
            if last.get("numeros"):
                lines.append(f"- números: `{json.dumps(last['numeros'], ensure_ascii=False)}`")
        if e.get("pendencias_nuvem"):
            lines += ["", "**Falta para a nuvem:**", ""] + [f"- {x}" for x in e["pendencias_nuvem"]]
        lines.append("")
    (ACOMP_DIR / "ACOMPANHAMENTO.md").write_text("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- linha de comando

def main(teste: Teste, argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=f"{teste.id}: {teste.nome}. {teste.objetivo}")
    ap.add_argument("--perfil", choices=PERFIS, default=os.environ.get("PERFIL", "mini"))
    ap.add_argument("--verificar", action="store_true", help="só o pré-voo: confere se pode rodar, sem rodar")
    ap.add_argument("--passos", nargs="*", help="roda só estes passos (de novo, se já feitos)")
    ap.add_argument("--refazer", nargs="*", default=[], help="refaz estes passos mesmo se já feitos")
    ap.add_argument("--novo", action="store_true", help="começa do zero (a pasta antiga é guardada ao lado)")
    ap.add_argument("--continuar", action="store_true", help="segue para o próximo passo depois de uma falha")
    ap.add_argument("--sem-congelamento", action="store_true", help="perfil nuvem fora do commit congelado (ensaio)")
    ap.add_argument("--listar", action="store_true", help="lista os passos do perfil e sai")
    ap.add_argument("--campanha", default=os.environ.get("TESTES_CAMPANHA"),
                    help="nome da pasta da campanha (padrão: o commit no mini; 'tst' na nuvem, para as duas fases)")
    a = ap.parse_args(argv)
    r = Runner(teste, a.perfil, unfrozen=a.sem_congelamento, novo=a.novo, refazer=set(a.refazer), campanha=a.campanha)
    if a.listar:
        for p in r.steps():
            print(f"{p.id:<22} {p.titulo}{'  [PENDENTE: ' + p.pendente + ']' if p.pendente else ''}\n{'':<22} $ {p.cmd}")
        return 0
    if a.verificar:
        probs = r.preflight(deps=False)
        dep = f" (depois de {', '.join(teste.depende)})" if teste.depende else ""
        print(f"{teste.id} ({a.perfil}): " + (f"pronto para rodar{dep}" if not probs else "NÃO pode rodar:\n  - " + "\n  - ".join(probs)))
        return 0 if not probs else 2
    return r.run(a.passos, a.continuar)
