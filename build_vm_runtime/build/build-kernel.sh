#!/bin/bash
set -euo pipefail

# Define local onde o kernel vai ser armazenado.
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

#Suporte a execução como guest virtualizado.
scripts/config --enable KVM_GUEST

# Habilita o suporte a virtio, que é o mecanismo de paravirtualização recomendado para Firecracker.
scripts/config --enable VIRTIO
scripts/config --enable VIRTIO_MMIO
scripts/config --enable VIRTIO_MMIO_CMDLINE_DEVICES
scripts/config --enable VIRTIO_BLK
scripts/config --enable VIRTIO_NET

# Habilita o suporte a rede.
scripts/config --enable NET
scripts/config --enable INET
scripts/config --enable IPV6
scripts/config --enable UNIX
scripts/config --enable PACKET


scripts/config --enable DEVTMPFS
scripts/config --enable DEVTMPFS_MOUNT
scripts/config --enable BLK_DEV

# Habilita o suporte a EXT4, que é o sistema de arquivos usado no rootfs.
scripts/config --enable EXT4_FS

# Compila o kernel.
make -j"$(nproc)"

# Copia o kernel compilado para o local do artefato.
cp vmlinux "$ARTIFACT"
