#!/bin/bash
set -euo pipefail

BUNDLE_PATH="$1"
OUTPUT_BUNDLE_PATH="$2"

[ -f "$BUNDLE_PATH" ] || { echo "Build bundle not found" >&2; exit 1; }

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KERNEL="$ROOT/artifacts/vmlinux"
ROOTFS="$ROOT/artifacts/rootfs.ext4"
WHEEL_CACHE_SOURCE_DIR="${WHEEL_CACHE_SOURCE_DIR:-/var/dnat/wheel-cache}"
# Markers simples em disco permitem ao guest descobrir papeis dos volumes sem metadata extra.
OUTPUT_MARKER="dnat-build-output.marker"
WHEEL_CACHE_MARKER="dnat-wheel-cache.marker"
BUILD_RESULT_FILE="build-result.json"
BUILD_STDOUT_FILE="build-stdout.txt"
BUILD_STDERR_FILE="build-stderr.txt"
APPLICATION_ARTIFACT_NAME="application.ext4"
COMPLETE_MARKER="BUILD_COMPLETE"
COMPLETE_PREFIX="BUILD_COMPLET"
GUEST_HALTED_MARKER="System halted"
VM_TIMEOUT_SECONDS="${BUILD_VM_TIMEOUT_SECONDS:-1800}"
SHUTDOWN_GRACE_SECONDS="${BUILD_VM_SHUTDOWN_GRACE_SECONDS:-20}"
TAP_NAME="tap-build0"
HOST_IP="172.31.0.1/30"
GUEST_IP="172.31.0.2/32"
GUEST_MAC="06:00:ac:1f:00:02"

[ -f "$KERNEL" ] && [ -f "$ROOTFS" ] || { echo "Build VM artifacts not found" >&2; exit 1; }

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

mount_disk_ro_or_rw() {
    local image="$1"
    local mount_dir="$2"
    # Tenta leitura pura primeiro; cai para RW quando o journal ext4 exige replay.
    if run_as_root mount -o loop,ro "$image" "$mount_dir"; then
        return
    fi
    run_as_root mount -o loop "$image" "$mount_dir"
}

cleanup_network() {
    if [ -n "${WAN_IF:-}" ]; then
        run_as_root iptables -D FORWARD -i "$TAP_NAME" -o "$WAN_IF" -s 172.31.0.2/32 -d 10.0.0.0/8 -j REJECT 2>/dev/null || true
        run_as_root iptables -D FORWARD -i "$TAP_NAME" -o "$WAN_IF" -s 172.31.0.2/32 -d 172.16.0.0/12 -j REJECT 2>/dev/null || true
        run_as_root iptables -D FORWARD -i "$TAP_NAME" -o "$WAN_IF" -s 172.31.0.2/32 -d 192.168.0.0/16 -j REJECT 2>/dev/null || true
        run_as_root iptables -D FORWARD -i "$TAP_NAME" -o "$WAN_IF" -s 172.31.0.2/32 -d 127.0.0.0/8 -j REJECT 2>/dev/null || true
        run_as_root iptables -D FORWARD -i "$TAP_NAME" -o "$WAN_IF" -s 172.31.0.2/32 -d 169.254.0.0/16 -j REJECT 2>/dev/null || true
        run_as_root iptables -D FORWARD -i "$TAP_NAME" -o "$WAN_IF" -s 172.31.0.2/32 -d 172.31.0.1/32 -j REJECT 2>/dev/null || true
        run_as_root iptables -D FORWARD -i "$WAN_IF" -o "$TAP_NAME" -d 172.31.0.2/32 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || true
        run_as_root iptables -D FORWARD -i "$TAP_NAME" -o "$WAN_IF" -s 172.31.0.2/32 -j ACCEPT 2>/dev/null || true
        run_as_root iptables -t nat -D POSTROUTING -s 172.31.0.2/32 -o "$WAN_IF" -j MASQUERADE 2>/dev/null || true
    fi

    run_as_root ip link del "$TAP_NAME" 2>/dev/null || true
}

