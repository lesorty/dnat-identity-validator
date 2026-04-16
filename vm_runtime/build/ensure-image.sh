#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ -f "$ROOT/artifacts/vmlinux" ] && [ -f "$ROOT/artifacts/rootfs.ext4" ]; then
    exit 0
fi

mkdir -p "$ROOT/artifacts"
bash "$ROOT/build/build-kernel.sh"
bash "$ROOT/build/build-rootfs.sh"