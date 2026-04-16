#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ARTIFACT_DIR="$ROOT_DIR/artifacts"

KERNEL_VERSION=6.6

mkdir -p "$ARTIFACT_DIR"

cd /tmp

if [ ! -d linux ]; then
    git clone https://github.com/torvalds/linux.git
fi

cd linux

make defconfig

scripts/config --disable CONFIG_DEBUG_INFO
scripts/config --enable CONFIG_KVM_GUEST
scripts/config --enable CONFIG_VIRTIO
scripts/config --enable CONFIG_VIRTIO_PCI
scripts/config --enable CONFIG_VIRTIO_BLK
scripts/config --enable CONFIG_VIRTIO_NET

make -j$(nproc)

cp arch/x86/boot/bzImage "$ARTIFACT_DIR/vmlinux"

echo "Kernel built."