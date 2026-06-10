#!/usr/bin/env bash
# Orquestrador completo dos testes T1-T5 para o paper DNAT.
# Executa nos dois ambientes (B=DNAT compartimentado, A=baseline centralizado)
# e registra evidências para a seção 5.1 (Security Evaluation).
#
# Pré-requisitos: containers rodando (ver RUN_COMPOSE.md)
# Uso: bash run_all_tests.sh

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ASSETS="$REPO/assets"
RESULTS_DIR="$ASSETS/test-results/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

API_B="http://127.0.0.1:3001"   # Ambiente B (DNAT)
API_A="http://127.0.0.1:4001"   # Ambiente A (baseline)

PASS=0
FAIL=0
SKIP=0

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$RESULTS_DIR/run.log"; }
pass() { log "  [PASS] $*"; PASS=$((PASS+1)); }
fail() { log "  [FAIL] $*"; FAIL=$((FAIL+1)); }
skip() { log "  [SKIP] $*"; SKIP=$((SKIP+1)); }
section() { log ""; log "════════════════════════════════════════"; log "  $*"; log "════════════════════════════════════════"; }

# ──────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────

wait_api() {
    local url="$1" label="$2" retries=15
    for i in $(seq 1 $retries); do
        if curl -sf --max-time 3 "$url/api/health" > /dev/null 2>&1; then
            log "$label está respondendo."
            return 0
        fi
        sleep 2
    done
    log "ERRO: $label não respondeu em $((retries*2))s"
    return 1
}

register_dataset() {
    local api="$1"
    curl -sf --max-time 20 -X POST "$api/api/register-dataset" \
        -F "file=@$ASSETS/data/teste1.csv" \
        -F "name=dataset-security-eval" \
        -F "description=dataset para testes de segurança"
}

register_app() {
    local api="$1" app_file="$2" name="$3" deps="${4:-}"
    curl -sf --max-time 180 -X POST "$api/api/register-application" \
        -F "file=@$app_file" \
        -F "name=$name" \
        -F "description=$name" \
        -F "dependencies=$deps"
}

purchase() {
    local api="$1" ds_id="$2" app_id="$3"
    curl -s --max-time 15 -X POST "$api/api/purchase-access" \
        -H "Content-Type: application/json" \
        -d "{\"datasetId\":\"$ds_id\",\"applicationId\":\"$app_id\"}"
}

execute() {
    local api="$1" ds_id="$2" app_id="$3"
    curl -s --max-time 300 -X POST "$api/api/run-from-cids" \
        -H "Content-Type: application/json" \
        -d "{\"datasetId\":\"$ds_id\",\"applicationId\":\"$app_id\"}"
}

# ──────────────────────────────────────────
# Sanidade
# ──────────────────────────────────────────
section "Verificando ambientes"
wait_api "$API_B" "Ambiente B (DNAT)"
wait_api "$API_A" "Ambiente A (baseline)"

# ──────────────────────────────────────────
# T1 — Network Exfiltration
# ──────────────────────────────────────────
section "T1: Network Exfiltration via socket"
log "Registrando dataset e aplicação em AMBOS os ambientes..."

# --- Ambiente B ---
log "[B] Registrando dataset..."
DS_B=$(register_dataset "$API_B")
DS_ID_B=$(echo "$DS_B" | python3 -c "import sys,json; print(json.load(sys.stdin)['assetId'])")
log "[B] Dataset assetId=$DS_ID_B"

log "[B] Registrando aplicação T1 (sem dependências externas)..."
APP_B=$(register_app "$API_B" "$ASSETS/apps/t1_network_exfil.py" "t1-network-exfil")
APP_ID_B=$(echo "$APP_B" | python3 -c "import sys,json; print(json.load(sys.stdin)['assetId'])")
log "[B] App assetId=$APP_ID_B"

log "[B] Comprando acesso..."
purchase "$API_B" "$DS_ID_B" "$APP_ID_B" > /dev/null

log "[B] Executando T1 no DNAT..."
EXEC_B=$(execute "$API_B" "$DS_ID_B" "$APP_ID_B")
echo "$EXEC_B" > "$RESULTS_DIR/t1_dnat_execution.json"
STDOUT_B=$(echo "$EXEC_B" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('stdout',''))" 2>/dev/null || true)
log "[B] stdout: $STDOUT_B"

