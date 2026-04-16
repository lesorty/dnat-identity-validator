#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ARTIFACT_DIR="$ROOT_DIR/artifacts"

KERNEL="$ARTIFACT_DIR/vmlinux"
ROOTFS="$ARTIFACT_DIR/rootfs.ext4"

WORKDIR=$(mktemp -d)

OVERLAY="$WORKDIR/rootfs-overlay.ext4"

qemu-img create \
  -f qcow2 \
  -b "$ROOTFS" \
  "$OVERLAY"

SOCKET="$WORKDIR/firecracker.socket"

firecracker --api-sock "$SOCKET" &

sleep 1

curl --unix-socket "$SOCKET" -i \
  -X PUT 'http://localhost/boot-source' \
  -H 'Content-Type: application/json' \
  -d "{
    \"kernel_image_path\": \"$KERNEL\",
    \"boot_args\": \"console=ttyS0 reboot=k panic=1 pci=off\"
}"

curl --unix-socket "$SOCKET" -i \
  -X PUT 'http://localhost/drives/rootfs' \
  -H 'Content-Type: application/json' \
  -d "{
     \"drive_id\": \"rootfs\",
     \"path_on_host\": \"$OVERLAY\",
     \"is_root_device\": true,
     \"is_read_only\": false
}"

curl --unix-socket "$SOCKET" -i \
  -X PUT 'http://localhost/actions' \
  -H  'Content-Type: application/json' \
  -d '{
      "action_type": "InstanceStart"
   }'