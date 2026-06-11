#!/usr/bin/env bash
# Testes do PLANO DE BUILD (CVM2) enviando bundles diretamente ao builder.
#
# Reproduz o contrato de build do control plane (api-server.js -> /build):
# um tar.gz com source/application.py + manifest.json; a resposta e um tar.gz
# com application.ext4. Mede latencia de build (com/sem dependencias) e tamanho
# do artefato, e suporta o teste T2 (dependencia maliciosa).
#
# Uso:
#   bash run_build_plane_tests.sh                       # builder :5100 (Ambiente B)
#   BUILDER_PORT=4100 bash run_build_plane_tests.sh     # baseline (Ambiente A)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ASSETS="$REPO/assets"
BUILDER_PORT="${BUILDER_PORT:-5100}"
BUILDER="http://127.0.0.1:${BUILDER_PORT}/build"
RESULTS_DIR="$ASSETS/test-results/build-plane-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$RESULTS_DIR/run.log"; }

# Monta o bundle de request e dispara o build. Args: nome app_file deps
build_case() {
    local name="$1" app_file="$2" deps_json="$3"
    log "── build '$name' (deps=$deps_json) ──"
    local stage; stage="$(mktemp -d)"
    mkdir -p "$stage/source"
    cp "$app_file" "$stage/source/application.py"
    python3 - "$stage/manifest.json" "$name" "$deps_json" <<'PY'
import json, sys
path, name, deps = sys.argv[1], sys.argv[2], sys.argv[3]
json.dump({"name": name, "description": name, "framework": "python",
           "dependencies": json.loads(deps)}, open(path, "w"))
PY
    local req="$RESULTS_DIR/${name}.request.tar.gz"
    local resp="$RESULTS_DIR/${name}.response.tar.gz"
    tar -C "$stage" -czf "$req" source manifest.json
    rm -rf "$stage"

    local t0 t1 http
    t0=$(date +%s%3N)
    http=$(curl -s --max-time 2400 -X POST "$BUILDER" \
        -H "Content-Type: application/gzip" \
        --data-binary @"$req" -o "$resp" -w "%{http_code}")
    t1=$(date +%s%3N)
    echo "$((t1-t0))" > "$RESULTS_DIR/${name}.latency_ms.txt"

    local size="n/a"
    if [ "$http" = "200" ]; then
        # Extrai application.ext4 e mede o tamanho.
        local ex="$RESULTS_DIR/${name}.extract"; mkdir -p "$ex"
        if tar -C "$ex" -xzf "$resp" 2>/dev/null && [ -f "$ex/application.ext4" ]; then
            size=$(stat -c%s "$ex/application.ext4")
            cp "$ex/build-result.json" "$RESULTS_DIR/${name}.build-result.json" 2>/dev/null || true
        fi
        rm -rf "$ex"
    else
        # Erro: salva o corpo JSON para diagnostico.
        cp "$resp" "$RESULTS_DIR/${name}.error.json" 2>/dev/null || true
    fi
    log "  HTTP $http | wall=$(cat "$RESULTS_DIR/${name}.latency_ms.txt")ms | artifact=${size} bytes"
    rm -f "$req"
}

log "Builder alvo: $BUILDER"
log "Resultados: $RESULTS_DIR"

# Caso 1: build SEM dependencias (baseline de latencia/tamanho).
build_case "benign_nodeps" "$ASSETS/apps/benign_stats.py" "[]"

# Caso 2: build COM dependencias (custo da resolucao/instalacao + rede).
#   Ajuste a lista conforme desejado. Use deps leves para um teste rapido.
build_case "benign_deps" "$ASSETS/apps/benign_stats.py" "[\"requests\"]"

# Caso 3 (T2): dependencia maliciosa. Requer o pacote semeado no cache:
#   bash assets/malicious_wheel/build_dist.sh && bash assets/malicious_wheel/seed_cache.sh
if [ "${RUN_T2:-0}" = "1" ]; then
    build_case "t2_malicious" "$ASSETS/apps/t2_malicious_dep.py" "[\"malicious-pkg\"]"
    log "── T2 payload markers no log do builder ──"
    docker logs dnat-builder 2>&1 | grep -iE "T2-MALICIOUS-PKG|malicious_pkg" | tail -30 | tee -a "$RESULTS_DIR/t2_builder_log.txt" || true
fi

log ""
log "── Resumo ──"
for n in benign_nodeps benign_deps t2_malicious; do
    [ -f "$RESULTS_DIR/${n}.latency_ms.txt" ] && log "  $n: $(cat "$RESULTS_DIR/${n}.latency_ms.txt")ms"
done
echo "$RESULTS_DIR"
