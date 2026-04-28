#!/bin/bash
set -e

ARTIFACT="$(cd "$(dirname "$0")/.." && pwd)/artifacts/rootfs.ext4"
ROOTFS_TARBALL="$(cd "$(dirname "$0")/.." && pwd)/artifacts/rootfs.tar.gz"
UBUNTU_RELEASE="jammy"
UBUNTU_MIRROR="http://archive.ubuntu.com/ubuntu/"
FORCE_REBUILD="${FORCE_REBUILD_ROOTFS:-0}"

if [ "$FORCE_REBUILD" != "1" ] && [ -f "$ARTIFACT" ]; then
    exit 0
fi

mkdir -p "$(dirname "$ARTIFACT")"
rm -f "$ARTIFACT"
ROOTFS=/tmp/firecracker-rootfs
rm -rf "$ROOTFS"

sudo debootstrap --arch=amd64 --variant=minbase "$UBUNTU_RELEASE" "$ROOTFS" "$UBUNTU_MIRROR"

if ! sudo chroot "$ROOTFS" apt-get update; then
    sudo chroot "$ROOTFS" sed -i 's|http://archive.ubuntu.com/ubuntu/|http://old-releases.ubuntu.com/ubuntu/|g' /etc/apt/sources.list
    sudo chroot "$ROOTFS" apt-get update
fi

sudo chroot "$ROOTFS" apt-get install -y python3 curl tar gzip

sudo cp "$(dirname "$0")/../rootfs/init" "$ROOTFS/init"
sudo cp "$(dirname "$0")/../rootfs/runner" "$ROOTFS/runner"
sudo chmod +x "$ROOTFS/init" "$ROOTFS/runner"

sudo tar -C "$ROOTFS" -czf "$ROOTFS_TARBALL" .

dd if=/dev/zero of="$ARTIFACT" bs=1M count=512 2>/dev/null
mkfs.ext4 "$ARTIFACT" >/dev/null 2>&1

mount_dir=$(mktemp -d)
if sudo mount "$ARTIFACT" "$mount_dir" 2>/dev/null; then
    sudo cp -r "$ROOTFS"/* "$mount_dir/"
    sudo umount "$mount_dir"
    rmdir "$mount_dir"
    echo "Filesystem created successfully"
else
    echo "Mount failed, keeping tar archive fallback..."
    rm -f "$ARTIFACT"
    dd if=/dev/zero of="$ARTIFACT" bs=1M count=512 2>/dev/null
    mkfs.ext4 "$ARTIFACT" >/dev/null 2>&1
    rmdir "$mount_dir"
fi