# --- Ambiente A ---
log "[A] Registrando dataset..."
DS_A=$(register_dataset "$API_A")
DS_ID_A=$(echo "$DS_A" | python3 -c "import sys,json; print(json.load(sys.stdin)['assetId'])")

log "[A] Registrando aplicação T1..."
APP_A=$(register_app "$API_A" "$ASSETS/apps/t1_network_exfil.py" "t1-network-exfil")
APP_ID_A=$(echo "$APP_A" | python3 -c "import sys,json; print(json.load(sys.stdin)['assetId'])")

log "[A] Comprando acesso..."
purchase "$API_A" "$DS_ID_A" "$APP_ID_A" > /dev/null

log "[A] Executando T1 no baseline..."
EXEC_A=$(execute "$API_A" "$DS_ID_A" "$APP_ID_A")
echo "$EXEC_A" > "$RESULTS_DIR/t1_baseline_execution.json"
STDOUT_A=$(echo "$EXEC_A" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('stdout',''))" 2>/dev/null || true)
log "[A] stdout: $STDOUT_A"

# --- Avaliação T1 ---
log ""
log "--- Evidências T1 ---"
DNAT_BLOCKED=$(echo "$STDOUT_B" | grep -c "EXFILTRATION FAILED" || true)
BASELINE_BLOCKED=$(echo "$STDOUT_A" | grep -c "EXFILTRATION FAILED" || true)
BASELINE_SUCCEEDED=$(echo "$STDOUT_A" | grep -c "EXFILTRATION SUCCEEDED" || true)

echo "DNAT stdout:" >> "$RESULTS_DIR/t1_evidence.txt"
echo "$STDOUT_B" >> "$RESULTS_DIR/t1_evidence.txt"
echo "" >> "$RESULTS_DIR/t1_evidence.txt"
echo "Baseline stdout:" >> "$RESULTS_DIR/t1_evidence.txt"
echo "$STDOUT_A" >> "$RESULTS_DIR/t1_evidence.txt"

if [ "$DNAT_BLOCKED" -gt 0 ]; then
    pass "T1 DNAT: exfiltração bloqueada pela ausência de rede na microVM"
else
    fail "T1 DNAT: exfiltração NÃO foi bloqueada — revisar configuração do kernel"
fi

if [ "$BASELINE_SUCCEEDED" -gt 0 ]; then
    pass "T1 Baseline: exfiltração SUCEDEU — confirma vulnerabilidade no modelo centralizado"
elif [ "$BASELINE_BLOCKED" -gt 0 ]; then
    log "  [INFO] T1 Baseline: também bloqueou — host pode ter firewall. Verificar $RESULTS_DIR/t1_baseline_execution.json"
    SKIP=$((SKIP+1))
fi

# ──────────────────────────────────────────
# T3 — Ephemeral Cleanup (roda após T1 que já fez uma execução)
# ──────────────────────────────────────────
section "T3: Ephemeral Cleanup Check (CVM3)"
log "Verificando artefatos remanescentes no dnat-executor após execução T1..."

LEFTOVER=$(docker exec dnat-executor sh -lc \
    'find /tmp -maxdepth 3 \( -name "firecracker.socket" -o -name "rootfs-overlay.ext4" -o -name "input.ext4" -o -name "output.ext4" -o -name "application.ext4" \) 2>/dev/null' \
    2>/dev/null || true)
MOUNTS=$(docker exec dnat-executor sh -lc \
    'mount 2>/dev/null | grep -E "result-mount|input-mount|output-mount" || true' \
    2>/dev/null || true)
DATASET=$(docker exec dnat-executor sh -lc \
    'find /tmp -maxdepth 3 -name "*.csv" 2>/dev/null' \
    2>/dev/null || true)

echo "Artefatos encontrados: '$LEFTOVER'" >> "$RESULTS_DIR/t3_evidence.txt"
echo "Mounts residuais: '$MOUNTS'" >> "$RESULTS_DIR/t3_evidence.txt"
echo "Datasets residuais: '$DATASET'" >> "$RESULTS_DIR/t3_evidence.txt"

[ -z "$LEFTOVER" ] && pass "T3: nenhum disco/socket efêmero remanescente" || fail "T3: artefatos não limpos: $LEFTOVER"
[ -z "$MOUNTS"   ] && pass "T3: nenhum mount residual"                    || fail "T3: mounts não desmontados: $MOUNTS"
[ -z "$DATASET"  ] && pass "T3: dataset não persiste na CVM3"              || fail "T3: dataset encontrado em /tmp: $DATASET"

