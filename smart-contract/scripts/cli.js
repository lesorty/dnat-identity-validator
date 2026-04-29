const { ethers } = require("hardhat");
const readline = require("node:readline/promises");
const { stdin: input, stdout: output } = require("node:process");
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { spawn } = require("node:child_process");

const RPC_URL = process.env.RPC_URL || "http://127.0.0.1:8545";
const PRIVATE_KEY =
  process.env.PRIVATE_KEY ||
  "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
const CONTRACT_ADDRESS_ENV = process.env.CONTRACT_ADDRESS;
const IPFS_API_URL = process.env.IPFS_API_URL || "http://localhost:5001";

const abi = [
  "function registerAsset(uint8 assetType, string title, string description, string encryptedUri, string manifestUri, bytes32 contentHash, uint256 price, bytes bloomFilter) returns (uint256)",
  "function purchaseAccess(uint256 datasetId, uint256 applicationId) payable",
  "function getAsset(uint256 assetId) view returns (uint8 assetType, address owner, string title, string description, string encryptedUri, string manifestUri, bytes32 contentHash, uint256 price, bytes bloomFilter, bool active)",
  "function nextAssetId() view returns (uint256)",
  "function hasAccess(address user, string encryptedDatasetHash, string encryptedApplicationHash) view returns (bool)",
  "function hasAccessByIds(address user, uint256 datasetId, uint256 applicationId) view returns (bool)",
  "function updateAsset(uint256 assetId, uint256 newPrice, bool newActive)",
  "function revokeAsset(uint256 assetId)",
  "event AssetRegistered(uint256 indexed id, uint8 assetType, address indexed owner, uint256 price, bool hasBloomFilter)",
  "event AccessPurchased(uint256 indexed datasetId, uint256 indexed applicationId, address indexed user, uint256 datasetPrice, uint256 applicationPrice)",
];

const provider = new ethers.JsonRpcProvider(RPC_URL);
const wallet = new ethers.Wallet(PRIVATE_KEY, provider);
let contractAddress =
  CONTRACT_ADDRESS_ENV || "0x5FbDB2315678afecb367f032d93F642f64180aa3";
let contract = new ethers.Contract(contractAddress, abi, wallet);

function resolvePythonBin(pythonBin) {
  const requested = String(pythonBin || "").trim();
  if (requested && requested.toLowerCase() !== "python") return requested;

  const repoPython = path.resolve(
    __dirname,
    "..",
    "..",
    ".venv",
    "Scripts",
    "python.exe",
  );
  if (fs.existsSync(repoPython)) return repoPython;

  return requested || "python";
}

async function resolveContractAddress() {
  if (CONTRACT_ADDRESS_ENV) {
    const code = await provider.getCode(CONTRACT_ADDRESS_ENV);
    if (code && code !== "0x") return CONTRACT_ADDRESS_ENV;
  }

  const deploymentPath = path.join(
    __dirname,
    "..",
    "deployments",
    "localhost.json",
  );
  if (fs.existsSync(deploymentPath)) {
    const deployment = JSON.parse(fs.readFileSync(deploymentPath, "utf8"));
    if (deployment.contractAddress) return deployment.contractAddress;
  }

  return contractAddress;
}

async function initContract() {
  contractAddress = await resolveContractAddress();
  contract = new ethers.Contract(contractAddress, abi, wallet);
}

async function prompt(rl, label) {
  try {
    return (await rl.question(`${label}: `)).trim();
  } catch (e) {
    if (e && e.code === "ERR_USE_AFTER_CLOSE") return "0";
    throw e;
  }
}

async function promptUserAddress(rl) {
  const raw = await prompt(rl, "User address (empty = signer)");
  const user = raw || wallet.address;
  if (/^0x[0-9a-fA-F]{64}$/.test(user)) {
    console.log(
      "That looks like a transaction hash. Use a wallet address (0x...40 hex chars).",
    );
    return null;
  }
  if (!ethers.isAddress(user)) {
    console.log("Invalid wallet address:", user);
    return null;
  }
  return ethers.getAddress(user);
}

async function promptAssetId(rl, label) {
  const raw = await prompt(rl, label);
  if (!/^\d+$/.test(raw)) {
    if (raw.startsWith("ipfs://")) {
      console.log(
        `${label} must be numeric for this option. Use option 6 (Check Access by URIs) for ipfs:// values.`,
      );
    } else {
      console.log(`${label} must be a numeric asset id (example: 1, 2, 3).`);
    }
    return null;
  }
  return BigInt(raw);
}

