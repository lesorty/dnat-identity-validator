// Measures gasUsed for the DNAT marketplace user journey:
//   registerAsset(Dataset) + registerAsset(Application) + purchaseAccess
// and, for the derivative receipt (T-709): registerAsset(Model), registerDerivative (approved and
// rejected), revokeDerivative. Writes results/gas.{json,md} besides the RESULT lines.
// Run: npx hardhat run scripts/measure-gas.js
// Deterministic: deploys a fresh contract on the in-process hardhat network.
// Same control plane is shared by M0/A/B, so these numbers apply to all three.
const hre = require("hardhat");

async function main() {
  const ethers = hre.ethers;
  const [provider, buyer] = await ethers.getSigners();

  const Factory = await ethers.getContractFactory("DnatMarketplace");
  const mkt = await Factory.deploy(provider.address); // operador (T-703); não entra na jornada medida
  await mkt.waitForDeployment();

  // Representative inputs mirroring api-server.js registerAsset():
  //   assetUri/manifestUri = "ipfs://<CIDv0>" (53 chars), contentHash = bytes32,
  //   bloomFilter = "0x" (common case; contract stores it only for datasets).
  const cidUri = "ipfs://QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG";
  const otherUri = (k) => cidUri.slice(0, -1) + String(k); // 53 chars
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
  // URI do mesmo tamanho, mas outro: o contrato recusa URI de dataset ou aplicação repetido.
  const r1b = await (await mkt.connect(provider).registerAsset(
    0, "Synthetic Customers 60", "Synthetic customer dataset, 60 rows",
    otherUri(1), cidUri, contentHash, datasetPrice, bloom256
  )).wait();

  // 2) register application (AssetType.Application = 1), bloom ignored for apps
  const r2 = await (await mkt.connect(provider).registerAsset(
    1, "Mean Aggregator", "Computes per-column means",
    otherUri(2), cidUri, contentHash, appPrice, "0x"
  )).wait();

  // datasetId = 1 (the empty-bloom one), applicationId = 3 (nextAssetId increments per call)
  // 3) purchase access: buyer pays dataset+app price to the provider
  const total = datasetPrice + appPrice;
  const r3 = await (await mkt.connect(buyer).purchaseAccess(1, 3, { value: total })).wait();

  // 4) receipt path (T-709): custodied parent model, two derivatives, operator revocation.
  //    The deployer is the operator here (constructor arg), as the CVM1 is in the real flow.
  const r4 = await (await mkt.connect(provider).registerAsset(
    2, "Qwen2.5-0.5B-Instruct", "Base model deposited by the operator",
    cidUri, cidUri, contentHash, 0, "0x"
  )).wait();
  const parentId = await mkt.nextAssetId();
  const h = (s) => ethers.keccak256(ethers.toUtf8Bytes(s));
  const info = (verdict) => ({
    parentId, parentReferenceHash: h("ref"), derivativeHash: h(`der-${verdict}`), judgeHash: h("judge"),
    batteryCommitment: h("battery"), preregHash: h("prereg"), datasetHash: h("dataset"),
    verdictHash: h(`verdict-${verdict}`), identityId: h("identity"), verdict, decidedAt: 1_794_528_000n,
  });
  // Title as the api-server writes it: "Derivado de <parent title> (<executionId>)".
  const title = "Derivado de Qwen2.5-0.5B-Instruct (20261113T120000Z_0a1b2c3d)";
  const r5 = await (await mkt.connect(provider).registerDerivative(info(1), buyer.address, title, cidUri)).wait(); // Approved = 1
  const approvedId = await mkt.nextAssetId();
  const r6 = await (await mkt.connect(provider).registerDerivative(info(2), buyer.address, title, cidUri)).wait(); // Rejected = 2
  const r7 = await (await mkt.connect(provider).revokeDerivative(approvedId, "judge-version-changed")).wait();

  const g = (r) => r.gasUsed.toString();
  console.log("RESULT register_dataset_bloom0x    =", g(r1));
  console.log("RESULT register_dataset_bloom256B  =", g(r1b));
  console.log("RESULT register_application        =", g(r2));
  console.log("RESULT purchase_access             =", g(r3));
  console.log("RESULT total_regDataset_regApp_buy =", (r1.gasUsed + r2.gasUsed + r3.gasUsed).toString());
  console.log("RESULT total_regDataset_buy        =", (r1.gasUsed + r3.gasUsed).toString());
  console.log("RESULT register_model              =", g(r4));
  console.log("RESULT register_derivative_approved =", g(r5));
  console.log("RESULT register_derivative_rejected =", g(r6));
  console.log("RESULT revoke_derivative           =", g(r7));

  const rows = [
    ["registerAsset (dataset, bloom vazio)", r1], ["registerAsset (dataset, bloom 256 B)", r1b],
    ["registerAsset (aplicação)", r2], ["purchaseAccess", r3], ["registerAsset (modelo base)", r4],
    ["registerDerivative (recibo, aprovado)", r5], ["registerDerivative (recibo, reprovado)", r6],
    ["revokeDerivative", r7],
  ].map(([fn, r]) => ({ fn, gasUsed: Number(r.gasUsed) }));
  const fs = require("node:fs");
  const path = require("node:path");
  const dir = path.join(__dirname, "..", "results");
  fs.mkdirSync(dir, { recursive: true });
  const meta = { note: "gasUsed na rede hardhat em processo (determinístico para as mesmas entradas); "
    + "o número citado no artigo sai da execução na nuvem (T-709, fase de testes).",
    hardhat: require("hardhat/package.json").version, solc: hre.config.solidity.compilers?.[0]?.version || hre.config.solidity.version,
    measuredAtUtc: new Date().toISOString() };
  fs.writeFileSync(path.join(dir, "gas.json"), JSON.stringify({ ...meta, rows }, null, 2) + "\n");
  fs.writeFileSync(path.join(dir, "gas.md"), `# Gás por função do DnatMarketplace (T-709)\n\n${meta.note}\n\n`
    + `Hardhat ${meta.hardhat} · solc ${meta.solc}\n\n| Função | gasUsed |\n|---|---|\n`
    + rows.map((r) => `| ${r.fn} | ${r.gasUsed.toLocaleString("en-US")} |`).join("\n") + "\n");
}

main().catch((e) => { console.error(e); process.exit(1); });
