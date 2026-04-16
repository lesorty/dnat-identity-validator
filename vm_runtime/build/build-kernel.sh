#!/bin/bash
set -e

ARTIFACT="$(cd "$(dirname "$0")/.." && pwd)/artifacts/vmlinux"

if [ -f "$ARTIFACT" ]; then
    exit 0
fi

mkdir -p "$(dirname "$ARTIFACT")"
cd /tmp

git clone --depth=1 -b v6.6 https://github.com/torvalds/linux.git 2>/dev/null || (cd linux && git pull)
cd linux

make defconfig
scripts/config --disable CONFIG_DEBUG_INFO
scripts/config --enable CONFIG_KVM_GUEST CONFIG_VIRTIO CONFIG_VIRTIO_PCI CONFIG_VIRTIO_BLK CONFIG_VIRTIO_NET

make -j$(nproc)
cp arch/x86/boot/bzImage "$ARTIFACT"