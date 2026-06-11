#!/usr/bin/env bash
# Testes do PLANO DE EXECUCAO (CVM3) enviando bundles diretamente ao executor.
#
# Este harness nao depende do builder, do IPFS nem do smart contract: ele
# reproduz fielmente o ambiente de execucao (workspace/run.sh dentro da microVM
# Firecracker sem rede) empacotando a aplicacao em modo "script" exatamente como
# o run_from_cids.py faz. Isso permite coletar evidencias dos testes T1
# (exfiltracao de rede), T1b (contencao de filesystem) e a app benigna (corretude
# e latencia) de forma automatizada e reproduzivel.
#
# Uso:
#   bash run_execution_plane_tests.sh                 # Ambiente B (executor :5000)
#   EXECUTOR_PORT=4000 bash run_execution_plane_tests.sh   # Ambiente A (baseline)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ASSETS="$REPO/assets"
EXECUTOR_PORT="${EXECUTOR_PORT:-5000}"
EXECUTOR="http://127.0.0.1:${EXECUTOR_PORT}/execute"
DATASET="${DATASET:-$ASSETS/data/dataset_synthetic.csv}"
RESULTS_DIR="$ASSETS/test-results/exec-plane-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$RESULTS_DIR/run.log"; }

# Empacota uma aplicacao Python no mesmo formato do executor (workspace/run.sh
# em modo script) e retorna o caminho do bundle.
make_script_bundle() {
    local app_file="$1" bundle_out="$2"
    local stage; stage="$(mktemp -d)"
    mkdir -p "$stage/workspace/code" "$stage/workspace/data"
    cp "$app_file" "$stage/workspace/code/application.py"
    cp "$DATASET" "$stage/workspace/data/dataset.csv"
    cat > "$stage/workspace/run.sh" <<'RUNSH'
#!/bin/bash
set -euo pipefail
cd /tmp/exec/workspace
if python3 code/application.py --dataset data/dataset.csv; then exit 0; fi
if python3 code/application.py --dataset data/dataset.csv --output result.json; then exit 0; fi
if python3 code/application.py data/dataset.csv; then exit 0; fi
python3 code/application.py
RUNSH
    chmod +x "$stage/workspace/run.sh"
    tar -C "$stage" -czf "$bundle_out" workspace
    rm -rf "$stage"
}

# Executa um bundle e mede a latencia de parede (boot + run + teardown).
run_case() {
    local name="$1" app_file="$2"
    log "── $name ($(basename "$app_file")) ──"
    local bundle="$RESULTS_DIR/${name}.bundle.tar.gz"
    local resp="$RESULTS_DIR/${name}.response.json"
    make_script_bundle "$app_file" "$bundle"

    local t0 t1 elapsed http
    t0=$(date +%s%3N)
    http=$(curl -s --max-time 300 -X POST "$EXECUTOR" \
        -H "Content-Type: application/gzip" \
        --data-binary @"$bundle" -o "$resp" -w "%{http_code}")
    t1=$(date +%s%3N)
    elapsed=$((t1 - t0))
    echo "$elapsed" > "$RESULTS_DIR/${name}.latency_ms.txt"
    log "  HTTP $http | wall=${elapsed}ms | response -> $(basename "$resp")"

    # Extrai stdout para inspecao rapida.
    python3 - "$resp" "$RESULTS_DIR/${name}.stdout.txt" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception as e:
    open(sys.argv[2], "w").write(f"[harness] could not parse response: {e}")
    sys.exit(0)
open(sys.argv[2], "w", encoding="utf-8").write(d.get("stdout", "") or "")
print("  returncode:", d.get("returncode"))
PY
    rm -f "$bundle"
}

log "Executor alvo: $EXECUTOR"
log "Dataset: $DATASET ($(wc -c < "$DATASET") bytes)"
log "Resultados: $RESULTS_DIR"
log ""

run_case "t1_network_exfil"  "$ASSETS/apps/t1_network_exfil.py"
run_case "t1b_fs_escape"     "$ASSETS/apps/t1b_fs_escape.py"
run_case "benign_stats"      "$ASSETS/apps/benign_stats.py"

log ""
log "── Resumo das evidencias ──"
echo "── T1 (network) ──"            | tee -a "$RESULTS_DIR/run.log"
grep -E "OVERALL|interfaces|SUMMARY" "$RESULTS_DIR/t1_network_exfil.stdout.txt" | tee -a "$RESULTS_DIR/run.log" || true
echo "── T1b (filesystem) ──"        | tee -a "$RESULTS_DIR/run.log"
grep -E "OVERALL|NO-SECRETS|SECRET-FOUND|writable" "$RESULTS_DIR/t1b_fs_escape.stdout.txt" | tee -a "$RESULTS_DIR/run.log" || true
echo "── benign (corretude) ──"      | tee -a "$RESULTS_DIR/run.log"
grep -E "processed|RESULT" "$RESULTS_DIR/benign_stats.stdout.txt" | tee -a "$RESULTS_DIR/run.log" || true

log ""
log "Latencias (ms): T1=$(cat "$RESULTS_DIR/t1_network_exfil.latency_ms.txt") T1b=$(cat "$RESULTS_DIR/t1b_fs_escape.latency_ms.txt") benign=$(cat "$RESULTS_DIR/benign_stats.latency_ms.txt")"
echo "$RESULTS_DIR"
