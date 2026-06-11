#!/usr/bin/env bash
# Semeia o pacote malicioso no cache de wheels da CVM2 (dnat-builder), para que
# uma aplicacao que declare a dependencia "malicious-pkg" consiga resolve-la sem
# que o pacote exista no PyPI. Isto reproduz, de forma controlada e reproduzivel,
# um cenario de supply chain comprometida na avaliacao do artigo.
#
# Modo de dependencia (escolha um):
#   SDIST  -> apenas o sdist e semeado; o build microVM RECONSTROI o pacote
#             (setup.py roda) => payload de build-time (CVM2).
#   WHEEL  -> o wheel pronto e semeado; instala sem rodar setup.py => util para
#             isolar o payload de import-time (CVM3).
#
# Uso:
#   bash seed_cache.sh            # default: SDIST (build-time)
#   MODE=WHEEL bash seed_cache.sh # apenas wheel (import-time)
#   BUILDER_CONTAINER=dnat-baseline bash seed_cache.sh   # para o Ambiente A
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${MODE:-SDIST}"
BUILDER_CONTAINER="${BUILDER_CONTAINER:-dnat-builder}"
CACHE_DIR="/var/dnat/wheel-cache"

if [ ! -d dist ] || [ -z "$(ls -A dist 2>/dev/null || true)" ]; then
    echo "[seed_cache] dist/ vazio; gerando artefatos..."
    bash build_dist.sh
fi

if ! docker ps --format '{{.Names}}' | grep -q "^${BUILDER_CONTAINER}$"; then
    echo "[seed_cache] ERRO: container '${BUILDER_CONTAINER}' nao esta rodando." >&2
    echo "[seed_cache] suba o builder (docker compose -f docker/builder-vm.compose.yaml up -d)." >&2
    exit 1
fi

docker exec "$BUILDER_CONTAINER" mkdir -p "$CACHE_DIR"

if [ "$MODE" = "WHEEL" ]; then
    ARTIFACT="$(find dist -name '*.whl' | head -1)"
else
    ARTIFACT="$(find dist -name '*.tar.gz' | head -1)"
fi

[ -n "$ARTIFACT" ] || { echo "[seed_cache] nenhum artefato $MODE em dist/" >&2; exit 1; }

docker cp "$ARTIFACT" "${BUILDER_CONTAINER}:${CACHE_DIR}/$(basename "$ARTIFACT")"
echo "[seed_cache] semeado ($MODE): $(basename "$ARTIFACT") -> ${BUILDER_CONTAINER}:${CACHE_DIR}"
echo "[seed_cache] conteudo atual do cache:"
docker exec "$BUILDER_CONTAINER" sh -lc "ls -l ${CACHE_DIR}"