async function registerAsset(rl, assetType) {
  const uploaded = await addFileToIpfsFlow(rl);
  if (!uploaded) return;

  const priceWei = await prompt(rl, "Price in wei");
  const title =
    (await prompt(
      rl,
      `Asset title (default: ${path.basename(uploaded.localPath)})`,
    )) || path.basename(uploaded.localPath);
  const description = await prompt(rl, "Asset description (optional)");
  const bloom =
    assetType === 0
      ? await prompt(rl, "Bloom filter hex (0x... or empty)")
      : "";

  const tx = await contract.registerAsset(
    assetType,
    title,
    description,
    uploaded.assetUri,
    uploaded.manifestUri,
    uploaded.assetContentHash,
    BigInt(priceWei || "0"),
    bloom ? bloom : "0x",
  );
  const receipt = await tx.wait();
  let createdAssetId = null;
  for (const log of receipt.logs || []) {
    try {
      const parsed = contract.interface.parseLog(log);
      if (parsed && parsed.name === "AssetRegistered") {
        createdAssetId = parsed.args.id;
        break;
      }
    } catch {
      // ignore logs from other contracts
    }
  }
  if (createdAssetId === null) {
    const nextAssetId = await contract.nextAssetId();
    createdAssetId = nextAssetId > 0n ? nextAssetId - 1n : 0n;
  }

  const onChainAsset = await contract.getAsset(createdAssetId);
  console.log({
    assetCid: uploaded.assetCid,
    assetUri: uploaded.assetUri,
    assetContentHash: uploaded.assetContentHash,
    manifestCid: uploaded.manifestCid,
    manifestUri: uploaded.manifestUri,
    manifestContentHash: uploaded.manifestContentHash,
    registeredTx: receipt.hash,
    assetId: createdAssetId.toString(),
    onChainAsset: {
      assetType: Number(onChainAsset.assetType),
      owner: onChainAsset.owner,
      title: onChainAsset.title,
      description: onChainAsset.description,
      encryptedUri: onChainAsset.encryptedUri,
      manifestUri: onChainAsset.manifestUri,
      contentHash: onChainAsset.contentHash,
      priceWei: onChainAsset.price.toString(),
      bloomFilter: onChainAsset.bloomFilter,
      active: onChainAsset.active,
    },
  });
}

async function purchaseAccess(rl) {
  const datasetId = await promptAssetId(rl, "Dataset ID");
  if (datasetId === null) return;
  const applicationId = await promptAssetId(rl, "Application ID");
  if (applicationId === null) return;

  const dataset = await contract.getAsset(datasetId);
  const app = await contract.getAsset(applicationId);
  const total = dataset.price + app.price;

  const tx = await contract.purchaseAccess(datasetId, applicationId, {
    value: total,
  });
  const receipt = await tx.wait();
  console.log("purchase tx:", receipt.hash);
  console.log("total paid (wei):", total.toString());
}

async function getAsset(rl) {
  const assetId = await prompt(rl, "Asset ID");
  if (/^0x[0-9a-fA-F]{64}$/.test(assetId)) {
    console.log(
      "That looks like a transaction hash. Use the numeric asset id (example: 1, 2, 3).",
    );
    return;
  }
  const a = await contract.getAsset(BigInt(assetId));
  console.log({
    assetType: Number(a.assetType),
    owner: a.owner,
    title: a.title,
    description: a.description,
    encryptedUri: a.encryptedUri,
    manifestUri: a.manifestUri,
    contentHash: a.contentHash,
    priceWei: a.price.toString(),
    bloomFilter: a.bloomFilter,
    active: a.active,
  });
}

async function hasAccessByIds(rl) {
  const user = await promptUserAddress(rl);
  if (!user) return;
  const datasetId = await promptAssetId(rl, "Dataset ID");
  if (datasetId === null) return;
  const applicationId = await promptAssetId(rl, "Application ID");
  if (applicationId === null) return;
  const ok = await contract.hasAccessByIds(user, datasetId, applicationId);
  console.log("hasAccessByIds:", ok);
}

async function hasAccessByUris(rl) {
  const user = await promptUserAddress(rl);
  if (!user) return;
  const datasetUri = await prompt(rl, "Dataset encrypted URI");
  const appUri = await prompt(rl, "Application encrypted URI");
  const ok = await contract.hasAccess(user, datasetUri, appUri);
  console.log("hasAccess:", ok);
}

async function updateAsset(rl) {
  const assetId = await promptAssetId(rl, "Asset ID");
  if (assetId === null) return;
  const newPriceWei = await prompt(rl, "New price in wei");
  const newActive = await prompt(rl, "Active? (true/false)");
  const tx = await contract.updateAsset(
    assetId,
    BigInt(newPriceWei || "0"),
    newActive.toLowerCase() === "true",
  );
  const receipt = await tx.wait();
  console.log("updated tx:", receipt.hash);
}

async function revokeAsset(rl) {
  const assetId = await promptAssetId(rl, "Asset ID");
  if (assetId === null) return;
  const tx = await contract.revokeAsset(assetId);
  const receipt = await tx.wait();
  console.log("revoked tx:", receipt.hash);
}

