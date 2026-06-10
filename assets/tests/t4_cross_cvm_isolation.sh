#!/usr/bin/env bash
# T4 — Verifica que a CVM3 (executor) não consegue alcançar ativos da CVM1 e CVM2.
# Simula comprometimento do executor tentando escalar para outros planos.

set -euo pipefail

PASS=0
FAIL=0

check_blocked() {
    local label="$1"
    local cmd="$2"
    local result
    result=$(docker exec dnat-executor sh -lc "$cmd" 2>&1 || true)
    # Considera bloqueado se retornou erro de rede ou não encontrou serviço
    if echo "$result" | grep -qiE "refused|unreachable|not resolve|network|failed|error|curl.*[45][0-9][0-9]|timed out"; then
        echo "  [PASS] $label — acesso bloqueado"
        echo "         resposta: $(echo "$result" | head -1)"
        PASS=$((PASS + 1))
    else
        echo "  [FAIL] $label — acesso obtido:"
        echo "$result" | head -5 | sed 's/^/    /'
        FAIL=$((FAIL + 1))
    fi
}

check_reachable() {
    local label="$1"
    local cmd="$2"
    local result
    result=$(docker exec dnat-executor sh -lc "$cmd" 2>&1 || true)
    if echo "$result" | grep -qiE "refused|unreachable|not resolve|network|failed|error|timed out"; then
        echo "  [FAIL] $label — deveria ser alcançável mas não está"
        FAIL=$((FAIL + 1))
    else
        echo "  [PASS] $label — alcançável conforme esperado"
        PASS=$((PASS + 1))
    fi
}

echo "=== T4: Cross-CVM Privilege Escalation Check ==="
echo ""
echo "--- Acessos que DEVEM ser bloqueados (CVM3 -> CVM1/CVM2) ---"

check_blocked "CVM1 API frontend (porta 3001)" \
    "curl -sf --max-time 3 http://dnat-client:3001/api/health"

check_blocked "CVM1 IPFS API (porta 5001)" \
    "curl -sf --max-time 3 http://dnat-client:5001/api/v0/id"

check_blocked "CVM2 builder API (porta 5100)" \
    "curl -sf --max-time 3 http://dnat-builder:5100/health"

check_blocked "CVM1 hardhat RPC (porta 8545)" \
    "curl -sf --max-time 3 -X POST -H 'Content-Type: application/json' \
     -d '{\"jsonrpc\":\"2.0\",\"method\":\"eth_blockNumber\",\"params\":[],\"id\":1}' \
     http://dnat-client:8545"

echo ""
echo "--- Variáveis sensíveis da CVM1 acessíveis na CVM3 ---"

sensitive=$(docker exec dnat-executor sh -lc \
    'echo "ASSET_ENCRYPTION_KEY=${ASSET_ENCRYPTION_KEY:-[not set]}"' 2>/dev/null || true)
if echo "$sensitive" | grep -q "\[not set\]"; then
    echo "  [PASS] ASSET_ENCRYPTION_KEY — não presente na CVM3"
    PASS=$((PASS + 1))
else
    echo "  [FAIL] ASSET_ENCRYPTION_KEY — VAZOU para a CVM3: $sensitive"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "=== Resultado: $PASS passou(aram), $FAIL falhou(aram) ==="

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
