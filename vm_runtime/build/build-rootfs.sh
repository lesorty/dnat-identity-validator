#!/bin/bash
set -e

ARTIFACT="$(cd "$(dirname "$0")/.." && pwd)/artifacts/rootfs.ext4"
ROOTFS_TARBALL="$(cd "$(dirname "$0")/.." && pwd)/artifacts/rootfs.tar.gz"
DEBIAN_RELEASE="bookworm"
DEBIAN_MIRROR="http://deb.debian.org/debian/"
FORCE_REBUILD="${FORCE_REBUILD_ROOTFS:-0}"

# O rootfs do executor e pequeno e estavel; evita rebuild desnecessario.
if [ "$FORCE_REBUILD" != "1" ] && [ -f "$ARTIFACT" ]; then
    exit 0
fi

mkdir -p "$(dirname "$ARTIFACT")"
rm -f "$ARTIFACT"
ROOTFS=/tmp/firecracker-rootfs
rm -rf "$ROOTFS"

# Guest minimo focado apenas em extrair bundle e rodar `workspace/run.sh`.
sudo debootstrap --arch=amd64 --variant=minbase "$DEBIAN_RELEASE" "$ROOTFS" "$DEBIAN_MIRROR"

if ! sudo chroot "$ROOTFS" apt-get update; then
    sudo chroot "$ROOTFS" sed -i 's|http://deb.debian.org/debian/|http://archive.debian.org/debian/|g' /etc/apt/sources.list
    sudo chroot "$ROOTFS" apt-get update
fi

sudo chroot "$ROOTFS" apt-get install -y python3 tar gzip busybox-static ca-certificates

sudo cp "$(dirname "$0")/../rootfs/init" "$ROOTFS/init"
sudo cp "$(dirname "$0")/../rootfs/runner" "$ROOTFS/runner"
sudo sed -i 's/\r$//' "$ROOTFS/init" "$ROOTFS/runner"
sudo chmod +x "$ROOTFS/init" "$ROOTFS/runner"

# O tarball e usado como fallback para restaurar o ext4 no startup do container executor.
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
