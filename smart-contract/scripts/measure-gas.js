// Measures gasUsed for the DNAT marketplace user journey:
//   registerAsset(Dataset) + registerAsset(Application) + purchaseAccess
// Run: npx hardhat run scripts/measure-gas.js
// Deterministic: deploys a fresh contract on the in-process hardhat network.
// Same control plane is shared by M0/A/B, so these numbers apply to all three.
const hre = require("hardhat");

async function main() {
  const ethers = hre.ethers;
  const [provider, buyer] = await ethers.getSigners();

  const Factory = await ethers.getContractFactory("DnatMarketplace");
  const mkt = await Factory.deploy();
  await mkt.waitForDeployment();

  // Representative inputs mirroring api-server.js registerAsset():
  //   assetUri/manifestUri = "ipfs://<CIDv0>" (53 chars), contentHash = bytes32,
  //   bloomFilter = "0x" (common case; contract stores it only for datasets).
  const cidUri = "ipfs://QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"; // 53 chars
  const contentHash = ethers.keccak256(ethers.toUtf8Bytes("plaintext-asset-sha256"));
  const datasetPrice = ethers.parseEther("0.01");
  const appPrice = ethers.parseEther("0.005");

  // 1) register dataset (AssetType.Dataset = 0), empty bloom filter
  const r1 = await (await mkt.connect(provider).registerAsset(
    0, "Synthetic Customers 60", "Synthetic customer dataset, 60 rows",
    cidUri, cidUri, contentHash, datasetPrice, "0x"
  )).wait();

  // 1b) same dataset register but WITH a 256-byte bloom filter (to show scaling)
  const bloom256 = "0x" + "ab".repeat(256);
  const r1b = await (await mkt.connect(provider).registerAsset(
    0, "Synthetic Customers 60", "Synthetic customer dataset, 60 rows",
    cidUri, cidUri, contentHash, datasetPrice, bloom256
  )).wait();

  // 2) register application (AssetType.Application = 1), bloom ignored for apps
  const r2 = await (await mkt.connect(provider).registerAsset(
    1, "Mean Aggregator", "Computes per-column means",
    cidUri, cidUri, contentHash, appPrice, "0x"
  )).wait();

  // datasetId = 1 (the empty-bloom one), applicationId = 3 (nextAssetId increments per call)
  // 3) purchase access: buyer pays dataset+app price to the provider
  const total = datasetPrice + appPrice;
  const r3 = await (await mkt.connect(buyer).purchaseAccess(1, 3, { value: total })).wait();

  const g = (r) => r.gasUsed.toString();
  console.log("RESULT register_dataset_bloom0x    =", g(r1));
  console.log("RESULT register_dataset_bloom256B  =", g(r1b));
  console.log("RESULT register_application        =", g(r2));
  console.log("RESULT purchase_access             =", g(r3));
  console.log("RESULT total_regDataset_regApp_buy =", (r1.gasUsed + r2.gasUsed + r3.gasUsed).toString());
  console.log("RESULT total_regDataset_buy        =", (r1.gasUsed + r3.gasUsed).toString());
}

main().catch((e) => { console.error(e); process.exit(1); });
