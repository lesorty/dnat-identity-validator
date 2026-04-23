.PHONY: help setup build build-kernel build-rootfs test clean diagnose

help:
	@echo "🔧 DNAT VM Runtime - Build Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup & Build:"
	@echo "  make setup              Install dependencies (one-time)"
	@echo "  make build              Build kernel + rootfs (~30-40 min)"
	@echo "  make build-kernel       Build Linux 6.6 kernel only (~20-30 min)"
	@echo "  make build-rootfs       Build Ubuntu rootfs only (~5-10 min)"
	@echo ""
	@echo "Run:"
	@echo "  make run-server         Start HTTP executor (port 5000)"
	@echo "  make test-local         Test with quick bundle"
	@echo ""
	@echo "Maintenance:"
	@echo "  make diagnose           Check system & environment"
	@echo "  make clean              Remove build artifacts"
	@echo "  make clean-all          Remove artifacts + kernel cache"
	@echo ""
	@echo "Docker (automatic full build):"
	@echo "  make docker-build       Build Docker image with kernel+rootfs (~40-50 min)"
	@echo "  make docker-run         Run executor server (port 5000)"
	@echo "  make docker-run-shell   Run Docker shell for debugging"
	@echo ""

# Setup environment
setup:
	@echo "📦 Installing dependencies..."
	bash setup-local.sh

# Build targets
build: build-kernel build-rootfs
	@echo "✅ Build complete!"
	ls -lh artifacts/

build-kernel:
	@echo "🔨 Building Linux 6.6 kernel..."
	@echo "   Cores: $$(nproc) | Time: ~20-30 min"
	bash build/build-kernel.sh

build-rootfs: artifacts/vmlinux
	@echo "📦 Building Ubuntu Jammy rootfs..."
	@echo "   Time: ~5-10 min"
	bash build/build-rootfs.sh

ensure-artifacts:
	bash build/ensure-image.sh

# Run targets
run-server: ensure-artifacts
	@echo "🚀 Starting DNAT VM Runtime executor..."
	@echo "   Listening on http://localhost:5000/execute"
	@echo "   POST binary bundle -> get JSON result"
	python3 executor.py 5000

run-server-bg: ensure-artifacts
	@echo "🚀 Starting executor in background..."
	python3 executor.py 5000 &
	@sleep 2
	@echo "✅ Ready at http://localhost:5000/execute"

test-local: run-server-bg
	@echo ""
	@echo "📝 Testing with demo bundle..."
	@mkdir -p test-bundle/workspace
	@echo '#!/bin/bash' > test-bundle/workspace/run.sh
	@echo 'echo "Hello from VM"' >> test-bundle/workspace/run.sh
	@chmod +x test-bundle/workspace/run.sh
	@cd test-bundle && tar -czf bundle.tar.gz workspace/
	@curl -X POST --data-binary @test-bundle/bundle.tar.gz http://localhost:5000/execute | jq .
	@echo ""
	@echo "✅ Test complete!"
	@pkill -f "python3 executor.py" || true
	@rm -rf test-bundle

# Diagnostic tools
diagnose:
	bash diagnose.sh

docker-build:
	@echo "🐳 Building Docker image with full build..."
	docker build -f Dockerfile.build -t dnat-executor:latest .
	@echo "✅ Image built: dnat-executor:latest"

docker-run:
	@echo "🐳 Running executor server..."
	docker run -p 5000:5000 dnat-executor:latest

docker-run-shell:
	@echo "🐳 Running in Docker shell..."
	docker run -it dnat-executor:latest /bin/bash

# Cleanup
clean:
	@echo "🧹 Cleaning..."
	rm -rf input/* output/* run-vm.sh.lock
	@echo "✅ Cleaned temporary files"

clean-all: clean
	@echo "🔥 Removing all build artifacts..."
	rm -rf artifacts/ /tmp/linux /tmp/firecracker-rootfs
	@echo "⚠️  You'll need to rebuild: make build"

.PHONY: help setup build build-kernel build-rootfs test-local run-server diagnose clean clean-all
