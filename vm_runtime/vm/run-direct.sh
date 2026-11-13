#!/bin/bash
# =============================================================================
# M0 — Runner de execucao DIRETA (sem microVM). Baseline "sem isolamento".
#
# Executa EXATAMENTE o mesmo contrato workspace/run.sh que run-vm.sh, porem
# diretamente no namespace do container: sem Firecracker, sem discos isolados,
# sem remocao de rede. Serve para (1) medir o custo do microVM (boot ~= 0,
# latencia ~= tempo de computo da app) e (2) expor o que o isolamento contem
# (rede alcancavel, env/segredos do host visiveis, filesystem persistente).
#
# Saida (T-804): um JSON {returncode, timed_out, elapsed_seconds, metrics,
# metrics_error, derivative} que executor.py reduz ao esquema fixo de
# job_output.py. stdout e stderr do script vao para /dev/null: um script hostil
# nao tem por onde imprimir pesos. So o arquivo de metricas
# ($DNAT_METRICS_PATH, workspace/metrics.json) e lido, com teto de bytes e
# campos numericos fixos. "derivative" (T-803): o derivado que o job gravou em
# workspace/derivative/, empacotado com o digest por derivative.py e apagado do
# disco; vai so a CVM1, que o retem cifrado.
#
# Tempo limite (T-802): DNAT_JOB_TIMEOUT_SECONDS, que executor.py passa por
# job (padrao 600; substitui o antigo VM_TIMEOUT_SECONDS). Estouro: o grupo do
# script recebe TERM e, 10 s depois (DNAT_JOB_KILL_GRACE_SECONDS), KILL; a
# saida marca timed_out e o derivado e apagado sem ser coletado.
# =============================================================================
set -uo pipefail

BUNDLE_PATH="${1:-}"
[ -f "$BUNDLE_PATH" ] || { echo '{"error": "Bundle not found"}'; exit 1; }

# O run.sh gerado pelo control plane faz `cd /tmp/exec/workspace`; espelhamos o
# mesmo layout que o guest usa em /tmp/exec para rodar o run.sh sem nenhuma
# alteracao (fairness com o caminho do microVM).
# DNAT_EXEC_DIR so existe para os testes; no agente fica /tmp/exec.
EXEC_DIR="${DNAT_EXEC_DIR:-/tmp/exec}"
VM_RUNTIME_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_SYMLINK="/mnt/dnat-app"
TIMEOUT_SECONDS="${DNAT_JOB_TIMEOUT_SECONDS:-600}"
KILL_GRACE_SECONDS="${DNAT_JOB_KILL_GRACE_SECONDS:-10}"

APP_MOUNT=""
cleanup() {
    if [ -n "$APP_MOUNT" ] && mountpoint -q "$APP_MOUNT" 2>/dev/null; then
        umount "$APP_MOUNT" 2>/dev/null || true
        rmdir "$APP_MOUNT" 2>/dev/null || true
    fi
}
trap cleanup EXIT

rm -rf "$EXEC_DIR"
mkdir -p "$EXEC_DIR"
if ! tar -xzf "$BUNDLE_PATH" -C "$EXEC_DIR" 2>/dev/null; then
    echo '{"error": "failed to extract bundle"}'
    exit 1
fi
[ -d "$EXEC_DIR/workspace" ] || { echo '{"error": "workspace missing from execution bundle"}'; exit 1; }

# Artefato opcional da aplicacao: espelha o /mnt/dnat-app read-only do microVM
# para bundles construidos pelo builder (no modo script nao ha artifacts/).
if [ -f "$EXEC_DIR/artifacts/application.ext4" ]; then
    APP_MOUNT="$(mktemp -d)"
    if mount -o loop,ro "$EXEC_DIR/artifacts/application.ext4" "$APP_MOUNT" 2>/dev/null; then
        rm -f "$APP_SYMLINK" 2>/dev/null || true
        ln -s "$APP_MOUNT" "$APP_SYMLINK" 2>/dev/null || true
    else
        rmdir "$APP_MOUNT" 2>/dev/null || true
        APP_MOUNT=""
    fi
fi

# Sem isolamento: a aplicacao herda rede, variaveis de ambiente e filesystem do
# container. Saida bruta descartada (T-804). O limite (T-802) corta o grupo de
# processos do script: TERM e, depois da folga, KILL. Feito em Python e nao
# com `timeout`, porque nem todo `timeout` (uutils) mata os netos.
python3 - "$TIMEOUT_SECONDS" "$KILL_GRACE_SECONDS" "$VM_RUNTIME_DIR" "$EXEC_DIR/workspace" <<'PY'
import json, os, shutil, signal, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[3])
from derivative import DERIVATIVE_DIRNAME, collect
from job_output import METRICS_FILENAME, read_metrics_file

limit, grace = int(sys.argv[1]), int(sys.argv[2])
workspace = Path(sys.argv[4])


def kill_group(proc, sig):
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        pass


started = time.monotonic()
proc = subprocess.Popen(
    ["bash", str(workspace / "run.sh")],
    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    start_new_session=True,
)
timed_out = False
try:
    rc = proc.wait(timeout=limit)
except subprocess.TimeoutExpired:
    timed_out = True
    kill_group(proc, signal.SIGTERM)
    try:
        proc.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        pass
    kill_group(proc, signal.SIGKILL)
    proc.wait()
    rc = 124
elapsed = time.monotonic() - started

metrics, metrics_error = read_metrics_file(workspace / METRICS_FILENAME)
if timed_out:
    # Derivado de job que estourou o tempo nao e coletado: e apagado do disco.
    shutil.rmtree(workspace / DERIVATIVE_DIRNAME, ignore_errors=True)
    derivative = None
else:
    derivative = collect(workspace)
print(json.dumps({
    "returncode": rc,
    "timed_out": timed_out,
    "elapsed_seconds": elapsed,
    "metrics": metrics,
    "metrics_error": metrics_error,
    "derivative": derivative,
}))
PY
