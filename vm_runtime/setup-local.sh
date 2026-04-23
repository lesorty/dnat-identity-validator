#!/bin/bash
# Setup local environment for DNAT VM Runtime (no Docker required)
# This script installs all dependencies and prepares the system

set -e

echo "🔧 DNAT VM Runtime - Local Setup"
echo "================================"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on Linux
if [[ ! "$OSTYPE" == "linux-gnu"* ]]; then
    log_error "This script requires Linux. Detected: $OSTYPE"
    exit 1
fi

log_info "Detecting distro..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
    VERSION=$VERSION_ID
    log_info "Detected: $PRETTY_NAME"
else
    log_error "Cannot detect Linux distro"
    exit 1
fi

# Check if running with sudo for this session
if [ "$EUID" -ne 0 ] && ! sudo -n true 2>/dev/null; then
    log_warn "Some commands require sudo. You may be prompted for your password."
fi

# Update package manager
log_info "Updating package manager..."
sudo apt-get update || true

# Install build essentials
log_info "Installing build essentials..."
sudo apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    python3 \
    python3-pip \
    debootstrap \
    qemu-utils \
    sudo

# Install Linux kernel build dependencies
log_info "Installing Linux kernel build dependencies..."
sudo apt-get install -y \
    flex \
    bison \
    libncurses-dev \
    libssl-dev \
    bc \
    libelf-dev \
    libdw-dev \
    pkg-config \
    libpython3-dev

# Install Firecracker
log_info "Installing Firecracker v1.7.0..."
FC_VERSION="1.7.0"
FC_BIN="/usr/local/bin/firecracker"

if command -v firecracker &> /dev/null; then
    CURRENT_FC_VERSION=$(firecracker --version 2>/dev/null | awk '{print $2}' || echo "unknown")
    if [ "$CURRENT_FC_VERSION" = "$FC_VERSION" ]; then
        log_warn "Firecracker $FC_VERSION already installed"
    else
        log_warn "Firecracker version mismatch. Current: $CURRENT_FC_VERSION, Required: $FC_VERSION"
    fi
else
    mkdir -p /tmp/fc-download
    cd /tmp/fc-download
    
    log_info "Downloading Firecracker..."
    curl -sL https://github.com/firecracker-microvm/firecracker/releases/download/v${FC_VERSION}/firecracker-v${FC_VERSION}-x86_64.tgz | tar -xz
    
    log_info "Installing Firecracker binary..."
    sudo mv release-v${FC_VERSION}-x86_64/firecracker-v${FC_VERSION}-x86_64 "$FC_BIN"
    sudo chmod +x "$FC_BIN"
    
    rm -rf /tmp/fc-download
    log_info "✓ Firecracker installed"
fi

# Create necessary directories
log_info "Creating necessary directories..."
# Define ROOT early (before changing directories)
ROOT="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$ROOT/artifacts"
mkdir -p "$ROOT/input"
mkdir -p "$ROOT/output"

# Export ROOT so child scripts use correct path
export ROOT

# Verify Firecracker installation
log_info "Verifying Firecracker installation..."
if firecracker --version; then
    log_info "✓ Firecracker ready"
else
    log_error "Firecracker verification failed"
    exit 1
fi

# Show build time estimation
echo ""
echo "📋 Build Time Estimation:"
echo "  - Linux Kernel 6.6: ~20-30 minutes (parallel: ~nproc=$(nproc) cores)"
echo "  - Ubuntu Rootfs: ~5-10 minutes"
echo "  - Total: ~30-40 minutes"
echo ""

# Ask if user wants to start build
read -p "Start building kernel and rootfs now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Starting build process..."
    log_info "Building Linux kernel (this will take a while)..."
    bash "$ROOT/build/build-kernel.sh" || log_error "Kernel build failed"
    
    log_info "Building Ubuntu rootfs..."
    bash "$ROOT/build/build-rootfs.sh" || log_error "Rootfs build failed"
    
    log_info "✓ Build complete!"
    echo ""
    echo "✅ Setup complete! You can now run:"
    echo "   python3 executor.py 5000"
else
    log_info "Build skipped. You can start it manually with:"
    echo "  bash $ROOT/build/ensure-image.sh"
    echo "  bash $ROOT/setup-runtime.sh"
fi

log_info "✅ Setup complete!"
