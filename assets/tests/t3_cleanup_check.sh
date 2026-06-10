#!/usr/bin/env bash
# T3 — Verifica que nenhum artefato efêmero persiste na CVM3 após execução.
# Executar após pelo menos uma execução via "Run From CIDs".

set -euo pipefail

PASS=0
FAIL=0

check_absent() {
    local label="$1"
    local cmd="$2"
    local result
    result=$(docker exec dnat-executor sh -lc "$cmd" 2>/dev/null || true)
    if [ -z "$result" ]; then
        echo "  [PASS] $label — nenhum artefato encontrado"
        PASS=$((PASS + 1))
    else
        echo "  [FAIL] $label — artefatos presentes:"
        echo "$result" | sed 's/^/    /'
        FAIL=$((FAIL + 1))
    fi
}

echo "=== T3: Ephemeral Cleanup Check (CVM3 / dnat-executor) ==="
echo ""

check_absent "firecracker.socket" \
    "find /tmp -maxdepth 3 -name firecracker.socket"

check_absent "rootfs-overlay.ext4" \
    "find /tmp -maxdepth 3 -name rootfs-overlay.ext4"

check_absent "input.ext4" \
    "find /tmp -maxdepth 3 -name input.ext4"

check_absent "output.ext4" \
    "find /tmp -maxdepth 3 -name output.ext4"

check_absent "application.ext4 (descriptografado)" \
    "find /tmp -maxdepth 3 -name application.ext4"

check_absent "mounts residuais" \
    "mount | grep -E 'result-mount|input-mount|output-mount' || true"

check_absent "dataset no executor" \
    "find /tmp -maxdepth 3 -name '*.csv' -o -name 'dataset*'"

echo ""
echo "=== Resultado: $PASS passou(aram), $FAIL falhou(aram) ==="

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
