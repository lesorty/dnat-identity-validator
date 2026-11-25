#!/usr/bin/env python3
"""Ficha da máquina (T-210): o que descreve a bancada no artigo e acompanha cada pacote de resultados.

    python3 -I tools/cloud/machine_card.py [--out ARQUIVO.json] [--quiet]

Só biblioteca padrão. Registra CPU (modelo, núcleos, extensões que decidem o custo do avaliador:
AVX-512, AVX-512 BF16, AMX), memória, disco livre em $MODEL_GATE_DATA, sistema, se a VM é
confidencial (SEV-SNP ou TDX, pelo dispositivo do convidado e pelo log do kernel), a nuvem e o tipo
de VM (metadados da Azure ou da Oracle, se houver) e as versões (git, Node, uv, Python, torch, hash do
Juiz). Grava em $MODEL_GATE_DATA/machine/<host>.json por padrão e imprime um resumo.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("MODEL_GATE_DATA", Path.home() / "model_gate_data")).expanduser()
FLAGS = ("avx2", "avx512f", "avx512_bf16", "avx512_vnni", "amx_tile", "amx_bf16", "amx_int8", "avx_vnni", "sev", "sev_es", "sev_snp")


def sh(*cmd: str, cwd: Path | None = None, timeout: int = 60) -> str | None:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.stdout.strip() if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def cpu() -> dict:
    info = {}
    try:
        txt = Path("/proc/cpuinfo").read_text()
    except OSError:
        return {"model": platform.processor()}
    first = txt.split("\n\n")[0]
    kv = dict(line.split(":", 1) for line in first.splitlines() if ":" in line)
    flags = set(kv.get("flags\t\t", kv.get("flags", "")).split())
    info["model"] = kv.get("model name\t", kv.get("model name", "")).strip()
    info["vendor"] = kv.get("vendor_id\t", kv.get("vendor_id", "")).strip()
    info["logical_cpus"] = os.cpu_count()
    info["affinity"] = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None
    info["flags"] = {f: f in flags for f in FLAGS}
    lscpu = sh("lscpu", "-J")
    if lscpu:
        rows = {r["field"].rstrip(":"): r["data"] for r in json.loads(lscpu).get("lscpu", [])}
        info["threads_per_core"] = rows.get("Thread(s) per core")
        info["sockets"] = rows.get("Socket(s)")
        info["hypervisor"] = rows.get("Hypervisor vendor")
    return info


def memory() -> dict:
    try:
        kv = {l.split(":")[0]: int(l.split()[1]) for l in Path("/proc/meminfo").read_text().splitlines() if l.split()[1].isdigit()}
        return {"total_gb": round(kv["MemTotal"] / 2**20, 1), "available_gb": round(kv.get("MemAvailable", 0) / 2**20, 1)}
    except (OSError, KeyError, IndexError):
        return {}


def confidential() -> dict:
    out = {"sev_guest_device": Path("/dev/sev-guest").exists(), "tdx_guest_device": Path("/dev/tdx_guest").exists()}
    log = sh("dmesg") or sh("journalctl", "-k", "-b", "--no-pager", "-q") or ""
    line = next((l for l in log.splitlines() if "Memory Encryption Features active" in l), None)
    out["kernel_line"] = line.split("]", 1)[-1].strip() if line else None
    out["kind"] = ("SEV-SNP" if (out["sev_guest_device"] or (line and "SEV-SNP" in line))
                   else "TDX" if out["tdx_guest_device"] or (line and "TDX" in line) else None)
    return out


def gpu() -> dict:
    """Placas da NVIDIA, driver e o modo confidencial da placa (Hopper em CC: o tráfego CPU↔GPU cifrado)."""
    q = sh("nvidia-smi", "--query-gpu=name,memory.total,driver_version,serial", "--format=csv,noheader")
    if not q:
        return {"present": False}
    cards = [dict(zip(("name", "memory", "driver", "serial"), [x.strip() for x in l.split(",")])) for l in q.splitlines()]
    cc = sh("nvidia-smi", "conf-compute", "-f") or ""
    ready = sh("nvidia-smi", "conf-compute", "-grs") or ""
    return {"present": True, "cards": cards, "cc_mode": cc.strip() or None, "cc_ready_state": ready.strip() or None,
            "cc_on": "ON" in cc.upper(), "attestation": "não verificada pelo DNAT (verificador local da NVIDIA fora do escopo)"}


def metadata(url: str, headers: dict) -> dict | None:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=1.5) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def cloud() -> dict:
    az = metadata("http://169.254.169.254/metadata/instance/compute?api-version=2021-02-01", {"Metadata": "true"})
    if az:
        return {"provider": "azure", "vm_size": az.get("vmSize"), "location": az.get("location"),
                "security_type": (az.get("securityProfile") or {}).get("securityType"), "image": (az.get("storageProfile") or {}).get("imageReference")}
    oci = metadata("http://169.254.169.254/opc/v2/instance/", {"Authorization": "Bearer Oracle"})
    if oci:
        return {"provider": "oracle", "shape": oci.get("shape"), "region": oci.get("canonicalRegionName") or oci.get("region"),
                "shape_config": oci.get("shapeConfig")}
    gcp = metadata("http://metadata.google.internal/computeMetadata/v1/instance/?recursive=true", {"Metadata-Flavor": "Google"})
    if gcp:
        sched = gcp.get("scheduling") or {}
        return {"provider": "gcp", "vm_size": str(gcp.get("machineType", "")).rsplit("/", 1)[-1],
                "location": str(gcp.get("zone", "")).rsplit("/", 1)[-1],
                "provisioning": sched.get("provisioningModel") or ("SPOT" if sched.get("preemptible") == "TRUE" else None),
                "on_preempt": sched.get("instanceTerminationAction")}
    return {"provider": None}


def software() -> dict:
    mg = REPO / "model_gate"
    commit = sh("git", "rev-parse", "HEAD", cwd=REPO)
    torch = sh("uv", "run", "--frozen", "--quiet", "python", "-c",
               "import torch; print(torch.__version__, torch.backends.mkldnn.is_available(), torch.get_num_threads(), "
               "'cuda', torch.version.cuda, torch.cuda.is_available())", cwd=mg, timeout=180)
    jh = sh("uv", "run", "--frozen", "--quiet", "python", "-c",
            "from model_gate.judge_package import judge_hash; print(judge_hash()[0])", cwd=mg, timeout=180)
    return {
        "git_commit": commit, "git_dirty": bool(sh("git", "status", "--porcelain", cwd=REPO)),
        "git_tags": (sh("git", "tag", "--points-at", "HEAD", cwd=REPO) or "").split(),
        "node": sh("node", "--version"), "uv": sh("uv", "--version"), "python": sys.version.split()[0],
        "torch": torch, "judge_hash": jh.splitlines()[-1] if jh else None,
        "docker": sh("docker", "--version"),
    }


def main() -> int:
    out = None
    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
    host = socket.gethostname()
    try:
        os_release = dict(l.split("=", 1) for l in Path("/etc/os-release").read_text().splitlines() if "=" in l)
    except OSError:
        os_release = {}
    card = {
        "schema": "dnat.machine-card.v1", "host": host, "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "os": os_release.get("PRETTY_NAME", "").strip('"'), "kernel": platform.release(),
        "cpu": cpu(), "memory": memory(), "confidential": confidential(), "gpu": gpu(), "cloud": cloud(), "software": software(),
        "disk_free_gb": round(shutil.disk_usage(DATA if DATA.exists() else Path.home()).free / 2**30, 1),
        "model_gate_data": str(DATA),
    }
    out = out or (DATA / "machine" / f"{host}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(card, indent=1, ensure_ascii=False) + "\n")
    if "--quiet" not in sys.argv:
        c, f = card["cpu"], card["cpu"].get("flags", {})
        print(f"máquina {host}: {c.get('model')} · {c.get('logical_cpus')} CPUs lógicas · {card['memory'].get('total_gb')} GB")
        print(f"  extensões: " + ", ".join(k for k, v in f.items() if v and not k.startswith("sev")) )
        print(f"  bf16 acelerado: {'sim' if f.get('avx512_bf16') or f.get('amx_bf16') else 'NÃO (o avaliador em bf16 fica lento: escolha outra família de VM)'}")
        print(f"  confidencial: {card['confidential']['kind'] or 'não detectado'} · nuvem: {card['cloud'].get('provider') or 'nenhuma'} "
              f"{card['cloud'].get('vm_size') or card['cloud'].get('shape') or ''}")
        g = card["gpu"]
        if g.get("present"):
            print(f"  GPU: {', '.join(c['name'] + ' ' + c['memory'] for c in g['cards'])} · driver {g['cards'][0]['driver']} · "
                  f"modo confidencial da placa: {'LIGADO' if g['cc_on'] else 'desligado'}")
        s = card["software"]
        print(f"  commit {str(s['git_commit'])[:12]}{' (sujo)' if s['git_dirty'] else ''} · Juiz {str(s['judge_hash'])[:12]} · {s['torch'] or 'torch ?'}")
        print(f"  ficha em {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
