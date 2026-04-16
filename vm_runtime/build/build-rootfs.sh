#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ARTIFACT_DIR="$ROOT_DIR/artifacts"
ROOTFS_DIR=/tmp/firecracker-rootfs

rm -rf "$ROOTFS_DIR"

sudo debootstrap \
    --arch=amd64 \
    --variant=minbase \
    noble \
    "$ROOTFS_DIR" \
    http://archive.ubuntu.com/ubuntu/

sudo cp "$ROOT_DIR/rootfs/init" "$ROOTFS_DIR/init"
sudo cp "$ROOT_DIR/rootfs/runner" "$ROOTFS_DIR/runner"

sudo chmod +x "$ROOTFS_DIR/init"
sudo chmod +x "$ROOTFS_DIR/runner"

IMAGE="$ARTIFACT_DIR/rootfs.ext4"

dd if=/dev/zero of="$IMAGE" bs=1M count=256
mkfs.ext4 "$IMAGE"

mkdir -p /tmp/rootfs-mount

sudo mount "$IMAGE" /tmp/rootfs-mount
sudo cp -r "$ROOTFS_DIR"/* /tmp/rootfs-mount/
sudo umount /tmp/rootfs-mount

echo "RootFS built."