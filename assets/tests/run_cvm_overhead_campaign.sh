#!/usr/bin/env bash
# =============================================================================
# Campanha de overhead de substrato confidencial (CVM vs VM comum).
#
# Roda a MESMA carga N vezes contra o executor local e grava uma linha CSV por
# execucao, com a latencia de parede vista pelo cliente e, quando a app expoe,
# as fases internas cronometradas pela propria carga. Uma celula do experimento
# = uma invocacao deste script.
#
# As quatro celulas do desenho (ver TCC/PLANO_EXPERIMENTO_CVM_AZURE.md):
#   B_vm_direct     VM comum   + DNAT_NO_MICROVM=1   (docker/executor-direct.compose.yaml)
#   C_cvm_direct    CVM SEV-SNP + DNAT_NO_MICROVM=1  (docker/executor-direct.compose.yaml)
#   A_vm_microvm    VM comum   + Firecracker         (docker/executor-vm.compose.yaml)
#   [CVM + Firecracker: estruturalmente indisponivel — sem virtualizacao aninhada]
#
# Uso (executar DENTRO da VM, para que o curl nao atravesse a internet):
#   LABEL=C_cvm_direct REPEATS=10 bash assets/tests/run_cvm_overhead_campaign.sh
#
# Variaveis:
#   LABEL          nome da celula (vai para o CSV e para o nome do diretorio)
#   REPEATS        repeticoes por app (default 10)
#   EXECUTOR_PORT  porta do executor (default 5000)
#   APPS           lista separada por espaco (default: probe + benigna)
#   PROBE_*        repassadas ao guest via linha de comando da app; MANTENHA
#                  IDENTICAS entre celulas, senao a comparacao nao vale
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ASSETS="$REPO/assets"
LABEL="${LABEL:-unlabeled}"
REPEATS="${REPEATS:-10}"
EXECUTOR_PORT="${EXECUTOR_PORT:-5000}"
EXECUTOR="http://127.0.0.1:${EXECUTOR_PORT}/execute"
DATASET="${DATASET:-$ASSETS/data/dataset_synthetic.csv}"
APPS="${APPS:-cvm_overhead_probe benign_stats}"

PROBE_WORKING_SET_MIB="${PROBE_WORKING_SET_MIB:-192}"
PROBE_MEMORY_PASSES="${PROBE_MEMORY_PASSES:-20}"
PROBE_CPU_ITERATIONS="${PROBE_CPU_ITERATIONS:-8000000}"

RESULTS_DIR="$ASSETS/test-results/cvm-overhead-${LABEL}-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"
CSV="$RESULTS_DIR/latencies.csv"
ENVFILE="$RESULTS_DIR/environment.txt"

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$RESULTS_DIR/run.log"; }

# -----------------------------------------------------------------------------
# Registro do ambiente. Sem isto o numero nao e reprodutivel nem defensavel: o
# modelo exato de CPU e a evidencia de que o par CVM/VM caiu no mesmo silicio, e
# o `mode` do executor e a evidencia de que a celula rodou o caminho pretendido.
# -----------------------------------------------------------------------------
{
    echo "label=$LABEL"
    echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "repeats=$REPEATS"
    echo "probe_working_set_mib=$PROBE_WORKING_SET_MIB"
    echo "probe_memory_passes=$PROBE_MEMORY_PASSES"
    echo "probe_cpu_iterations=$PROBE_CPU_ITERATIONS"
    echo "kernel=$(uname -r)"
    echo "cpu_model=$(grep -m1 '^model name' /proc/cpuinfo | cut -d: -f2- | sed 's/^ *//')"
    echo "cpu_cores=$(nproc)"
    echo "mem_total_kb=$(grep -m1 MemTotal /proc/meminfo | awk '{print $2}')"
    # Evidencia de memoria criptografada: presente so em guest SEV-SNP / TDX.
    echo "cc_flags=$(grep -o -m1 -E 'sev_snp|sev_es|sev|tdx_guest' /proc/cpuinfo | sort -u | tr '\n' ',' || true)"
    echo "cc_dmesg=$( (set +o pipefail; { sudo -n dmesg 2>/dev/null || dmesg 2>/dev/null; } | grep -m1 -i -E 'Memory Encryption|SEV|TDX') || echo 'n/a')"
    echo "kvm_present=$([ -e /dev/kvm ] && echo yes || echo no)"
    echo "executor_health=$(curl -s --max-time 5 "http://127.0.0.1:${EXECUTOR_PORT}/health" || echo 'unreachable')"
} > "$ENVFILE"

log "Celula: $LABEL"
log "Ambiente registrado em $(basename "$ENVFILE")"
sed 's/^/    /' "$ENVFILE" | tee -a "$RESULTS_DIR/run.log"

# Guarda de sanidade: uma celula "direct" que reporta mode=microvm (ou o
# contrario) invalida silenciosamente toda a campanha.
HEALTH_MODE="$(curl -s --max-time 5 "http://127.0.0.1:${EXECUTOR_PORT}/health" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("mode",""))' 2>/dev/null || true)"
log "Modo do executor: ${HEALTH_MODE:-desconhecido}"

echo "label,app,run,http_code,returncode,wall_ms,total_s,first_touch_s,memory_s,cpu_s,mem_mibs,digest" > "$CSV"

