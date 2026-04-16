#!/usr/bin/env bash
set -e

ROOT=$(cd "$(dirname "$0")/.." && pwd)

KERNEL="$ROOT/artifacts/vmlinux"
IMAGE="$ROOT/artifacts/rootfs.img"

if [ -f "$KERNEL" ] && [ -f "$IMAGE" ]; then
    echo "Base image already exists."
    exit 0
fi

echo "Building base VM image..."

mkdir -p $ROOT/artifacts

bash $ROOT/build/build-kernel.sh
bash $ROOT/build/build-rootfs.sh
bash $ROOT/build/build-image.sh

echo "VM image created."