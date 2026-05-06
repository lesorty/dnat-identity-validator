#!/bin/bash
set -euo pipefail

ROOT="/app"

# Imagem utilizada como base para o builder de microVMs.
ROOTFS="$ROOT/artifacts/rootfs.ext4"
ROOTFS_TARBALL="$ROOT/artifacts/rootfs.tar.gz"
GUEST_INIT_SRC="$ROOT/rootfs/init"
GUEST_RUNNER_SRC="$ROOT/rootfs/runner"
GUEST_HELPER_SRC="$ROOT/guest-tools/build_application_artifact.py"

rebuild_rootfs_from_tarball() {
    local mount_dir

    [ -f "$ROOTFS_TARBALL" ] || {
        echo "Missing rootfs tarball: $ROOTFS_TARBALL" >&2
        return 1
    }

    # Recria um ext4 "limpo" a partir do tarball para evitar depender de uma imagem corrompida em disco.
    rm -f "$ROOTFS"
    dd if=/dev/zero of="$ROOTFS" bs=1M count=1536 >/dev/null 2>&1
    mkfs.ext4 "$ROOTFS" >/dev/null 2>&1

    mount_dir="$(mktemp -d)"
    mount -o loop "$ROOTFS" "$mount_dir"
    tar -xzf "$ROOTFS_TARBALL" -C "$mount_dir"
    mkdir -p "$mount_dir/opt/dnat"
    cp "$GUEST_INIT_SRC" "$mount_dir/init"
    cp "$GUEST_RUNNER_SRC" "$mount_dir/runner"
    cp "$GUEST_HELPER_SRC" "$mount_dir/opt/dnat/build_application_artifact.py"
    sed -i 's/\r$//' "$mount_dir/init" "$mount_dir/runner" "$mount_dir/opt/dnat/build_application_artifact.py"
    chmod +x "$mount_dir/init" "$mount_dir/runner" "$mount_dir/opt/dnat/build_application_artifact.py"
    sync
    umount "$mount_dir"
    rmdir "$mount_dir"
}

validate_rootfs() {
    local mount_dir
    mount_dir="$(mktemp -d)"

    if ! mount -o loop,ro "$ROOTFS" "$mount_dir" 2>/dev/null; then
        rmdir "$mount_dir"
        return 1
    fi

    # O builder exige tres pontos de entrada no guest: `init`, `runner` e helper Python.
    local ok=0
    if [ -x "$mount_dir/init" ] && [ -x "$mount_dir/runner" ] && [ -f "$mount_dir/opt/dnat/build_application_artifact.py" ]; then
        ok=1
    fi

    umount "$mount_dir"
    rmdir "$mount_dir"

    [ "$ok" -eq 1 ]
}

sync_guest_scripts() {
    local mount_dir
    mount_dir="$(mktemp -d)"
    # Sincroniza scripts no rootfs a cada boot do container para facilitar iteracao sem rebuild completo.
    mount -o loop "$ROOTFS" "$mount_dir"
    mkdir -p "$mount_dir/opt/dnat"
    cp "$GUEST_INIT_SRC" "$mount_dir/init"
    cp "$GUEST_RUNNER_SRC" "$mount_dir/runner"
    cp "$GUEST_HELPER_SRC" "$mount_dir/opt/dnat/build_application_artifact.py"
    sed -i 's/\r$//' "$mount_dir/init" "$mount_dir/runner" "$mount_dir/opt/dnat/build_application_artifact.py"
    chmod +x "$mount_dir/init" "$mount_dir/runner" "$mount_dir/opt/dnat/build_application_artifact.py"
    sync
    umount "$mount_dir"
    rmdir "$mount_dir"
}

if [ ! -f "$ROOTFS" ] || ! validate_rootfs; then
    echo "Rebuilding build rootfs artifact from bundled tarball..."
    rebuild_rootfs_from_tarball
fi

echo "Syncing build guest scripts into rootfs..."
sync_guest_scripts

# O processo persistente da CVM builder e uma API HTTP minima; cada build real roda num worker efemero.
exec python3 "$ROOT/builder.py" 5100