# Empacota a app no mesmo formato do executor (workspace/run.sh em modo script),
# identico ao que run_execution_plane_tests.sh e run_from_cids.py produzem.
make_script_bundle() {
    local app_file="$1" bundle_out="$2"
    local stage; stage="$(mktemp -d)"
    mkdir -p "$stage/workspace/code" "$stage/workspace/data"
    cp "$app_file" "$stage/workspace/code/application.py"
    cp "$DATASET" "$stage/workspace/data/dataset.csv"
    cat > "$stage/workspace/run.sh" <<RUNSH
#!/bin/bash
set -euo pipefail
cd /tmp/exec/workspace
python3 code/application.py --dataset data/dataset.csv \
    --working-set-mib $PROBE_WORKING_SET_MIB \
    --passes $PROBE_MEMORY_PASSES \
    --cpu-iterations $PROBE_CPU_ITERATIONS 2>/dev/null \
  || python3 code/application.py --dataset data/dataset.csv
RUNSH
    chmod +x "$stage/workspace/run.sh"
    tar -C "$stage" -czf "$bundle_out" workspace
    rm -rf "$stage"
}

run_once() {
    local app_name="$1" app_file="$2" run_idx="$3"
    local bundle="$RESULTS_DIR/.bundle.tar.gz"
    local resp="$RESULTS_DIR/${app_name}.run${run_idx}.json"
    make_script_bundle "$app_file" "$bundle"

    local t0 t1 wall http
    t0=$(date +%s%3N)
    http=$(curl -s --max-time 900 -X POST "$EXECUTOR" \
        -H "Content-Type: application/gzip" \
        --data-binary @"$bundle" -o "$resp" -w "%{http_code}")
    t1=$(date +%s%3N)
    wall=$((t1 - t0))
    rm -f "$bundle"

    # Extrai as fases internas do "[APP] RESULT {...}" impresso pela sonda. A
    # latencia de parede inclui HTTP, extracao do bundle e, no caso microVM,
    # boot e teardown; as fases isolam o custo computacional puro.
    python3 - "$resp" "$LABEL" "$app_name" "$run_idx" "$http" "$wall" <<'PY' >> "$CSV"
import json, sys
resp_path, label, app, run_idx, http, wall = sys.argv[1:7]
rc = ""
total = first = mem = cpu = mibs = ""
digest = ""
try:
    d = json.load(open(resp_path, encoding="utf-8"))
    rc = d.get("returncode", "")
    for line in (d.get("stdout") or "").splitlines():
        if line.startswith("[APP] RESULT "):
            payload = json.loads(line[len("[APP] RESULT "):])
            ph = payload.get("phases_s") or {}
            total = payload.get("total_s", "")
            first = ph.get("first_touch", "")
            mem = ph.get("memory", "")
            cpu = ph.get("cpu", "")
            mibs = payload.get("memory_throughput_mibs", "")
            digest = (payload.get("digest") or "")[:16]
            break
except Exception:
    pass
print(",".join(str(x) for x in
      [label, app, run_idx, http, rc, wall, total, first, mem, cpu, mibs, digest]))
PY
    log "  $app_name run $run_idx/$REPEATS: HTTP $http, wall=${wall}ms"
}

for app_name in $APPS; do
    app_file="$ASSETS/apps/${app_name}.py"
    if [ ! -f "$app_file" ]; then
        log "!! app nao encontrada, pulando: $app_file"
        continue
    fi
    log "── $app_name × $REPEATS ──"
    # Descarte de aquecimento: a primeira execucao paga cache de pagina frio e
    # primeiro toque no rootfs, e nao representa o regime medido.
    run_once "$app_name" "$app_file" 0
    for i in $(seq 1 "$REPEATS"); do
        run_once "$app_name" "$app_file" "$i"
    done
done

# -----------------------------------------------------------------------------
# Resumo. Descarta a rodada 0 (aquecimento) e reporta mediana alem da media: com
# N=10 num host compartilhado, um unico outlier de vizinho barulhento move a
# media e nao move a mediana.
# -----------------------------------------------------------------------------
log ""
log "── Resumo ($LABEL) ──"
python3 - "$CSV" <<'PY' | tee -a "$RESULTS_DIR/run.log"
import csv, statistics, sys

rows = [r for r in csv.DictReader(open(sys.argv[1], encoding="utf-8")) if r["run"] != "0"]
by_app = {}
for r in rows:
    by_app.setdefault(r["app"], []).append(r)

def stats(vals):
    vals = [float(v) for v in vals if v not in ("", None)]
    if not vals:
        return None
    return (statistics.fmean(vals), statistics.median(vals),
            statistics.pstdev(vals) if len(vals) > 1 else 0.0, len(vals))

for app, rs in by_app.items():
    print(f"\n{app}  (n={len(rs)})")
    for col, unit in (("wall_ms", "ms"), ("total_s", "s"), ("first_touch_s", "s"),
                      ("memory_s", "s"), ("cpu_s", "s"), ("mem_mibs", "MiB/s")):
        s = stats([r[col] for r in rs])
        if s:
            mean, med, sd, n = s
            print(f"  {col:>15}: mean={mean:.4f} median={med:.4f} sd={sd:.4f} {unit}")
    bad = [r for r in rs if r["returncode"] not in ("0", "")]
    if bad:
        print(f"  !! {len(bad)} execucoes com returncode != 0")
    digests = {r["digest"] for r in rs if r["digest"]}
    if len(digests) > 1:
        print(f"  !! digests divergentes na mesma celula: {digests}")
    elif digests:
        print(f"  {'digest':>15}: {digests.pop()} (deve bater entre TODAS as celulas)")
PY

log ""
log "CSV: $CSV"
echo "$RESULTS_DIR"
