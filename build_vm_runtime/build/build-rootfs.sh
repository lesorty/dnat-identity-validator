#!/bin/bash
set -euo pipefail

ARTIFACT="$(cd "$(dirname "$0")/.." && pwd)/artifacts/rootfs.ext4"
ROOTFS_TARBALL="$(cd "$(dirname "$0")/.." && pwd)/artifacts/rootfs.tar.gz"
DEBIAN_RELEASE="bookworm"
DEBIAN_MIRROR="http://deb.debian.org/debian/"
FORCE_REBUILD="${FORCE_REBUILD_ROOTFS:-0}"

if [ "$FORCE_REBUILD" != "1" ] && [ -f "$ARTIFACT" ]; then
    exit 0
fi

mkdir -p "$(dirname "$ARTIFACT")"
rm -f "$ARTIFACT"
ROOTFS=/tmp/firecracker-build-rootfs
rm -rf "$ROOTFS"

sudo debootstrap --arch=amd64 --variant=minbase "$DEBIAN_RELEASE" "$ROOTFS" "$DEBIAN_MIRROR"

if ! sudo chroot "$ROOTFS" apt-get update; then
    sudo chroot "$ROOTFS" sed -i 's|http://deb.debian.org/debian/|http://archive.debian.org/debian/|g' /etc/apt/sources.list
    sudo chroot "$ROOTFS" apt-get update
fi

sudo chroot "$ROOTFS" apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-packaging \
    build-essential \
    gcc \
    g++ \
    make \
    pkg-config \
    libffi-dev \
    libssl-dev \
    ca-certificates \
    e2fsprogs \
    iproute2 \
    tar \
    gzip \
    curl \
    busybox-static

sudo mkdir -p "$ROOTFS/opt/dnat"
sudo cp "$(dirname "$0")/../rootfs/init" "$ROOTFS/init"
sudo cp "$(dirname "$0")/../rootfs/runner" "$ROOTFS/runner"
sudo cp "$(dirname "$0")/../smart-contract/scripts/build_application_artifact.py" "$ROOTFS/opt/dnat/build_application_artifact.py"
sudo sed -i 's/\r$//' "$ROOTFS/init" "$ROOTFS/runner" "$ROOTFS/opt/dnat/build_application_artifact.py"
sudo chmod +x "$ROOTFS/init" "$ROOTFS/runner" "$ROOTFS/opt/dnat/build_application_artifact.py"

sudo tar -C "$ROOTFS" -czf "$ROOTFS_TARBALL" .

dd if=/dev/zero of="$ARTIFACT" bs=1M count=1536 2>/dev/null
mkfs.ext4 "$ARTIFACT" >/dev/null 2>&1

mount_dir=$(mktemp -d)
if sudo mount "$ARTIFACT" "$mount_dir" 2>/dev/null; then
    sudo cp -r "$ROOTFS"/* "$mount_dir/"
    sudo umount "$mount_dir"
    rmdir "$mount_dir"
else
    rm -f "$ARTIFACT"
    dd if=/dev/zero of="$ARTIFACT" bs=1M count=1536 2>/dev/null
    mkfs.ext4 "$ARTIFACT" >/dev/null 2>&1
    rmdir "$mount_dir"
fi