async function listMyPurchases() {
  const filter = contract.filters.AccessPurchased(null, null, wallet.address);
  const logs = await contract.queryFilter(filter, 0, "latest");
  for (const l of logs) {
    console.log({
      tx: l.transactionHash,
      datasetId: l.args.datasetId.toString(),
      applicationId: l.args.applicationId.toString(),
      datasetPriceWei: l.args.datasetPrice.toString(),
      applicationPriceWei: l.args.applicationPrice.toString(),
    });
  }
  if (logs.length === 0)
    console.log("No purchases for signer:", wallet.address);
}

async function runFromCids(rl) {
  const datasetCid = await prompt(rl, "Dataset CID");
  if (!datasetCid) {
    console.log("Dataset CID is required.");
    return;
  }

  const scriptCid = await prompt(rl, "Script CID");
  if (!scriptCid) {
    console.log("Script CID is required.");
    return;
  }

  const pythonBinInput = await prompt(rl, "Python binary (empty = auto)");
  const pythonBin = resolvePythonBin(pythonBinInput);
  const ipfsApiUrl =
    (await prompt(rl, `IPFS API URL (default: ${IPFS_API_URL})`)) || IPFS_API_URL;

  const runnerPath = path.resolve(
    __dirname,
    "run_from_cids.py",
  );
  if (!fs.existsSync(runnerPath)) {
    console.log("Runner not found:", runnerPath);
    return;
  }

  const args = [
    runnerPath,
    "--dataset-cid",
    datasetCid,
    "--script-cid",
    scriptCid,
    "--ipfs-api-url",
    ipfsApiUrl,
  ];

  await new Promise((resolve) => {
    const child = spawn(pythonBin, args, { stdio: "inherit" });
    child.on("error", (err) => {
      console.log("Failed to start runner:", err.message);
      resolve();
    });
    child.on("close", (code) => {
      console.log("python binary:", pythonBin);
      console.log("run_from_cids exit code:", code);
      resolve();
    });
  });
}

async function showContractInfo() {
  const network = await provider.getNetwork();
  const blockNumber = await provider.getBlockNumber();
  const nextAssetId = await contract.nextAssetId();
  const balance = await provider.getBalance(wallet.address);

  console.log({
    rpcUrl: RPC_URL,
    chainId: network.chainId.toString(),
    latestBlock: blockNumber,
    contractAddress: contractAddress,
    signer: wallet.address,
    signerBalanceWei: balance.toString(),
    signerBalanceEth: ethers.formatEther(balance),
    nextAssetId: nextAssetId.toString(),
  });
}

function toYamlValue(value) {
  const s = String(value ?? "")
    .replace(/\r?\n/g, " ")
    .trim();
  return `"${s.replace(/"/g, '\\"')}"`;
}

function buildManifestYaml(manifest) {
  const lines = [
    `name: ${toYamlValue(manifest.name)}`,
    `description: ${toYamlValue(manifest.description)}`,
    `version: ${toYamlValue(manifest.version)}`,
    `author: ${toYamlValue(manifest.author)}`,
  ];

  if (manifest.framework) {
    lines.push(`framework: ${toYamlValue(manifest.framework)}`);
  }

  if (manifest.dependencies) {
    lines.push(`dependencies: ${toYamlValue(manifest.dependencies)}`);
  }

  return `${lines.join("\n")}\n`;
}

async function uploadLocalFileToIpfs(localPath) {
  const fileBuffer = fs.readFileSync(localPath);
  const formData = new FormData();
  formData.append("file", new Blob([fileBuffer]), path.basename(localPath));

  const url = `${IPFS_API_URL.replace(/\/$/, "")}/api/v0/add?pin=true`;
  const response = await fetch(url, {
    method: "POST",
    body: formData,
  });

  const raw = await response.text();
  if (!response.ok) {
    throw new Error(`IPFS upload failed (${response.status}): ${raw}`);
  }

  try {
    return JSON.parse(raw);
  } catch {
    const lastLine = raw
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .pop();
    if (!lastLine) {
      throw new Error(`Invalid IPFS response: ${raw}`);
    }
    return JSON.parse(lastLine);
  }
}

function computeSha256Hex(localPath) {
  const fileBuffer = fs.readFileSync(localPath);
  return `0x${crypto.createHash("sha256").update(fileBuffer).digest("hex")}`;
}

