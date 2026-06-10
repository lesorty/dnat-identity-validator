#!/usr/bin/env bash
# Gera o arquivo .whl do pacote malicioso.
# Requer: pip install wheel setuptools
# Uso: bash build_wheel.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

pip install wheel setuptools --quiet
python setup.py bdist_wheel --quiet

WHL=$(find dist -name "*.whl" | head -1)
cp "$WHL" ../
echo "[build_wheel] wheel gerado: $WHL"
echo "[build_wheel] copiado para assets/$(basename $WHL)"
