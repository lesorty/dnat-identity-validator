#!/usr/bin/env bash
set -e

IMAGE=build/rootfs.img
ROOTFS=build/rootfs

SIZE=512M

qemu-img create -f qcow2 $IMAGE $SIZE

mkfs.ext4 $IMAGE

mkdir -p build/mount

sudo mount -o loop $IMAGE build/mount

sudo cp -r $ROOTFS/* build/mount/

sudo umount build/mount