#!/bin/bash
set -euo pipefail

BUNDLE_PATH="$1"

[ -f "$BUNDLE_PATH" ] || { echo "Bundle not found" >&2; exit 1; }

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KERNEL="$ROOT/artifacts/vmlinux"
ROOTFS="$ROOT/artifacts/rootfs.ext4"
# O guest identifica discos olhando apenas para arquivos-marker criados pelo host.
OUTPUT_MARKER="dnat-output.marker"
APP_MARKER="dnat-application.marker"
RESULT_FILE="result.json"
RESULT_STDOUT_FILE="stdout.txt"
RESULT_STDERR_FILE="stderr.txt"
EXECUTION_COMPLETE_MARKER="EXECUTION_COMPLETE"
EXECUTION_COMPLETE_PREFIX="EXECUTION_COMPLE"
GUEST_HALTED_MARKER="System halted"
VM_TIMEOUT_SECONDS="${VM_TIMEOUT_SECONDS:-660}"
SHUTDOWN_GRACE_SECONDS="${SHUTDOWN_GRACE_SECONDS:-20}"

[ -f "$KERNEL" ] && [ -f "$ROOTFS" ] || { echo "Artifacts not found" >&2; exit 1; }

fc_put() {
    local endpoint="$1"
    local payload="$2"
    local response
    local body
    local status

    response=$(curl --unix-socket "$SOCKET" -sS -w $'\n%{http_code}' -X PUT "http://localhost/${endpoint}" \
      -H 'Content-Type: application/json' \
      -d "$payload")
    body="${response%$'\n'*}"
    status="${response##*$'\n'}"

    if [ "$status" -lt 200 ] || [ "$status" -ge 300 ]; then
        echo "{\"error\": \"firecracker api error\", \"endpoint\": \"${endpoint}\", \"status\": ${status}, \"body\": $(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$body")}" 
        exit 1
    fi
}

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

json_string() {
    python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"
}

json_file_tail() {
    python3 - "$1" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
if not path.is_file():
    print("null")
else:
    print(json.dumps(path.read_text(errors="ignore")[-4000:]))
PY
}

emit_error() {
    local message="$1"
    local firecracker_log="${2:-}"

    if [ -n "$firecracker_log" ] && [ -f "$firecracker_log" ]; then
        echo "{\"error\": $(json_string "$message"), \"firecrackerLog\": $(json_file_tail "$firecracker_log")}"
        return
    fi

    echo "{\"error\": $(json_string "$message")}"
}

cleanup() {
    # Toda execucao usa overlays/discos temporarios novos; nada da aplicacao e reutilizado depois.
    if [ -n "${RESULT_MOUNT:-}" ] && mountpoint -q "$RESULT_MOUNT" 2>/dev/null; then
        run_as_root umount "$RESULT_MOUNT" || true
    fi

    if [ -n "${INPUT_MOUNT:-}" ] && mountpoint -q "$INPUT_MOUNT" 2>/dev/null; then
        run_as_root umount "$INPUT_MOUNT" || true
    fi

    if [ -n "${OUTPUT_MOUNT:-}" ] && mountpoint -q "$OUTPUT_MOUNT" 2>/dev/null; then
        run_as_root umount "$OUTPUT_MOUNT" || true
    fi

    if [ -n "${FC_PID:-}" ] && kill -0 "$FC_PID" 2>/dev/null; then
        kill -9 "$FC_PID" 2>/dev/null || true
        wait "$FC_PID" 2>/dev/null || true
    fi

    rm -rf "${WORKDIR:-}"
}

mount_output_disk() {
    if run_as_root mount -o loop,ro "$OUTPUT_DISK" "$RESULT_MOUNT"; then
        return
    fi

    # If the guest was force-stopped after syncing the result, ext4 may still
    # require journal replay, which only works on a writable mount.
    run_as_root mount -o loop "$OUTPUT_DISK" "$RESULT_MOUNT"
}

WORKDIR=$(mktemp -d)
trap cleanup EXIT

# `APP_DISK` e anexado somente quando a execucao usa um artefato ext4 construido pelo builder.
OVERLAY="$WORKDIR/rootfs-overlay.ext4"
INPUT_DISK="$WORKDIR/input.ext4"
OUTPUT_DISK="$WORKDIR/output.ext4"
APP_DISK="$WORKDIR/application.ext4"
SOCKET="$WORKDIR/firecracker.socket"
INPUT_MOUNT="$WORKDIR/input-mount"
OUTPUT_MOUNT="$WORKDIR/output-mount"
RESULT_MOUNT="$WORKDIR/result-mount"
STAGING_DIR="$WORKDIR/staging"
GUEST_BUNDLE_PATH="$WORKDIR/guest-bundle.tar.gz"
SERIAL_LOG="$WORKDIR/serial.log"

cp "$ROOTFS" "$OVERLAY"
mkdir -p "$STAGING_DIR"
tar -xzf "$BUNDLE_PATH" -C "$STAGING_DIR"
[ -d "$STAGING_DIR/workspace" ] || { emit_error "workspace missing from execution bundle"; exit 1; }
# Reempacota apenas `workspace/` para o guest; o host interpreta e filtra o bundle original antes.
tar -C "$STAGING_DIR" -czf "$GUEST_BUNDLE_PATH" workspace

if [ -f "$STAGING_DIR/artifacts/application.ext4" ]; then
    cp "$STAGING_DIR/artifacts/application.ext4" "$APP_DISK"
fi

dd if=/dev/zero of="$INPUT_DISK" bs=1M count=64 >/dev/null 2>&1
dd if=/dev/zero of="$OUTPUT_DISK" bs=1M count=64 >/dev/null 2>&1
mkfs.ext4 -q "$INPUT_DISK" 2>/dev/null || true
mkfs.ext4 -q "$OUTPUT_DISK" 2>/dev/null || true

