#!/bin/bash
set -e

sudo apt update
sudo apt install -y curl qemu-utils

FC_VERSION="1.7.0"
curl -sL https://github.com/firecracker-microvm/firecracker/releases/download/v${FC_VERSION}/firecracker-v${FC_VERSION}-x86_64.tgz | tar -xz
sudo mv release-v${FC_VERSION}-x86_64/firecracker-v${FC_VERSION}-x86_64 /usr/local/bin/firecracker
sudo chmod +x /usr/local/bin/firecracker

mkdir -p build input output