# ──────────────────────────────────────────
# T4 — Cross-CVM Isolation
# ──────────────────────────────────────────
section "T4: Cross-CVM Privilege Escalation"
log "Testando o que a CVM3 (executor) consegue alcançar..."

T4_RESULTS="$RESULTS_DIR/t4_evidence.txt"
echo "Cross-CVM reachability from dnat-executor:" > "$T4_RESULTS"

check_cross() {
    local label="$1" cmd="$2"
    local out
    out=$(docker exec dnat-executor sh -lc "$cmd" 2>&1 || true)
    echo "$label: $out" >> "$T4_RESULTS"
    if echo "$out" | grep -qiE "refused|unreachable|could not resolve|network|failed|timed out|curl.*(7|28|6)"; then
        pass "T4: $label — bloqueado"
    else
        fail "T4: $label — ACESSÍVEL: $(echo "$out" | head -1)"
    fi
}

check_cross "CVM1 API (3001)"     "curl -sf --max-time 3 http://dnat-client:3001/api/health 2>&1 || true"
check_cross "CVM1 IPFS (5001)"    "curl -sf --max-time 3 http://dnat-client:5001/api/v0/id 2>&1 || true"
check_cross "CVM2 builder (5100)" "curl -sf --max-time 3 http://dnat-builder:5100/health 2>&1 || true"
check_cross "Hardhat RPC (8545)"  "curl -sf --max-time 3 -X POST -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"eth_blockNumber\",\"params\":[],\"id\":1}' http://dnat-client:8545 2>&1 || true"

# Chave de criptografia
KEY_LEAKED=$(docker exec dnat-executor sh -lc 'echo "${ASSET_ENCRYPTION_KEY:-__not_set__}"' 2>/dev/null || true)
echo "ASSET_ENCRYPTION_KEY in CVM3: $KEY_LEAKED" >> "$T4_RESULTS"
if echo "$KEY_LEAKED" | grep -q "__not_set__"; then
    pass "T4: ASSET_ENCRYPTION_KEY não vazou para a CVM3"
else
    fail "T4: ASSET_ENCRYPTION_KEY PRESENTE na CVM3: $KEY_LEAKED"
fi

# ──────────────────────────────────────────
# T5 — Access Control sem purchaseAccess
# ──────────────────────────────────────────
section "T5: Access Control — execução sem comprar acesso"
log "Tentando executar com IDs válidos mas sem acesso comprado..."

# Registrar novos assets sem comprar acesso
log "Registrando dataset e app novos (sem purchaseAccess)..."
DS_T5=$(register_dataset "$API_B")
DS_ID_T5=$(echo "$DS_T5" | python3 -c "import sys,json; print(json.load(sys.stdin)['assetId'])")
APP_T5=$(register_app "$API_B" "$ASSETS/apps/ap1.py" "t5-no-access-app")
APP_ID_T5=$(echo "$APP_T5" | python3 -c "import sys,json; print(json.load(sys.stdin)['assetId'])")
log "Dataset=$DS_ID_T5 App=$APP_ID_T5 (sem purchaseAccess)"

EXEC_T5=$(curl -s --max-time 30 -X POST "$API_B/api/run-from-cids" \
    -H "Content-Type: application/json" \
    -d "{\"datasetId\":\"$DS_ID_T5\",\"applicationId\":\"$APP_ID_T5\"}" 2>&1 || true)
echo "$EXEC_T5" > "$RESULTS_DIR/t5_evidence.json"
log "Resposta: $EXEC_T5"

if echo "$EXEC_T5" | grep -qiE "access denied|denied|Access denied"; then
    pass "T5: execução bloqueada pelo smart contract — acesso negado sem purchaseAccess"
else
    fail "T5: execução prosseguiu sem acesso — controle falhou"
fi

# ──────────────────────────────────────────
# Sumário
# ──────────────────────────────────────────
section "SUMÁRIO FINAL"
TOTAL=$((PASS+FAIL+SKIP))
log "Total: $TOTAL | Passou: $PASS | Falhou: $FAIL | Skip: $SKIP"
log "Evidências salvas em: $RESULTS_DIR/"
ls "$RESULTS_DIR/"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
