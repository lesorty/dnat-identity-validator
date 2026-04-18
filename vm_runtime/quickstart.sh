#!/bin/bash
set -e

for cmd in debootstrap qemu-img firecracker curl python3; do
    command -v $cmd >/dev/null || { echo "Missing: $cmd"; exit 1; }
done

cd "$(dirname "$0")"

echo "Building images..."
bash build/ensure-image.sh >/dev/null

echo "Setting up runtime..."
bash setup-runtime.sh >/dev/null

echo "✓ Ready"
echo ""
echo "Usage:"
echo "  bash execute-bundle.sh | jq ."
echo "  python3 executor.py 5000"
