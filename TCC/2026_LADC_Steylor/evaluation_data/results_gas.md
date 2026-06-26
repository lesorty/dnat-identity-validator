# DNAT — Blockchain gas (registerAsset / purchaseAccess)

> Measured on **2026-06-23** with `smart-contract/scripts/measure-gas.js`
> (`npx hardhat run`). These numbers fill the last measurable row of
> `tab:comparison`. They are **identical across M0/A/B**: the on-chain registry is
> the shared control plane, and isolation (microVM, plane separation) lives in the
> build/execution planes, not in the contract — so the gas cost of the user
> journey does not depend on the isolation architecture.

## Method

| Item | Value |
|------|-------|
| Contract | `DnatMarketplace.sol` (`registerAsset`, `purchaseAccess`) |
| Toolchain | Hardhat in-process network, ethers v6 |
| Compiler | solc 0.8.20, `viaIR: true`, optimizer enabled, `runs: 200` |
| Deploy | fresh `DnatMarketplace` (no constructor args) per run |
| `gasUsed` source | transaction receipt (`receipt.gasUsed`) |
| Accounts | provider registers; a distinct buyer purchases |

**Representative inputs** (mirroring `api-server.js registerAsset()`):
`encryptedUri = manifestUri = "ipfs://<CIDv0>"` (53 chars), `contentHash`
= a `bytes32`, `price` non-zero, `bloomFilter = "0x"` for the headline case
(the common path; the contract stores the filter only for datasets).

## Results (gasUsed)

| Operation | gasUsed |
|-----------|--------:|
| `registerAsset` — dataset, bloom `0x` | 388,712 |
| `registerAsset` — dataset, bloom 256 B | 573,219 |
| `registerAsset` — application | 326,567 |
| `purchaseAccess` | 96,537 |
| Journey: reg(dataset)+reg(app)+purchase | 811,816 |
| Journey: reg(dataset)+purchase | 485,249 |

**Notes.**
- A dataset's on-chain bloom filter adds ≈ **185k gas per 256 bytes**
  (≈ 721 gas/byte = `SSTORE` of new words), so dataset registration cost grows
  with filter size; the headline 388.7k is the empty-filter base.
- `purchaseAccess` is much cheaper (96.5k): one `accessRights` `SSTORE`, two
  value transfers to the owners, and the `AccessPurchased` event.
- `registerAsset` dominates because it persists six fields (title, description,
  two IPFS URIs, content hash, price) plus the optional filter.

## Illustrative monetary cost

Gas is the EVM's unit of work and is deterministic; the fiat cost is
`gasUsed × gasPrice(gwei) × 1e-9 × ETH_USD` and floats with the network. Anchor:
a plain ETH transfer is 21,000 gas, so `purchaseAccess` (96.5k) ≈ 4.6 transfers
and `registerAsset` (388.7k) ≈ 18.5 transfers.

Illustrative, with **ETH = US\$3,000**:

| Network | gas price | `registerAsset` | `purchaseAccess` |
|---------|-----------|----------------:|-----------------:|
| Ethereum L1 | 15 gwei | ≈ US\$17.5 | ≈ US\$4.3 |
| **Layer-2 (Base/Arbitrum)** | **0.03 gwei** | **≈ US\$0.035** | **< US\$0.01** |

The paper reports the **L2** figure (the realistic deployment for a data
marketplace); L1 is shown only to bound the range. These assumptions are stated
explicitly in `tab:comparison` (footnote §) and the Operational Cost prose.

## What this fills in the paper

- `tab:comparison`, row *On-chain gas (register / purchase)*: 389k / 97k for
  M0/A/B (identical), `---` for the SGX reference column.
- Remaining matrix gap: the SGX column numbers, cited from the original DNAT work.
