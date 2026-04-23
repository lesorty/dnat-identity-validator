#!/bin/bash
# Diagnostic tool for DNAT VM Runtime environment

echo "🔍 DNAT VM Runtime - Environment Diagnostic"
echo "==========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_command() {
    local cmd=$1
    local display_name=${2:-$cmd}
    
    if command -v "$cmd" &> /dev/null; then
        local version=$("$cmd" --version 2>&1 | head -n 1)
        echo -e "${GREEN}✓${NC} $display_name: $version"
        return 0
    else
        echo -e "${RED}✗${NC} $display_name: NOT FOUND"
        return 1
    fi
}

check_file() {
    local file=$1
    local display_name=${2:-$file}
    
    if [ -f "$file" ]; then
        local size=$(du -h "$file" | cut -f1)
        echo -e "${GREEN}✓${NC} $display_name: $size"
        return 0
    else
        echo -e "${RED}✗${NC} $display_name: NOT FOUND"
        return 1
    fi
}

echo "📦 Required Commands:"
check_command "gcc" "GCC"
check_command "git" "Git"
check_command "curl" "Curl"
check_command "python3" "Python3"
check_command "debootstrap" "Debootstrap"
check_command "qemu-img" "QEMU Utils"
check_command "firecracker" "Firecracker"
check_command "mkfs.ext4" "mkfs.ext4"

echo ""
echo "📁 Build Artifacts:"
ROOT="$(cd "$(dirname "$0")" && pwd)"
check_file "$ROOT/artifacts/vmlinux" "Linux Kernel"
check_file "$ROOT/artifacts/rootfs.ext4" "Ubuntu Rootfs"

echo ""
echo "💾 Required Packages (apt):"
apt-cache policy build-essential 2>/dev/null | grep "Installed:" | grep -q "0.0" && \
    echo -e "${RED}✗${NC} build-essential: not installed" || \
    echo -e "${GREEN}✓${NC} build-essential: installed"

apt-cache policy linux-headers-generic 2>/dev/null | grep "Installed:" | grep -q "0.0" && \
    echo -e "${YELLOW}⚠${NC} linux-headers-generic: optional" || \
    echo -e "${GREEN}✓${NC} linux-headers-generic: installed"

echo ""
echo "🖥️  System Info:"
echo "  CPU cores: $(nproc)"
echo "  Total RAM: $(free -h | awk 'NR==2 {print $2}')"

FREE_SPACE=$(df -h "$ROOT" 2>/dev/null | awk 'NR==2 {print $4}')
REQUIRED_SPACE="40GB (kernel ~3GB, rootfs ~1GB, working space ~36GB)"
echo "  Available space: $FREE_SPACE"
echo "  Required space: $REQUIRED_SPACE at $ROOT"

echo ""
echo "⚙️  Build Status:"
if [ -f "$ROOT/artifacts/vmlinux" ] && [ -f "$ROOT/artifacts/rootfs.ext4" ]; then
    echo -e "${GREEN}✓${NC} Ready to run executor"
    echo "  Run: python3 executor.py 5000"
else
    echo -e "${YELLOW}⚠${NC} Build artifacts missing"
    echo "  Run: bash setup-local.sh"
fi

echo ""
echo "📋 Common Issues:"
echo ""
echo "Issue: 'Command not found: firecracker'"
echo "  Fix: bash setup-local.sh"
echo ""
echo "Issue: 'kernel or rootfs not found'"
echo "  Fix: bash build/ensure-image.sh"
echo ""
echo "Issue: 'Permission denied'"
echo "  Fix: sudo bash build/ensure-image.sh"
echo ""
echo "Issue: Build too slow"
echo "  Tips: 
    - Use: make -j\$(nproc) for parallel builds
    - Check CPU load: top
    - Increase RAM if available
    - Run at off-peak hours if on VM"
