#!/usr/bin/env bash
set -euo pipefail

# Entrypoint do Ambiente A (baseline centralizado do TCC).
# Sobe IPFS, Hardhat, deploy do contrato, builder API, executor API e api-server.js
# no mesmo container, mesmo usuario, mesmo namespace de mount/rede.
# Tudo se comunica via 127.0.0.1.

IPFS_PATH="${IPFS_PATH:-/data/ipfs}"
RPC_URL="${RPC_URL:-http://127.0.0.1:8545}"
IPFS_API_URL="${IPFS_API_URL:-http://127.0.0.1:5001}"
WEB_PORT="${WEB_PORT:-3001}"
EXECUTOR_URL="${EXECUTOR_URL:-http://127.0.0.1:5000}"
BUILDER_URL="${BUILDER_URL:-http://127.0.0.1:5100}"
PRIVATE_KEY="${PRIVATE_KEY:-0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80}"
ASSET_ENCRYPTION_KEY="${ASSET_ENCRYPTION_KEY:-dnat-dev-asset-key}"

PIDS=()

cleanup() {
  local exit_code=$?
  # Termina em ordem inversa, ignorando processos ja mortos.
  for ((i = ${#PIDS[@]} - 1; i >= 0; i -= 1)); do
    local pid="${PIDS[$i]}"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
  exit "${exit_code}"
}
trap cleanup EXIT INT TERM

wait_for_http() {
  local name="$1" method="$2" url="$3" data="${4:-}" attempts="${5:-60}"
  for ((i = 1; i <= attempts; i += 1)); do
    if [[ -n "${data}" ]]; then
      if curl --silent --show-error --fail -X "${method}" -H "Content-Type: application/json" --data "${data}" "${url}" >/dev/null; then
        echo "${name} ready at ${url}"
        return 0
      fi
    else
      if curl --silent --show-error --fail -X "${method}" "${url}" >/dev/null; then
        echo "${name} ready at ${url}"
        return 0
      fi
    fi
    sleep 1
  done
  echo "Timed out waiting for ${name} at ${url}" >&2
  return 1
}

mkdir -p "${IPFS_PATH}" /app/smart-contract/executions /var/dnat/wheel-cache

# === IPFS ===
if [[ ! -f "${IPFS_PATH}/config" ]]; then
  echo "[baseline] Initializing IPFS repository at ${IPFS_PATH}"
  ipfs init --profile=server
fi

echo "[baseline] Starting IPFS daemon"
ipfs daemon --migrate=true &
PIDS+=($!)
wait_for_http "IPFS API" "POST" "${IPFS_API_URL%/}/api/v0/version"

# === Hardhat node + deploy ===
echo "[baseline] Starting Hardhat node"
( cd /app/smart-contract && npx hardhat node --hostname 0.0.0.0 ) &
PIDS+=($!)
wait_for_http \
  "Hardhat RPC" "POST" "${RPC_URL}" \
  '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}'

echo "[baseline] Deploying smart contract"
( cd /app/smart-contract && RPC_URL="${RPC_URL}" npx hardhat run scripts/deploy.js --network localhost )

# === Builder API (porta 5100) ===
# start-builder.sh ja foi patchado para ROOT=/opt/dnat-builder no Dockerfile.baseline.
echo "[baseline] Starting builder API on 5100"
( cd /opt/dnat-builder && WHEEL_CACHE_SOURCE_DIR="${WHEEL_CACHE_SOURCE_DIR:-/var/dnat/wheel-cache}" bash /opt/dnat-builder/start-builder.sh ) &
PIDS+=($!)
wait_for_http "Builder API" "GET" "${BUILDER_URL%/}/health"

# === Executor API (porta 5000) ===
echo "[baseline] Starting executor API on 5000"
( cd /opt/dnat-executor && bash /opt/dnat-executor/start-executor.sh ) &
PIDS+=($!)
wait_for_http "Executor API" "GET" "${EXECUTOR_URL%/}/health"

# === Control plane (api-server.js) por ultimo, depende de tudo acima ===
echo "[baseline] Starting DNAT control plane on port ${WEB_PORT}"
cd /app/smart-contract
RPC_URL="${RPC_URL}" \
IPFS_API_URL="${IPFS_API_URL}" \
WEB_PORT="${WEB_PORT}" \
EXECUTOR_URL="${EXECUTOR_URL}" \
BUILDER_URL="${BUILDER_URL}" \
PRIVATE_KEY="${PRIVATE_KEY}" \
ASSET_ENCRYPTION_KEY="${ASSET_ENCRYPTION_KEY}" \
node scripts/api-server.js &
WEB_PID=$!
PIDS+=("${WEB_PID}")

# Bloqueia no processo principal (control plane); se ele morrer, o trap cleanup leva os outros junto.
wait "${WEB_PID}"
