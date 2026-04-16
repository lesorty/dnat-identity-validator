#!/bin/bash
set -e

BUNDLE_PATH="$1"
HTTP_PORT="${2:-8888}"

[ -f "$BUNDLE_PATH" ] || { echo "Bundle not found" >&2; exit 1; }

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KERNEL="$ROOT/artifacts/vmlinux"
ROOTFS="$ROOT/artifacts/rootfs.ext4"

[ -f "$KERNEL" ] && [ -f "$ROOTFS" ] || { echo "Artifacts not found" >&2; exit 1; }

WORKDIR=$(mktemp -d)
trap "pkill -9 firecracker 2>/dev/null; rm -rf $WORKDIR" EXIT

OVERLAY="$WORKDIR/rootfs-overlay.ext4"
OUTPUT_DISK="$WORKDIR/output.ext4"
SOCKET="$WORKDIR/firecracker.socket"
OUTPUT_MOUNT="$WORKDIR/output-mount"
SERIAL_LOG="$WORKDIR/serial.log"

qemu-img create -f qcow2 -b "$ROOTFS" "$OVERLAY" >/dev/null 2>&1
dd if=/dev/zero of="$OUTPUT_DISK" bs=1M count=64 >/dev/null 2>&1
mkfs.ext4 -q "$OUTPUT_DISK" 2>/dev/null || true

cd "$(dirname "$BUNDLE_PATH")"
python3 -m http.server $HTTP_PORT >"$WORKDIR/http.log" 2>&1 &
HTTP_PID=$!

firecracker --api-sock "$SOCKET" >"$SERIAL_LOG" 2>&1 &
FC_PID=$!

sleep 1

curl --unix-socket "$SOCKET" -s -X PUT 'http://localhost/boot-source' \
  -H 'Content-Type: application/json' \
  -d "{\"kernel_image_path\": \"$KERNEL\", \"boot_args\": \"console=ttyS0 reboot=k panic=1 pci=off\"}" >/dev/null 2>&1 || true

curl --unix-socket "$SOCKET" -s -X PUT 'http://localhost/drives/rootfs' \
  -H 'Content-Type: application/json' \
  -d "{\"drive_id\": \"rootfs\", \"path_on_host\": \"$OVERLAY\", \"is_root_device\": true, \"is_read_only\": false}" >/dev/null 2>&1 || true

curl --unix-socket "$SOCKET" -s -X PUT 'http://localhost/drives/output' \
  -H 'Content-Type: application/json' \
  -d "{\"drive_id\": \"output\", \"path_on_host\": \"$OUTPUT_DISK\", \"is_root_device\": false, \"is_read_only\": false}" >/dev/null 2>&1 || true

curl --unix-socket "$SOCKET" -s -X PUT 'http://localhost/actions' \
  -H 'Content-Type: application/json' \
  -d '{"action_type": "InstanceStart"}' >/dev/null 2>&1 || true

for i in {1..120}; do
    grep -q "EXECUTION_COMPLETE" "$SERIAL_LOG" 2>/dev/null && break
    kill -0 $FC_PID 2>/dev/null || { sleep 2; break; }
    sleep 1
done

mkdir -p "$OUTPUT_MOUNT"
sudo mount -o ro "$OUTPUT_DISK" "$OUTPUT_MOUNT" 2>/dev/null || { echo "{\"error\": \"mount failed\"}"; exit 1; }
[ -f "$OUTPUT_MOUNT/result.json" ] && cat "$OUTPUT_MOUNT/result.json" || echo "{\"error\": \"no result\"}"
sudo umount "$OUTPUT_MOUNT" 2>/dev/null || true