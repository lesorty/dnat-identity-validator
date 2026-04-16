#!/usr/bin/env bash
set -e

echo "Installing runtime dependencies"

sudo apt update

sudo apt install -y \
    curl \
    qemu-utils \
    iproute2 \
    iptables

echo "Installing Firecracker"

FC_VERSION="1.7.0"

curl -LO https://github.com/firecracker-microvm/firecracker/releases/download/v${FC_VERSION}/firecracker-v${FC_VERSION}-x86_64.tgz

tar -xvf firecracker-v${FC_VERSION}-x86_64.tgz

sudo mv release-v${FC_VERSION}-x86_64/firecracker-v${FC_VERSION}-x86_64 /usr/local/bin/firecracker

sudo chmod +x /usr/local/bin/firecracker

echo "Creating directories"

mkdir -p build
mkdir -p input
mkdir -p output

echo "Runtime ready"