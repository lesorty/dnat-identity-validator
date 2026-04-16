# DNAT CLI Minimal Setup

This repository now contains only the parts needed to run the smart-contract CLI with:
- Hardhat local blockchain
- IPFS node

## Run

```powershell
cd executor
docker compose up -d hardhat ipfs

cd ..\smart-contract
npm install
npm run deploy:localhost
npm run cli
```

## Required `.env` (`smart-contract/.env`)

```env
RPC_URL=http://127.0.0.1:8545
PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
IPFS_API_URL=http://localhost:5001
CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
EXECUTOR_URL=http://localhost:8081
```

`EXECUTOR_URL` is optional if you are not using option 10/11 in the CLI.

## Web frontend (React + simple API)

From `smart-contract`:

```powershell
npm install
npm run web
```

Open:
- `http://localhost:3001/` for CLI functions UI
- `http://localhost:3001/assets.html` for available assets (datasets/apps split)
- `http://localhost:3001/executions.html` for execution results (`stdout/stderr/metadata/result`)


# Execute the VM_Runtime
## Build Environment
- docker build -t vm-builder -f Dockerfile.build .

## Open Container
- docker build -t vm-builder -f Dockerfile.build .

## Build VM
- bash build/build-kernel.sh
- bash build/build-rootfs.sh
- bash build/build-image.sh

## Design Security Properties:
rootfs.img -> imutable, base image

overlay-UUID.qcow2 -> mutable instance to be runned

