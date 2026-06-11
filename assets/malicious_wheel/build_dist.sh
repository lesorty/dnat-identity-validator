#!/usr/bin/env bash
# Gera o pacote malicioso como sdist (.tar.gz) e wheel (.whl).
#
# - O sdist forca o pip a RECONSTRUIR o pacote (rodando setup.py) dentro do
#   build microVM da CVM2 -> exercita o payload de BUILD-TIME.
# - O wheel e instalado sem rodar setup.py -> util para exercitar apenas o
#   payload de IMPORT-TIME (em malicious_pkg/__init__.py) na CVM3.
#
# Uso: bash build_dist.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python3 -m pip install --quiet --upgrade build wheel setuptools

rm -rf dist build ./*.egg-info
python3 -m build --sdist --wheel . 2>/dev/null || {
    # Fallback para ambientes sem o pacote `build`.
    python3 setup.py sdist bdist_wheel
}

echo "[build_dist] artefatos gerados em dist/:"
ls -1 dist/
