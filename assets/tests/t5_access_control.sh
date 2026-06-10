#!/usr/bin/env bash
# T5 — Verifica que a API rejeita execução sem acesso comprado no smart contract.
# Passa CIDs válidos de dataset e aplicação, mas sem ter chamado purchaseAccess().
# Requer: ambiente B rodando (dnat-client na porta 3001) e pelo menos um
#         dataset e aplicação registrados. Ajuste os CIDs abaixo.

set -euo pipefail

API="http://127.0.0.1:3001"
PASS=0
FAIL=0

# Substitua pelos CIDs reais de um dataset e aplicação registrados
# mas para os quais o usuário padrão NÃO comprou acesso.
DATASET_CID="${DATASET_CID:-}"
APP_CID="${APP_CID:-}"

if [ -z "$DATASET_CID" ] || [ -z "$APP_CID" ]; then
    echo "[T5] Uso: DATASET_CID=<cid> APP_CID=<cid> bash t5_access_control.sh"
    echo "[T5] Obtenha os CIDs na interface em $API após registrar dataset e aplicação"
    echo "[T5] sem comprar acesso para o endereço default."
    exit 1
fi

echo "=== T5: Access Control Without purchaseAccess ==="
echo "    Dataset CID : $DATASET_CID"
echo "    App CID     : $APP_CID"
echo ""

response=$(curl -sf --max-time 10 \
    -X POST "$API/api/run-from-cids" \
    -H "Content-Type: application/json" \
    -d "{\"datasetCid\":\"$DATASET_CID\",\"applicationCid\":\"$APP_CID\"}" \
    2>&1 || true)

echo "Resposta da API: $response"
echo ""

if echo "$response" | grep -qiE "access denied|unauthorized|not authorized|no access|forbidden|403|sem acesso"; then
    echo "  [PASS] execução bloqueada pelo access control"
    PASS=$((PASS + 1))
elif echo "$response" | grep -qiE "refused|unreachable|error"; then
    echo "  [INFO] API inacessível — verifique se o ambiente B está rodando"
    exit 2
else
    echo "  [FAIL] execução prosseguiu sem acesso comprado"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "=== Resultado: $PASS passou(aram), $FAIL falhou(aram) ==="

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
