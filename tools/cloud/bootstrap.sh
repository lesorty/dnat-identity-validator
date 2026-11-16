#!/usr/bin/env bash
# Prepara uma VM Ubuntu (22.04 ou 24.04, x86_64 ou arm64) para a fase de testes na nuvem.
# Rodar de dentro do repositório já clonado no commit congelado:
#
#   tools/cloud/bootstrap.sh [--docker] [--no-data] [--judges]
#
#   --docker   instala Docker e o plugin compose (pilha Docker, testes T1–T5, overhead T-812)
#   --no-data  não baixa dados (só ferramentas e ambientes)
#   --judges   baixa também os avaliadores do portão (Qwen3Guard-4B e Gemma; ~16 GB)
#
# Idempotente: rodar de novo só completa o que falta. Node e uv em versões fixas, conferidos pelo
# SHA-256 publicado; dados conferidos pelos digests versionados no repositório (manifestos em
# model_gate/models e model_gate/data). No fim: ficha da máquina e `make doctor`.
set -euo pipefail

NODE_VERSION=22.22.1
UV_VERSION=0.12.20
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DOCKER=0; DATA=1; JUDGES=0
for a in "$@"; do
  case "$a" in
    --docker) DOCKER=1 ;;
    --no-data) DATA=0 ;;
    --judges) JUDGES=1 ;;
    *) echo "opção desconhecida: $a" >&2; exit 2 ;;
  esac
done
SUDO=""; [ "$(id -u)" = 0 ] || SUDO="sudo"
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

step "pacotes do sistema"
export DEBIAN_FRONTEND=noninteractive
$SUDO apt-get update -qq
$SUDO apt-get install -y -qq --no-install-recommends git curl ca-certificates xz-utils build-essential \
  e2fsprogs python3 python3-venv util-linux rsync make procps >/dev/null

case "$(uname -m)" in
  x86_64) NODE_ARCH=x64; UV_ARCH=x86_64-unknown-linux-gnu ;;
  aarch64) NODE_ARCH=arm64; UV_ARCH=aarch64-unknown-linux-gnu ;;
  *) echo "arquitetura não suportada: $(uname -m)" >&2; exit 1 ;;
esac
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

step "Node $NODE_VERSION"
if [ "$(node --version 2>/dev/null)" != "v$NODE_VERSION" ]; then
  f="node-v$NODE_VERSION-linux-$NODE_ARCH.tar.xz"
  curl -fsSL "https://nodejs.org/dist/v$NODE_VERSION/$f" -o "$TMP/$f"
  curl -fsSL "https://nodejs.org/dist/v$NODE_VERSION/SHASUMS256.txt" -o "$TMP/SHASUMS256.txt"
  (cd "$TMP" && grep " $f\$" SHASUMS256.txt | sha256sum -c -)
  $SUDO rm -rf /opt/node && $SUDO mkdir -p /opt/node && $SUDO tar -xJf "$TMP/$f" -C /opt/node --strip-components=1
  for b in node npm npx; do $SUDO ln -sf "/opt/node/bin/$b" "/usr/local/bin/$b"; done
fi
node --version

step "uv $UV_VERSION"
if [ "$(uv --version 2>/dev/null | cut -d' ' -f2)" != "$UV_VERSION" ]; then
  f="uv-$UV_ARCH.tar.gz"
  curl -fsSL "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/$f" -o "$TMP/$f"
  curl -fsSL "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/$f.sha256" -o "$TMP/$f.sha256"
  (cd "$TMP" && sha256sum -c "$f.sha256")
  tar -xzf "$TMP/$f" -C "$TMP"
  $SUDO install -m 0755 "$TMP/uv-$UV_ARCH/uv" "$TMP/uv-$UV_ARCH/uvx" /usr/local/bin/
fi
uv --version

if [ "$DOCKER" = 1 ]; then
  step "Docker"
  if ! command -v docker >/dev/null; then
    $SUDO apt-get install -y -qq --no-install-recommends docker.io >/dev/null
    $SUDO apt-get install -y -qq --no-install-recommends docker-compose-v2 >/dev/null 2>&1 \
      || $SUDO apt-get install -y -qq --no-install-recommends docker-compose-plugin >/dev/null
    $SUDO usermod -aG docker "$(id -un)" || true
    echo "Docker instalado: entre de novo na sessão para usar sem sudo"
  fi
fi

step "ambientes (make setup)"
cd "$REPO"
make setup

if [ "$DATA" = 1 ]; then
  step "dados do model_gate, conferidos pelos digests versionados"
  tools/cloud/fetch_data.sh $([ "$JUDGES" = 1 ] && echo --judges)
fi

step "ficha da máquina"
python3 -I tools/cloud/machine_card.py

step "doctor"
make doctor || true
echo
echo "pronto. Próximo passo: make campanha-status (o que a campanha vai rodar e o que falta)"