async function addFileToIpfsFlow(rl) {
  const filePathInput = await prompt(rl, "File path to upload");
  if (!filePathInput) {
    console.log("File path is required.");
    return null;
  }

  const resolvedPath = path.resolve(filePathInput);
  if (!fs.existsSync(resolvedPath)) {
    console.log("File not found:", resolvedPath);
    return null;
  }

  const stats = fs.statSync(resolvedPath);
  if (!stats.isFile()) {
    console.log("Path is not a file:", resolvedPath);
    return null;
  }

  const defaultName = path.basename(resolvedPath);
  const manifestName =
    (await prompt(rl, `Manifest name (default: ${defaultName})`)) ||
    defaultName;
  const manifestDescription = await prompt(rl, "Manifest description");
  const manifestVersion =
    (await prompt(rl, "Manifest version (default: 1.0.0)")) || "1.0.0";
  const manifestAuthor = await prompt(rl, "Manifest author");
  const manifestFramework = await prompt(rl, "Manifest framework (optional)");
  const manifestDependencies = await prompt(
    rl,
    "Manifest dependencies (optional)",
  );

  const manifestsDir = path.join(__dirname, "..", "manifests");
  fs.mkdirSync(manifestsDir, { recursive: true });

  const baseName = path.basename(resolvedPath, path.extname(resolvedPath));
  const manifestFileName = `${baseName}.manifest.yaml`;
  const manifestPath = path.join(manifestsDir, manifestFileName);
  const manifestYaml = buildManifestYaml({
    name: manifestName,
    description: manifestDescription,
    version: manifestVersion,
    author: manifestAuthor,
    framework: manifestFramework,
    dependencies: manifestDependencies,
  });
  fs.writeFileSync(manifestPath, manifestYaml, "utf8");

  console.log("Manifest created:", manifestPath);

  try {
    const assetParsed = await uploadLocalFileToIpfs(resolvedPath);
    const manifestParsed = await uploadLocalFileToIpfs(manifestPath);

    const assetCid = assetParsed && assetParsed.Hash ? assetParsed.Hash : null;
    const manifestCid =
      manifestParsed && manifestParsed.Hash ? manifestParsed.Hash : null;

    const assetContentHash = computeSha256Hex(resolvedPath);
    const manifestContentHash = computeSha256Hex(manifestPath);

    console.log("Asset IPFS add response:", assetParsed);
    console.log("Manifest IPFS add response:", manifestParsed);

    if (!assetCid || !manifestCid) {
      console.log("IPFS upload succeeded but missing CID in response.");
      return null;
    }

    return {
      assetCid,
      assetUri: `ipfs://${assetCid}`,
      assetContentHash,
      manifestCid,
      manifestUri: `ipfs://${manifestCid}`,
      manifestContentHash,
      localPath: resolvedPath,
      manifestPath,
    };
  } catch (e) {
    console.log("IPFS upload failed:", e instanceof Error ? e.message : e);
    return null;
  }
}

async function addFileToIpfs(rl) {
  const uploaded = await addFileToIpfsFlow(rl);
  if (!uploaded) return;

  console.log({
    assetCid: uploaded.assetCid,
    assetUri: uploaded.assetUri,
    assetContentHash: uploaded.assetContentHash,
    manifestCid: uploaded.manifestCid,
    manifestUri: uploaded.manifestUri,
    manifestContentHash: uploaded.manifestContentHash,
    localPath: uploaded.localPath,
    manifestPath: uploaded.manifestPath,
  });
}

async function main() {
  await initContract();
  const rl = readline.createInterface({ input, output });

  console.log("DNAT CLI");
  console.log("RPC:", RPC_URL);
  console.log("Contract:", contractAddress);
  console.log("Signer:", wallet.address);

  let running = true;
  while (running) {
    console.log("\nChoose an option:");
    console.log("1) Register Dataset");
    console.log("2) Register Application");
    console.log("3) Get Asset");
    console.log("4) Purchase Access");
    console.log("5) Check Access (by IDs)");
    console.log("6) Check Access (by URIs)");
    console.log("7) Update Asset");
    console.log("8) Revoke Asset");
    console.log("9) List My AccessPurchased Events");
    console.log("10) Run From CIDs");
    console.log("11) Show Contract Info");
    console.log("12) Add File To IPFS");
    console.log("0) Exit");

    const choice = await prompt(rl, "Option");

    if (choice === "1") await registerAsset(rl, 0);
    if (choice === "2") await registerAsset(rl, 1);
    if (choice === "3") await getAsset(rl);
    if (choice === "4") await purchaseAccess(rl);
    if (choice === "5") await hasAccessByIds(rl);
    if (choice === "6") await hasAccessByUris(rl);
    if (choice === "7") await updateAsset(rl);
    if (choice === "8") await revokeAsset(rl);
    if (choice === "9") await listMyPurchases();
    if (choice === "10") await runFromCids(rl);
    if (choice === "11") await showContractInfo();
    if (choice === "12") await addFileToIpfs(rl);
    if (choice === "0") {
      console.log("Exiting DNAT CLI...");
      running = false;
    }
  }

  rl.close();
}

main();
