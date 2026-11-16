#!/usr/bin/env python3
"""Verifica o ambiente local do DNAT e diz o que falta, em português, com o comando que resolve.

    make doctor            (ou: python3 -I tools/doctor.py [--json])

Só lê; nada aqui muda arquivos, containers ou processos. Seções: ferramentas, ambientes, dados do
model_gate, pilha Docker, higiene (temporários, execuções antigas, containers de job órfãos) e git.
Saída 0 se não há erro (avisos não contam), 1 se há.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SC = REPO / "smart-contract"
MG = REPO / "model_gate"
DATA = Path(os.environ.get("MODEL_GATE_DATA", Path.home() / "model_gate_data")).expanduser()
QWEN = DATA / "models" / "Qwen__Qwen2.5-0.5B-Instruct" / "7ae557604adf67be50417f59c2c2f167def9a775"
PLAINTEXT = ("bundle.tar.gz", "dataset.csv", "application.ext4", "workspace")

rows: list[tuple[str, str, str, str]] = []  # (seção, nível, mensagem, como resolver)


def add(section: str, level: str, msg: str, fix: str = "") -> None:
    rows.append((section, level, msg, fix))


def run(*cmd: str, cwd: Path | None = None, timeout: int = 60) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, str(e)


def size(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    total = 0
    for root, _, files in os.walk(p):
        for f in files:
            try:
                total += (Path(root) / f).lstat().st_size
            except OSError:
                pass
    return total


def gb(n: int) -> str:
    return f"{n / 2**30:.1f} GB" if n >= 2**30 else f"{n / 2**20:.0f} MB"


def tools() -> None:
    s = "Ferramentas"
    for name, need, fix in [("node", True, "instale o Node 22"), ("npm", True, "vem com o Node"),
                            ("uv", True, "https://docs.astral.sh/uv/"), ("docker", False, "só para a pilha Docker e os testes T1–T5"),
                            ("google-chrome", False, "só para conferir a interface headless")]:
        if shutil.which(name):
            add(s, "ok", name)
        else:
            add(s, "erro" if need else "aviso", f"{name} não encontrado", fix)
    code, out = run("node", "--version")
    if code == 0 and int(out.lstrip("v").split(".")[0]) < 22:
        add(s, "erro", f"node {out}: os roteiros usam fetch e WebSocket nativos do Node 22", "atualize o Node")


def envs() -> None:
    s = "Ambientes"
    if not (SC / "node_modules").is_dir():
        add(s, "erro", "smart-contract sem node_modules", "make setup")
    else:
        add(s, "ok", "dependências do smart-contract instaladas")
    art = SC / "artifacts" / "contracts" / "DnatMarketplace.sol" / "DnatMarketplace.json"
    sol = SC / "contracts" / "DnatMarketplace.sol"
    if not art.exists():
        add(s, "erro", "contrato não compilado", "make setup")
    elif art.stat().st_mtime < sol.stat().st_mtime:
        add(s, "aviso", "o contrato mudou depois da última compilação", "cd smart-contract && npx hardhat compile")
    else:
        add(s, "ok", "contrato compilado")
    if not (MG / ".venv").is_dir():
        add(s, "erro", "model_gate sem ambiente (.venv)", "make setup")
    else:
        code, out = run("uv", "sync", "--frozen", "--dry-run", cwd=MG)
        if code != 0:
            add(s, "aviso", "não deu para conferir o ambiente do model_gate contra o uv.lock", "cd model_gate && ./setup.sh")
        elif "Would" in out and "Would make no changes" not in out:
            add(s, "aviso", "o ambiente do model_gate está fora do uv.lock", "cd model_gate && ./setup.sh")
        else:
            add(s, "ok", "ambiente do model_gate igual ao uv.lock")


def data() -> None:
    s = "Dados do model_gate"
    if not DATA.is_dir():
        add(s, "erro", f"{DATA} não existe", "uv run python -m experiments.fetch_base e fetch_datasets (model_gate/README)")
        return
    man = MG / "models" / "base.manifest.json"
    if (QWEN / "model.safetensors").exists():
        add(s, "ok", f"base Qwen2.5-0.5B em {QWEN.parent.parent.name}")
    else:
        add(s, "erro", "base Qwen2.5-0.5B ausente", "cd model_gate && uv run python -m experiments.fetch_base")
    for rel, fix in [("battery/local_t807", "uv run python -m experiments.battery_pack (pacote da T-807)"),
                     ("references/base_05b61d72bec3/refusal_dirs.safetensors", "uv run python -m experiments.s2_reference (T-402)"),
                     ("derivatives/fumaca-abl-d12-a1-todas", "receita de fumaça da T-908"),
                     ("datasets", "uv run python -m experiments.fetch_datasets")]:
        add(s, "ok" if (DATA / rel).exists() else "aviso", rel if (DATA / rel).exists() else f"falta {rel}", "" if (DATA / rel).exists() else fix)
    refs = [d for d in (DATA / "references").glob("t807_detector_*") if (d / "reference.json").exists()] if (DATA / "references").is_dir() else []
    add(s, "ok" if refs else "aviso", f"referência do pai medida (T-807): {len(refs)}",
        "" if refs else "taskset -c 0-3 uv run python -m experiments.judge_local (mede o pai; ~10 min)")
    fm = MG / "models" / "field.manifest.json"
    if fm.exists():
        man = json.loads(fm.read_text())
        for fam, v in man.get("por_familia", {}).items():
            # o manifesto é versionado: conta o que está NESTA máquina, não o que foi baixado onde ele foi gerado
            here = sum(1 for d in man.get("derivados", []) if d.get("familia") == fam and not d.get("problems")
                       and d.get("path") and all((DATA / d["path"] / f["path"]).exists() for f in d.get("files", [])))
            lvl = "ok" if here == v.get("aceitos") else "aviso"
            fix = "" if lvl == "ok" else ("aceitar a licença da Meta e rodar field_download --familia llama-3.2-1b --aceito-licenca-meta"
                                          if fam.startswith("llama") else f"cd model_gate && uv run python -m experiments.field_download --familia {fam}")
            add(s, lvl, f"campo {fam}: {here} de {v.get('aceitos', 0)} nesta máquina", fix)
    add(s, "info", f"{DATA}: {gb(size(DATA))}")


def judge_hash() -> str | None:
    code, out = run("uv", "run", "--frozen", "--quiet", "python", "-c",
                    "from model_gate.judge_package import judge_hash; print(judge_hash()[0])", cwd=MG, timeout=120)
    return out.splitlines()[-1].strip() if code == 0 and out else None


def docker_stack() -> None:
    s = "Pilha Docker"
    if not shutil.which("docker"):
        return
    code, out = run("docker", "ps", "--format", "{{.Names}}\t{{.Status}}")
    if code != 0:
        add(s, "aviso", "docker não respondeu", "o daemon está no ar? permissão no socket?")
        return
    running = dict(line.split("\t", 1) for line in out.splitlines() if "\t" in line)
    names = ("dnat-client", "dnat-builder", "dnat-executor")
    if not any(n in running for n in names):
        add(s, "info", "pilha Docker parada", "make stack-up (só para os testes T1–T5; para usar a interface, make dev)")
        return
    for n in names:
        add(s, "ok" if n in running else "erro", f"{n}: {running.get(n, 'parado')}", "" if n in running else "make stack-up")
    code, created = run("docker", "inspect", "dnat-client-direct:latest", "--format", "{{.Created}}")
    code2, last = run("git", "log", "-1", "--format=%cI", "--", "smart-contract", "model_gate/src", "vm_runtime", "build_vm_runtime", "docker", cwd=REPO)
    if code == 0 and code2 == 0 and created[:19] < last[:19]:
        add(s, "aviso", f"imagem da CVM1 de {created[:16]} é anterior ao código ({last[:16]}): a interface e o Juiz no container estão velhos",
            "make stack-up (reconstrói; a cadeia em memória recomeça vazia)")
    code, allow = run("docker", "exec", "dnat-client", "cat", "/app/smart-contract/judge_allowlist.json")
    if code != 0:
        add(s, "aviso", "nenhum Juiz liberado no container: todo job termina sem veredito", "make stack-seed")
    else:
        h = judge_hash()
        hashes = [j.get("judgeHash") for j in json.loads(allow).get("judges", [])]
        if h and h not in hashes:
            add(s, "aviso", "o Juiz liberado no container não é o do código atual (judge_not_allowed)", "make stack-up && make stack-seed")
        else:
            add(s, "ok", "Juiz atual liberado no container")


def hygiene() -> None:
    s = "Higiene"
    tmp = list(Path("/tmp").glob("dnat-*"))
    old = [p for p in tmp if time.time() - p.stat().st_mtime > 3600]
    if old:
        add(s, "aviso", f"{len(old)} pastas /tmp/dnat-* com mais de 1 h ({gb(sum(size(p) for p in old))})", "make clean")
    else:
        add(s, "ok", "sem temporários antigos em /tmp")
    ex = SC / "executions"
    if ex.is_dir():
        dirty = [d for d in ex.iterdir() if d.is_dir() and any((d / f).exists() for f in PLAINTEXT)]
        if dirty:
            add(s, "erro", f"{len(dirty)} execuções antigas guardam dataset, base ou bundle EM CLARO ({gb(sum(size(d) for d in dirty))})",
                "make clean-executions (apaga só esses arquivos; metadata.json e result.json ficam)")
        else:
            add(s, "ok", f"execuções sem texto claro ({len(list(ex.iterdir()))} em smart-contract/executions)")
    if shutil.which("docker"):
        code, out = run("docker", "ps", "-a", "--filter", "label=dnat.role=job-vm", "--format", "{{.Names}}")
        orphans = [x for x in out.splitlines() if x] if code == 0 else []
        dev = (SC / ".dev_stack.json").exists()
        if orphans and not dev:
            add(s, "aviso", f"{len(orphans)} containers de CVM de job sem pilha no ar", "make clean")
        else:
            add(s, "ok", "sem CVMs de job órfãs")
    code, out = run("pgrep", "-af", "hardhat node --hostname 127.0.0.1")
    procs = [x for x in out.splitlines() if "pgrep" not in x] if code == 0 else []
    if procs and not (SC / ".dev_stack.json").exists():
        add(s, "aviso", f"{len(procs)} nós do Hardhat de pilhas e2e ainda no ar", "make clean (encerra os de pilhas descartáveis)")
    if (SC / ".dev_stack.json").exists():
        st = json.loads((SC / ".dev_stack.json").read_text())
        add(s, "info", f"pilha de desenvolvimento no ar: {st.get('url')}")


def git() -> None:
    s = "Git"
    code, br = run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=REPO)
    if code != 0:
        add(s, "aviso", "não é um repositório git: as runs gravam commit desconhecido", "clone com git (não copie os arquivos)")
        return
    _, st = run("git", "status", "--porcelain", cwd=REPO)
    _, ahead = run("git", "rev-list", "--count", "@{u}..HEAD", cwd=REPO)
    n = len([x for x in st.splitlines() if x])
    add(s, "info", f"ramo {br}; {n} arquivos modificados; {ahead if ahead.isdigit() else '?'} commits sem push")
    if n:
        add(s, "aviso", "runs com o repositório sujo gravam dirty=true no registro de experimentos", "commit antes de rodar experimentos")


def main() -> int:
    for f in (tools, envs, data, docker_stack, hygiene, git):
        try:
            f()
        except Exception as e:  # um bloco que falha não esconde os outros
            add(f.__name__, "aviso", f"verificação falhou: {e}")
    if "--json" in sys.argv:
        print(json.dumps([dict(zip(("secao", "nivel", "msg", "fix"), r)) for r in rows], ensure_ascii=False, indent=1))
    else:
        mark = {"ok": "✓", "aviso": "!", "erro": "✗", "info": "·"}
        last = None
        for sec, lvl, msg, fix in rows:
            if sec != last:
                print(f"\n{sec}")
                last = sec
            print(f"  {mark[lvl]} {msg}" + (f"\n      → {fix}" if fix and lvl != "ok" else ""))
        e = sum(r[1] == "erro" for r in rows)
        w = sum(r[1] == "aviso" for r in rows)
        print(f"\n{e} erros, {w} avisos")
    return 1 if any(r[1] == "erro" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
