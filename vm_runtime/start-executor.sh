#!/bin/bash
set -euo pipefail

ROOT="/app"
ROOTFS="$ROOT/artifacts/rootfs.ext4"
ROOTFS_TARBALL="$ROOT/artifacts/rootfs.tar.gz"
GUEST_INIT_SRC="$ROOT/rootfs/init"
GUEST_RUNNER_SRC="$ROOT/rootfs/runner"

rebuild_rootfs_from_tarball() {
    local mount_dir

    [ -f "$ROOTFS_TARBALL" ] || {
        echo "Missing rootfs tarball: $ROOTFS_TARBALL" >&2
        return 1
    }

    # Reconstroi o ext4 a partir do tarball empacotado quando a imagem em disco nao esta confiavel.
    rm -f "$ROOTFS"
    dd if=/dev/zero of="$ROOTFS" bs=1M count=512 >/dev/null 2>&1
    mkfs.ext4 "$ROOTFS" >/dev/null 2>&1

    mount_dir="$(mktemp -d)"
    mount -o loop "$ROOTFS" "$mount_dir"
    tar -xzf "$ROOTFS_TARBALL" -C "$mount_dir"
    cp "$GUEST_INIT_SRC" "$mount_dir/init"
    cp "$GUEST_RUNNER_SRC" "$mount_dir/runner"
    sed -i 's/\r$//' "$mount_dir/init" "$mount_dir/runner"
    chmod +x "$mount_dir/init" "$mount_dir/runner"
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

    # O guest executora precisa apenas de `init` e `runner`.
    local ok=0
    if [ -x "$mount_dir/init" ] && [ -x "$mount_dir/runner" ]; then
        ok=1
    fi

    umount "$mount_dir"
    rmdir "$mount_dir"

    [ "$ok" -eq 1 ]
}

sync_guest_scripts() {
    local mount_dir
    mount_dir="$(mktemp -d)"
    # Permite iterar nos scripts do guest sem refazer toda a imagem Docker do executor.
    mount -o loop "$ROOTFS" "$mount_dir"
    cp "$GUEST_INIT_SRC" "$mount_dir/init"
    cp "$GUEST_RUNNER_SRC" "$mount_dir/runner"
    sed -i 's/\r$//' "$mount_dir/init" "$mount_dir/runner"
    chmod +x "$mount_dir/init" "$mount_dir/runner"
    sync
    umount "$mount_dir"
    rmdir "$mount_dir"
}

if [ ! -f "$ROOTFS" ] || ! validate_rootfs; then
    echo "Rebuilding rootfs artifact from bundled tarball..."
    rebuild_rootfs_from_tarball
fi

echo "Syncing guest scripts into rootfs..."
sync_guest_scripts

# O container executor permanece como API HTTP; cada chamada `/execute` sobe uma microVM nova.
exec python3 "$ROOT/executor.py" 5000
