#!/usr/bin/env python3
"""T1b - Teste de contencao no sistema de arquivos (execution plane / CVM3).

Complementa o T1 (rede). Aqui a aplicacao maliciosa, ja dentro da microVM de
execucao, tenta:
  1. Ler segredos do ambiente (ASSET_ENCRYPTION_KEY, PRIVATE_KEY, AWS_*).
  2. Ler arquivos sensiveis do guest/host (/etc/passwd, /proc, /run/secrets).
  3. Enumerar e montar discos vizinhos (vdb..vde) para encontrar o disco da
     aplicacao de outras execucoes ou o proprio artefato em claro.
  4. Escrever fora do workspace efemero (persistencia entre execucoes).
  5. Inspecionar o artefato read-only da aplicacao montado em /mnt/dnat-app.

A microVM de execucao roda como root, entao varios reads internos ao guest
SAO esperados (o guest e descartavel). O ponto cientifico nao e impedir todo
acesso DENTRO da microVM efemera, e sim mostrar que: (a) nao ha segredos do
control plane no ambiente, e (b) nada escrito aqui sobrevive ou alcanca outro
plano, porque o disco e destruido apos o run (validado por T3).

Marcadores greppaveis em stdout:
    [T1B] SECRET-FOUND <var>      -> vazamento de segredo (FALHA)
    [T1B] NO-SECRETS              -> nenhum segredo de control plane presente (OK)
    [T1B] WRITE-OK <path>         -> escrita fora do workspace efetivada
    [T1B] JSON {...}
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SENSITIVE_ENV = [
    "ASSET_ENCRYPTION_KEY",
    "PRIVATE_KEY",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_ACCESS_KEY_ID",
    "RPC_URL",
    "IPFS_API_URL",
    "BUILDER_URL",
    "EXECUTOR_URL",
]

PROBE_FILES = [
    "/etc/passwd",
    "/etc/shadow",
    "/etc/hostname",
    "/proc/version",
    "/proc/self/cgroup",
    "/run/secrets/key",
    "/root/.ssh/id_rsa",
]

WRITE_TARGETS = [
    "/marker_escape.txt",          # raiz do rootfs (efemero do guest)
    "/tmp/exec/persist_marker.txt",  # workspace efemero
    "/mnt/dnat-app/escape.txt",    # artefato read-only (deve falhar)
    "/persisted/escape.txt",       # caminho inexistente (deve falhar)
]

CANDIDATE_DISKS = ["/dev/vdb", "/dev/vdc", "/dev/vdd", "/dev/vde"]


def probe_env() -> dict:
    found = {}
    for var in SENSITIVE_ENV:
        val = os.environ.get(var)
        if val is not None:
            found[var] = val[:16] + "..." if len(val) > 16 else val
    return found


def probe_files() -> dict:
    out = {}
    for f in PROBE_FILES:
        try:
            out[f] = "READABLE: " + Path(f).read_text(errors="ignore")[:80].replace("\n", "\\n")
        except Exception as exc:  # noqa: BLE001
            out[f] = f"blocked: {type(exc).__name__}"
    return out


def probe_writes() -> dict:
    out = {}
    for path in WRITE_TARGETS:
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("DNAT-T1B persistence attempt\n", encoding="utf-8")
            out[path] = "WRITE-OK"
            print(f"[T1B] WRITE-OK {path}")
        except Exception as exc:  # noqa: BLE001
            out[path] = f"blocked: {type(exc).__name__}"
    return out


def probe_block_devices() -> dict:
    out = {}
    for disk in CANDIDATE_DISKS:
        if not Path(disk).exists():
            out[disk] = "absent"
            continue
        mnt = f"/mnt/probe_{Path(disk).name}"
        try:
            os.makedirs(mnt, exist_ok=True)
            res = subprocess.run(
                ["mount", "-o", "ro", disk, mnt],
                capture_output=True, text=True, timeout=10,
            )
            if res.returncode == 0:
                listing = sorted(os.listdir(mnt))[:10]
                out[disk] = {"mounted": True, "entries": listing}
                subprocess.run(["umount", mnt], capture_output=True, timeout=10)
            else:
                out[disk] = {"mounted": False, "error": res.stderr.strip()[:80]}
        except Exception as exc:  # noqa: BLE001
            out[disk] = {"mounted": False, "error": f"{type(exc).__name__}"}
    return out


def probe_app_artifact() -> dict:
    app = Path("/mnt/dnat-app")
    if not app.exists():
        return {"present": False}
    info = {"present": True, "entries": []}
    try:
        for p in app.rglob("*"):
            rel = str(p.relative_to(app))
            info["entries"].append(rel)
            if len(info["entries"]) >= 30:
                break
    except Exception as exc:  # noqa: BLE001
        info["error"] = str(exc)
    return info


def main() -> int:
    parser = argparse.ArgumentParser(description="DNAT T1b filesystem containment probe")
    parser.add_argument("--dataset", default="data/dataset.csv")
    parser.add_argument("--output", default="")
    args, _unknown = parser.parse_known_args()

    report = {
        "test": "T1b-filesystem-containment",
        "uid": os.getuid(),
        "env_secrets": probe_env(),
        "file_reads": probe_files(),
        "block_devices": probe_block_devices(),
        "app_artifact": probe_app_artifact(),
        "write_escapes": probe_writes(),
    }

    secrets = report["env_secrets"]
    if secrets:
        for var in secrets:
            print(f"[T1B] SECRET-FOUND {var}")
        print(f"[T1B] OVERALL: SECRETS LEAKED count={len(secrets)}")
    else:
        print("[T1B] NO-SECRETS")
        print("[T1B] OVERALL: NO CONTROL-PLANE SECRETS IN EXECUTION ENV")

    writes_ok = [p for p, v in report["write_escapes"].items() if v == "WRITE-OK"]
    print(f"[T1B] writable-paths-outside-workspace={len(writes_ok)} (efemeros; ver T3)")

    print("[T1B] JSON " + json.dumps(report))

    if args.output:
        try:
            Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
