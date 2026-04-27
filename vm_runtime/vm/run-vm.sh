#!/bin/bash
set -e

BUNDLE_PATH="$1"
HTTP_PORT="${2:-8888}"

[ -f "$BUNDLE_PATH" ] || { echo "Bundle not found" >&2; exit 1; }

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KERNEL="$ROOT/artifacts/vmlinux"
ROOTFS="$ROOT/artifacts/rootfs.ext4"

[ -f "$KERNEL" ] && [ -f "$ROOTFS" ] || { echo "Artifacts not found" >&2; exit 1; }

run_as_root() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
        return
    fi

    if command -v sudo >/dev/null 2>&1; then
        sudo "$@"
        return
    fi

    echo "Root privileges required to run: $*" >&2
    exit 1
}

WORKDIR=$(mktemp -d)
trap "pkill -9 firecracker 2>/dev/null; rm -rf $WORKDIR" EXIT

OVERLAY="$WORKDIR/rootfs-overlay.ext4"
INPUT_DISK="$WORKDIR/input.ext4"
OUTPUT_DISK="$WORKDIR/output.ext4"
SOCKET="$WORKDIR/firecracker.socket"
INPUT_MOUNT="$WORKDIR/input-mount"
OUTPUT_MOUNT="$WORKDIR/output-mount"
SERIAL_LOG="$WORKDIR/serial.log"

cp "$ROOTFS" "$OVERLAY"
dd if=/dev/zero of="$INPUT_DISK" bs=1M count=64 >/dev/null 2>&1
dd if=/dev/zero of="$OUTPUT_DISK" bs=1M count=64 >/dev/null 2>&1
mkfs.ext4 -q "$INPUT_DISK" 2>/dev/null || true
mkfs.ext4 -q "$OUTPUT_DISK" 2>/dev/null || true

mkdir -p "$INPUT_MOUNT"
run_as_root mount "$INPUT_DISK" "$INPUT_MOUNT"
run_as_root cp "$BUNDLE_PATH" "$INPUT_MOUNT/bundle.tar.gz"
run_as_root sync
run_as_root umount "$INPUT_MOUNT"

firecracker --api-sock "$SOCKET" >"$SERIAL_LOG" 2>&1 &
FC_PID=$!

sleep 1

curl --unix-socket "$SOCKET" -s -X PUT 'http://localhost/machine-config' \
  -H 'Content-Type: application/json' \
  -d '{"vcpu_count": 1, "mem_size_mib": 512, "ht_enabled": false}' >/dev/null 2>&1

curl --unix-socket "$SOCKET" -s -X PUT 'http://localhost/boot-source' \
  -H 'Content-Type: application/json' \
  -d "{\"kernel_image_path\": \"$KERNEL\", \"boot_args\": \"console=ttyS0 reboot=k panic=1 pci=off root=/dev/vda rw init=/init\"}" >/dev/null 2>&1

curl --unix-socket "$SOCKET" -s -X PUT 'http://localhost/drives/rootfs' \
  -H 'Content-Type: application/json' \
  -d "{\"drive_id\": \"rootfs\", \"path_on_host\": \"$OVERLAY\", \"is_root_device\": true, \"is_read_only\": false}" >/dev/null 2>&1

curl --unix-socket "$SOCKET" -s -X PUT 'http://localhost/drives/input' \
  -H 'Content-Type: application/json' \
  -d "{\"drive_id\": \"input\", \"path_on_host\": \"$INPUT_DISK\", \"is_root_device\": false, \"is_read_only\": true}" >/dev/null 2>&1

curl --unix-socket "$SOCKET" -s -X PUT 'http://localhost/drives/output' \
  -H 'Content-Type: application/json' \
  -d "{\"drive_id\": \"output\", \"path_on_host\": \"$OUTPUT_DISK\", \"is_root_device\": false, \"is_read_only\": false}" >/dev/null 2>&1

curl --unix-socket "$SOCKET" -s -X PUT 'http://localhost/actions' \
  -H 'Content-Type: application/json' \
  -d '{"action_type": "InstanceStart"}' >/dev/null 2>&1

for i in {1..120}; do
    grep -q "EXECUTION_COMPLETE" "$SERIAL_LOG" 2>/dev/null && break
    kill -0 $FC_PID 2>/dev/null || { sleep 2; break; }
    sleep 1
done

mkdir -p "$OUTPUT_MOUNT"
run_as_root mount -o ro "$OUTPUT_DISK" "$OUTPUT_MOUNT" 2>/dev/null || { echo "{\"error\": \"mount failed\"}"; exit 1; }
[ -f "$OUTPUT_MOUNT/result.json" ] && cat "$OUTPUT_MOUNT/result.json" || echo "{\"error\": \"no result\", \"serialLog\": $(python3 -c "import json, pathlib; print(json.dumps(pathlib.Path('$SERIAL_LOG').read_text(errors='ignore')[-4000:]))")}"
run_as_root umount "$OUTPUT_MOUNT" 2>/dev/null || true