mkdir -p "$INPUT_MOUNT"
mkdir -p "$OUTPUT_MOUNT" "$RESULT_MOUNT"
run_as_root mount -o loop "$INPUT_DISK" "$INPUT_MOUNT"
run_as_root cp "$GUEST_BUNDLE_PATH" "$INPUT_MOUNT/bundle.tar.gz"
run_as_root sync
run_as_root umount "$INPUT_MOUNT"
run_as_root mount -o loop "$OUTPUT_DISK" "$OUTPUT_MOUNT"
run_as_root touch "$OUTPUT_MOUNT/$OUTPUT_MARKER"
run_as_root sync
run_as_root umount "$OUTPUT_MOUNT"

firecracker --api-sock "$SOCKET" >"$SERIAL_LOG" 2>&1 &
FC_PID=$!

for _ in {1..20}; do
    [ -S "$SOCKET" ] && break
    sleep 0.5
done

[ -S "$SOCKET" ] || { emit_error "firecracker socket not created" "$SERIAL_LOG"; exit 1; }

# Executor usa menos recursos porque apenas roda o script ja empacotado.
fc_put "machine-config" '{"vcpu_count": 1, "mem_size_mib": 512, "smt": false}'

fc_put "boot-source" "{\"kernel_image_path\": \"$KERNEL\", \"boot_args\": \"console=ttyS0 loglevel=4 noapic reboot=k panic=1 pci=off nomodules random.trust_cpu=on root=/dev/vda rootfstype=ext4 rootwait rw init=/init\"}"

fc_put "drives/rootfs" "{\"drive_id\": \"rootfs\", \"path_on_host\": \"$OVERLAY\", \"is_root_device\": true, \"is_read_only\": false}"

fc_put "drives/input" "{\"drive_id\": \"input\", \"path_on_host\": \"$INPUT_DISK\", \"is_root_device\": false, \"is_read_only\": true}"
fc_put "drives/output" "{\"drive_id\": \"output\", \"path_on_host\": \"$OUTPUT_DISK\", \"is_root_device\": false, \"is_read_only\": false}"
if [ -f "$APP_DISK" ]; then
    # O artefato da aplicacao entra read-only para separar codigo/deps do workspace efemero.
    fc_put "drives/application" "{\"drive_id\": \"application\", \"path_on_host\": \"$APP_DISK\", \"is_root_device\": false, \"is_read_only\": true}"
fi

fc_put "actions" '{"action_type": "InstanceStart"}'

execution_complete=0
# A serial e o canal de sincronizacao entre host e guest para timeout/termino.
for ((i=0; i<VM_TIMEOUT_SECONDS; i++)); do
    if grep -q "$EXECUTION_COMPLETE_MARKER" "$SERIAL_LOG" 2>/dev/null || \
       grep -q "$EXECUTION_COMPLETE_PREFIX" "$SERIAL_LOG" 2>/dev/null || \
       grep -q "$GUEST_HALTED_MARKER" "$SERIAL_LOG" 2>/dev/null; then
        execution_complete=1
        break
    fi
    if ! kill -0 "$FC_PID" 2>/dev/null; then
        break
    fi
    sleep 1
done

if [ "$execution_complete" -eq 1 ] && kill -0 "$FC_PID" 2>/dev/null; then
    fc_put "actions" '{"action_type": "SendCtrlAltDel"}'

    for ((i=0; i<SHUTDOWN_GRACE_SECONDS; i++)); do
        if ! kill -0 "$FC_PID" 2>/dev/null; then
            break
        fi
        sleep 1
    done
fi

if [ "$execution_complete" -eq 1 ] && kill -0 "$FC_PID" 2>/dev/null; then
    kill -TERM "$FC_PID" 2>/dev/null || true
    sleep 2
fi

if [ "$execution_complete" -eq 1 ] && kill -0 "$FC_PID" 2>/dev/null; then
    kill -KILL "$FC_PID" 2>/dev/null || true
    wait "$FC_PID" 2>/dev/null || true
fi

if kill -0 "$FC_PID" 2>/dev/null; then
    emit_error "microVM execution timed out" "$SERIAL_LOG"
    exit 1
fi

wait "$FC_PID" || true

mount_output_disk

# A resposta HTTP final e sempre derivada do disco de saida persistido pela microVM.
python3 - <<PY
import json
from pathlib import Path

result_mount = Path(r"$RESULT_MOUNT")
serial_log = Path(r"$SERIAL_LOG")
result_path = result_mount / "$RESULT_FILE"
stdout_path = result_mount / "$RESULT_STDOUT_FILE"
stderr_path = result_mount / "$RESULT_STDERR_FILE"

if not result_path.is_file():
    print(json.dumps({
        "error": "no persisted result",
        "stdout": stdout_path.read_text(errors="ignore") if stdout_path.is_file() else "",
        "stderr": stderr_path.read_text(errors="ignore") if stderr_path.is_file() else "",
        "firecrackerLog": serial_log.read_text(errors="ignore")[-4000:],
    }))
    raise SystemExit(0)

payload = result_path.read_text(errors="ignore")
try:
    parsed = json.loads(payload)
except json.JSONDecodeError:
    print(json.dumps({
        "error": "invalid persisted result payload",
        "payload": payload,
        "stdout": stdout_path.read_text(errors="ignore") if stdout_path.is_file() else "",
        "stderr": stderr_path.read_text(errors="ignore") if stderr_path.is_file() else "",
        "firecrackerLog": serial_log.read_text(errors="ignore")[-4000:],
    }))
else:
    print(json.dumps(parsed))
PY
