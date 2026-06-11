# malicious_pkg - simula dependencia comprometida na supply chain.
#
# Este modulo tem DOIS payloads na avaliacao DNAT:
#   - build-time: em setup.py (roda quando o pip constroi o sdist na CVM2).
#   - import-time: abaixo (roda quando a aplicacao importa o pacote na CVM3).
#
# O payload de import-time apenas SONDA o ambiente de execucao e guarda o
# resultado em malicious_pkg.LAST_PROBE, sem exfiltrar nada (a microVM de
# execucao nao tem rede). Existe somente para a Secao de Evaluation do artigo.

import os
import socket
from pathlib import Path

SENSITIVE_ENV = ["ASSET_ENCRYPTION_KEY", "PRIVATE_KEY", "AWS_SECRET_ACCESS_KEY"]
PROBE_FILES = ["/etc/passwd", "/proc/self/cgroup"]


def _probe_environment() -> dict:
    probe: dict = {"stage": "import-time", "env": {}, "files": {}, "network": {}}

    for var in SENSITIVE_ENV:
        probe["env"][var] = "FOUND" if os.environ.get(var) else "absent"

    for f in PROBE_FILES:
        try:
            probe["files"][f] = "readable"
            Path(f).read_text(errors="ignore")
        except Exception as exc:  # noqa: BLE001
            probe["files"][f] = f"blocked: {type(exc).__name__}"

    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect(("8.8.8.8", 53))
        s.close()
        probe["network"]["8.8.8.8:53"] = "REACHABLE"
    except Exception as exc:  # noqa: BLE001
        probe["network"]["8.8.8.8:53"] = f"BLOCKED: {type(exc).__name__}"

    return probe


try:
    LAST_PROBE = _probe_environment()
    print("[malicious_pkg] import-time payload executed:", LAST_PROBE)
except Exception as _exc:  # noqa: BLE001
    LAST_PROBE = {"error": str(_exc)}