cleanup() {
    # Todo o estado da build fica dentro de um workdir efemero para evitar vazamento entre requisicoes.
    if [ -n "${RESULT_MOUNT:-}" ] && mountpoint -q "$RESULT_MOUNT" 2>/dev/null; then
        run_as_root umount "$RESULT_MOUNT" || true
    fi
    if [ -n "${INPUT_MOUNT:-}" ] && mountpoint -q "$INPUT_MOUNT" 2>/dev/null; then
        run_as_root umount "$INPUT_MOUNT" || true
    fi
    if [ -n "${OUTPUT_MOUNT:-}" ] && mountpoint -q "$OUTPUT_MOUNT" 2>/dev/null; then
        run_as_root umount "$OUTPUT_MOUNT" || true
    fi
    if [ -n "${CACHE_MOUNT:-}" ] && mountpoint -q "$CACHE_MOUNT" 2>/dev/null; then
        run_as_root umount "$CACHE_MOUNT" || true
    fi
    cleanup_network

    if [ -n "${FC_PID:-}" ] && kill -0 "$FC_PID" 2>/dev/null; then
        kill -9 "$FC_PID" 2>/dev/null || true
        wait "$FC_PID" 2>/dev/null || true
    fi

    rm -rf "${WORKDIR:-}"
}

directory_size_bytes() {
    python3 - "$1" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
total = 0
if root.is_dir():
    for entry in root.rglob("*"):
        if entry.is_file():
            total += entry.stat().st_size
print(total)
PY
}

create_data_disk_from_dir() {
    local source_dir="$1"
    local image_path="$2"
    local marker_name="$3"

    local size_bytes
    size_bytes="$(directory_size_bytes "$source_dir")"
    # Superdimensiona o disco para dar folga ao mkfs e a metadados ext4.
    local image_mb
    image_mb="$(python3 - "$size_bytes" <<'PY'
import math
import sys

size = int(sys.argv[1])
image_mb = max(64, math.ceil((size * 4 + 8 * 1024 * 1024) / (1024 * 1024)))
print(image_mb)
PY
)"

    mkdir -p "$source_dir"
    touch "$source_dir/$marker_name"
    dd if=/dev/zero of="$image_path" bs=1M count="$image_mb" >/dev/null 2>&1
    mkfs.ext4 -q -F -d "$source_dir" "$image_path"
}

setup_network() {
    # A microVM de build tem acesso de saida para baixar dependencias, mas bloqueia faixas privadas do host.
    WAN_IF="$(ip route show default | awk '/default/ {print $5; exit}')"
    [ -n "$WAN_IF" ] || { emit_error "Unable to determine default egress interface"; exit 1; }

    run_as_root sysctl -w net.ipv4.ip_forward=1 >/dev/null
    run_as_root ip link del "$TAP_NAME" 2>/dev/null || true
    run_as_root ip tuntap add dev "$TAP_NAME" mode tap
    run_as_root ip addr add "$HOST_IP" dev "$TAP_NAME"
    run_as_root ip link set "$TAP_NAME" up

    run_as_root iptables -t nat -A POSTROUTING -s 172.31.0.2/32 -o "$WAN_IF" -j MASQUERADE
    run_as_root iptables -A FORWARD -i "$TAP_NAME" -o "$WAN_IF" -s 172.31.0.2/32 -d 10.0.0.0/8 -j REJECT
    run_as_root iptables -A FORWARD -i "$TAP_NAME" -o "$WAN_IF" -s 172.31.0.2/32 -d 172.16.0.0/12 -j REJECT
    run_as_root iptables -A FORWARD -i "$TAP_NAME" -o "$WAN_IF" -s 172.31.0.2/32 -d 192.168.0.0/16 -j REJECT
    run_as_root iptables -A FORWARD -i "$TAP_NAME" -o "$WAN_IF" -s 172.31.0.2/32 -d 127.0.0.0/8 -j REJECT
    run_as_root iptables -A FORWARD -i "$TAP_NAME" -o "$WAN_IF" -s 172.31.0.2/32 -d 169.254.0.0/16 -j REJECT
    run_as_root iptables -A FORWARD -i "$TAP_NAME" -o "$WAN_IF" -s 172.31.0.2/32 -d 172.31.0.1/32 -j REJECT
    run_as_root iptables -A FORWARD -i "$WAN_IF" -o "$TAP_NAME" -d 172.31.0.2/32 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    run_as_root iptables -A FORWARD -i "$TAP_NAME" -o "$WAN_IF" -s 172.31.0.2/32 -j ACCEPT
}

WORKDIR="$(mktemp -d)"
trap cleanup EXIT

