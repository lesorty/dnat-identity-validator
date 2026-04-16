#!/bin/bash
set -e

ARTIFACT="$(cd "$(dirname "$0")/.." && pwd)/artifacts/rootfs.ext4"

if [ -f "$ARTIFACT" ]; then
    exit 0
fi

mkdir -p "$(dirname "$ARTIFACT")"
ROOTFS=/tmp/firecracker-rootfs
rm -rf "$ROOTFS"

sudo debootstrap --arch=amd64 --variant=minbase noble "$ROOTFS" http://archive.ubuntu.com/ubuntu/

sudo chroot "$ROOTFS" apt-get update
sudo chroot "$ROOTFS" apt-get install -y python3 curl tar gzip

sudo cp "$(dirname "$0")/../rootfs/init" "$ROOTFS/init"
sudo cp "$(dirname "$0")/../rootfs/runner" "$ROOTFS/runner"
sudo chmod +x "$ROOTFS/init" "$ROOTFS/runner"

dd if=/dev/zero of="$ARTIFACT" bs=1M count=512 2>/dev/null
mkfs.ext4 "$ARTIFACT" >/dev/null 2>&1

mount_dir=$(mktemp -d)
sudo mount "$ARTIFACT" "$mount_dir"
sudo cp -r "$ROOTFS"/* "$mount_dir/"
sudo umount "$mount_dir"
rmdir "$mount_dir"