#!/usr/bin/env bash
set -euo pipefail

IPFS_PATH="${IPFS_PATH:-/data/ipfs}"
RPC_URL="${RPC_URL:-http://127.0.0.1:8545}"
IPFS_API_URL="${IPFS_API_URL:-http://127.0.0.1:5001}"
WEB_PORT="${WEB_PORT:-3001}"
EXECUTOR_URL="${EXECUTOR_URL:-http://dnat-executor:5000}"
BUILDER_URL="${BUILDER_URL:-http://dnat-builder:5100}"
PRIVATE_KEY="${PRIVATE_KEY:-0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80}"
ASSET_ENCRYPTION_KEY="${ASSET_ENCRYPTION_KEY:-dnat-dev-asset-key}"

cleanup() {
  local exit_code=$?

  if [[ -n "${WEB_PID:-}" ]] && kill -0 "${WEB_PID}" 2>/dev/null; then
    kill "${WEB_PID}" 2>/dev/null || true
  fi
  if [[ -n "${HARDHAT_PID:-}" ]] && kill -0 "${HARDHAT_PID}" 2>/dev/null; then
    kill "${HARDHAT_PID}" 2>/dev/null || true
  fi
  if [[ -n "${IPFS_PID:-}" ]] && kill -0 "${IPFS_PID}" 2>/dev/null; then
    kill "${IPFS_PID}" 2>/dev/null || true
  fi

  wait "${WEB_PID:-}" "${HARDHAT_PID:-}" "${IPFS_PID:-}" 2>/dev/null || true
  exit "${exit_code}"
}

trap cleanup EXIT INT TERM

wait_for_http() {
  local name="$1"
  local method="$2"
  local url="$3"
  local data="${4:-}"
  local attempts="${5:-60}"

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

mkdir -p "${IPFS_PATH}" /app/smart-contract/executions

if [[ ! -f "${IPFS_PATH}/config" ]]; then
  echo "Initializing IPFS repository at ${IPFS_PATH}"
  ipfs init --profile=server
fi

echo "Starting IPFS daemon"
ipfs daemon --migrate=true &
IPFS_PID=$!

wait_for_http "IPFS API" "POST" "${IPFS_API_URL%/}/api/v0/version"

echo "Starting Hardhat node"
cd /app/smart-contract
npx hardhat node --hostname 0.0.0.0 &
HARDHAT_PID=$!

wait_for_http \
  "Hardhat RPC" \
  "POST" \
  "${RPC_URL}" \
  '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}'

echo "Deploying local smart contract"
RPC_URL="${RPC_URL}" npx hardhat run scripts/deploy.js --network localhost

echo "Starting DNAT web client on port ${WEB_PORT}"
RPC_URL="${RPC_URL}" \
IPFS_API_URL="${IPFS_API_URL}" \
WEB_PORT="${WEB_PORT}" \
EXECUTOR_URL="${EXECUTOR_URL}" \
BUILDER_URL="${BUILDER_URL}" \
PRIVATE_KEY="${PRIVATE_KEY}" \
ASSET_ENCRYPTION_KEY="${ASSET_ENCRYPTION_KEY}" \
node scripts/api-server.js &
WEB_PID=$!

wait "${WEB_PID}"