# O host monta discos separados para entrada, saida e cache; o guest os descobre por markers.
OVERLAY="$WORKDIR/rootfs-overlay.ext4"
INPUT_DISK="$WORKDIR/input.ext4"
OUTPUT_DISK="$WORKDIR/output.ext4"
CACHE_DISK="$WORKDIR/cache.ext4"
SOCKET="$WORKDIR/firecracker.socket"
INPUT_MOUNT="$WORKDIR/input-mount"
OUTPUT_MOUNT="$WORKDIR/output-mount"
CACHE_MOUNT="$WORKDIR/cache-mount"
RESULT_MOUNT="$WORKDIR/result-mount"
STAGING_DIR="$WORKDIR/staging"
SERIAL_LOG="$WORKDIR/serial.log"
REQUEST_BUNDLE_PATH="$WORKDIR/request-bundle.tar.gz"
PACKAGE_DIR="$WORKDIR/response"

cp "$ROOTFS" "$OVERLAY"
mkdir -p "$STAGING_DIR" "$PACKAGE_DIR"
cp "$BUNDLE_PATH" "$REQUEST_BUNDLE_PATH"

dd if=/dev/zero of="$INPUT_DISK" bs=1M count=128 >/dev/null 2>&1
dd if=/dev/zero of="$OUTPUT_DISK" bs=1M count=1024 >/dev/null 2>&1
mkfs.ext4 -q "$INPUT_DISK" 2>/dev/null || true
mkfs.ext4 -q "$OUTPUT_DISK" 2>/dev/null || true

mkdir -p "$INPUT_MOUNT" "$OUTPUT_MOUNT" "$RESULT_MOUNT" "$CACHE_MOUNT"
run_as_root mount -o loop "$INPUT_DISK" "$INPUT_MOUNT"
run_as_root cp "$REQUEST_BUNDLE_PATH" "$INPUT_MOUNT/bundle.tar.gz"
run_as_root sync
run_as_root umount "$INPUT_MOUNT"

run_as_root mount -o loop "$OUTPUT_DISK" "$OUTPUT_MOUNT"
run_as_root touch "$OUTPUT_MOUNT/$OUTPUT_MARKER"
run_as_root mkdir -p "$OUTPUT_MOUNT/wheelhouse"
run_as_root sync
run_as_root umount "$OUTPUT_MOUNT"

if find "$WHEEL_CACHE_SOURCE_DIR" -maxdepth 3 -type f -name '*.whl' -print -quit 2>/dev/null | grep -q .; then
    CACHE_STAGING="$WORKDIR/cache-source"
    mkdir -p "$CACHE_STAGING/wheels"
    cp -R "$WHEEL_CACHE_SOURCE_DIR"/. "$CACHE_STAGING/wheels/"
    create_data_disk_from_dir "$CACHE_STAGING" "$CACHE_DISK" "$WHEEL_CACHE_MARKER"
fi

setup_network

firecracker --api-sock "$SOCKET" >"$SERIAL_LOG" 2>&1 &
FC_PID=$!

for _ in {1..20}; do
    [ -S "$SOCKET" ] && break
    sleep 0.5
done

[ -S "$SOCKET" ] || { emit_error "firecracker socket not created" "$SERIAL_LOG"; exit 1; }

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

# Builder recebe mais CPU/memoria porque pode compilar wheels e resolver dependencias pesadas.
fc_put "machine-config" '{"vcpu_count": 2, "mem_size_mib": 1536, "smt": false}'
fc_put "boot-source" "{\"kernel_image_path\": \"$KERNEL\", \"boot_args\": \"console=ttyS0 loglevel=4 noapic reboot=k panic=1 pci=off nomodules random.trust_cpu=on root=/dev/vda rootfstype=ext4 rootwait rw init=/init\"}"
fc_put "drives/rootfs" "{\"drive_id\": \"rootfs\", \"path_on_host\": \"$OVERLAY\", \"is_root_device\": true, \"is_read_only\": false}"
fc_put "drives/input" "{\"drive_id\": \"input\", \"path_on_host\": \"$INPUT_DISK\", \"is_root_device\": false, \"is_read_only\": true}"
fc_put "drives/output" "{\"drive_id\": \"output\", \"path_on_host\": \"$OUTPUT_DISK\", \"is_root_device\": false, \"is_read_only\": false}"
if [ -f "$CACHE_DISK" ]; then
    fc_put "drives/cache" "{\"drive_id\": \"cache\", \"path_on_host\": \"$CACHE_DISK\", \"is_root_device\": false, \"is_read_only\": true}"
fi
fc_put "network-interfaces/eth0" "{\"iface_id\": \"eth0\", \"guest_mac\": \"$GUEST_MAC\", \"host_dev_name\": \"$TAP_NAME\"}"
fc_put "actions" '{"action_type": "InstanceStart"}'

