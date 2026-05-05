#!/bin/bash
set -euo pipefail

ARTIFACT="$(cd "$(dirname "$0")/.." && pwd)/artifacts/vmlinux"

# Evita recompilar o kernel quando o artefato ja esta disponivel no cache da imagem.
if [ -f "$ARTIFACT" ]; then
    exit 0
fi

mkdir -p "$(dirname "$ARTIFACT")"
cd /tmp

git clone --depth=1 -b v6.6 https://github.com/torvalds/linux.git 2>/dev/null || (cd linux && git pull)
cd linux

# Baseia o kernel em `defconfig` e depois liga apenas o necessario para guest Firecracker com rede.
make defconfig
scripts/config --disable DEBUG_INFO
scripts/config --enable ACPI
scripts/config --enable PCI
scripts/config --enable KVM_GUEST
scripts/config --enable VIRTIO
scripts/config --enable VIRTIO_MMIO
scripts/config --enable VIRTIO_MMIO_CMDLINE_DEVICES
scripts/config --enable VIRTIO_BLK
scripts/config --enable VIRTIO_NET
scripts/config --enable NET
scripts/config --enable INET
scripts/config --enable IPV6
scripts/config --enable UNIX
scripts/config --enable PACKET
scripts/config --enable DEVTMPFS
scripts/config --enable DEVTMPFS_MOUNT
scripts/config --enable BLK_DEV
scripts/config --enable EXT4_FS

make -j"$(nproc)"
cp vmlinux "$ARTIFACT"