build_complete=0
# O host considera a execucao finalizada quando o guest escreve um marcador na serial ou encerra.
for ((i=0; i<VM_TIMEOUT_SECONDS; i++)); do
    if grep -q "$COMPLETE_MARKER" "$SERIAL_LOG" 2>/dev/null || \
       grep -q "$COMPLETE_PREFIX" "$SERIAL_LOG" 2>/dev/null || \
       grep -q "$GUEST_HALTED_MARKER" "$SERIAL_LOG" 2>/dev/null; then
        build_complete=1
        break
    fi
    if ! kill -0 "$FC_PID" 2>/dev/null; then
        break
    fi
    sleep 1
done

if [ "$build_complete" -eq 1 ] && kill -0 "$FC_PID" 2>/dev/null; then
    fc_put "actions" '{"action_type": "SendCtrlAltDel"}'
    for ((i=0; i<SHUTDOWN_GRACE_SECONDS; i++)); do
        if ! kill -0 "$FC_PID" 2>/dev/null; then
            break
        fi
        sleep 1
    done
fi

if [ "$build_complete" -eq 1 ] && kill -0 "$FC_PID" 2>/dev/null; then
    kill -TERM "$FC_PID" 2>/dev/null || true
    sleep 2
fi

if [ "$build_complete" -eq 1 ] && kill -0 "$FC_PID" 2>/dev/null; then
    kill -KILL "$FC_PID" 2>/dev/null || true
    wait "$FC_PID" 2>/dev/null || true
fi

if kill -0 "$FC_PID" 2>/dev/null; then
    emit_error "build microVM timed out" "$SERIAL_LOG"
    exit 1
fi

wait "$FC_PID" || true
mount_disk_ro_or_rw "$OUTPUT_DISK" "$RESULT_MOUNT"

BUILD_RESULT_PATH="$RESULT_MOUNT/$BUILD_RESULT_FILE"
[ -f "$BUILD_RESULT_PATH" ] || { emit_error "build result missing" "$SERIAL_LOG"; exit 1; }

if ! python3 - "$BUILD_RESULT_PATH" "$RESULT_MOUNT/$BUILD_STDOUT_FILE" "$RESULT_MOUNT/$BUILD_STDERR_FILE" "$SERIAL_LOG" <<'PY'
import json
import pathlib
import sys

result_path = pathlib.Path(sys.argv[1])
stdout_path = pathlib.Path(sys.argv[2])
stderr_path = pathlib.Path(sys.argv[3])
serial_path = pathlib.Path(sys.argv[4])

payload = json.loads(result_path.read_text(encoding="utf-8"))
if payload.get("returncode") == 0:
    raise SystemExit(0)

print(json.dumps({
    "error": "build microVM failed",
    "buildResult": payload,
    "stdout": stdout_path.read_text(errors="ignore") if stdout_path.is_file() else "",
    "stderr": stderr_path.read_text(errors="ignore") if stderr_path.is_file() else "",
    "firecrackerLog": serial_path.read_text(errors="ignore")[-4000:] if serial_path.is_file() else "",
}))
raise SystemExit(1)
PY
then
    exit 1
fi

cp "$RESULT_MOUNT/$APPLICATION_ARTIFACT_NAME" "$PACKAGE_DIR/$APPLICATION_ARTIFACT_NAME"
cp "$RESULT_MOUNT/$BUILD_RESULT_FILE" "$PACKAGE_DIR/$BUILD_RESULT_FILE"
[ -f "$RESULT_MOUNT/$BUILD_STDOUT_FILE" ] && cp "$RESULT_MOUNT/$BUILD_STDOUT_FILE" "$PACKAGE_DIR/$BUILD_STDOUT_FILE"
[ -f "$RESULT_MOUNT/$BUILD_STDERR_FILE" ] && cp "$RESULT_MOUNT/$BUILD_STDERR_FILE" "$PACKAGE_DIR/$BUILD_STDERR_FILE"
if [ -d "$RESULT_MOUNT/wheelhouse" ]; then
    mkdir -p "$PACKAGE_DIR/wheelhouse"
    find "$RESULT_MOUNT/wheelhouse" -maxdepth 1 -type f -name '*.whl' -exec cp {} "$PACKAGE_DIR/wheelhouse/" \;
fi

# A resposta devolve apenas o artefato final e metadados do build; o estado temporario da app e descartado.
tar -C "$PACKAGE_DIR" -czf "$OUTPUT_BUNDLE_PATH" .
