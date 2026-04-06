require("dotenv").config();
const { ethers } = require("hardhat");
const express = require("express");
const cors = require("cors");
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
const PORT = Number(process.env.WEB_PORT || "3001");

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
let contractAddress = CONTRACT_ADDRESS_ENV || "0x5FbDB2315678afecb367f032d93F642f64180aa3";
let contract = new ethers.Contract(contractAddress, abi, wallet);

async function resolveContractAddress() {
  if (CONTRACT_ADDRESS_ENV) {
    const code = await provider.getCode(CONTRACT_ADDRESS_ENV);
    if (code && code !== "0x") return CONTRACT_ADDRESS_ENV;
  }

  const deploymentPath = path.join(__dirname, "..", "deployments", "localhost.json");
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

function toYamlValue(value) {
  const s = String(value ?? "").replace(/\r?\n/g, " ").trim();
  return `"${s.replace(/"/g, '\\"')}"`;
}

function buildManifestYaml(manifest) {
  const lines = [
    `name: ${toYamlValue(manifest.name)}`,
    `description: ${toYamlValue(manifest.description)}`,
    `version: ${toYamlValue(manifest.version)}`,
    `author: ${toYamlValue(manifest.author)}`,
  ];

  if (manifest.framework) lines.push(`framework: ${toYamlValue(manifest.framework)}`);
  if (manifest.dependencies) lines.push(`dependencies: ${toYamlValue(manifest.dependencies)}`);

  return `${lines.join("\n")}\n`;
}

async function uploadLocalFileToIpfs(localPath) {
  const fileBuffer = fs.readFileSync(localPath);
  const formData = new FormData();
  formData.append("file", new Blob([fileBuffer]), path.basename(localPath));

  const url = `${IPFS_API_URL.replace(/\/$/, "")}/api/v0/add?pin=true`;
  const response = await fetch(url, { method: "POST", body: formData });
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

async function addFileToIpfsFlow({ filePath, manifest = {}, title = "", description = "" }) {
  const resolvedPath = path.resolve(String(filePath || "").trim());
  if (!resolvedPath) throw new Error("filePath is required");
  if (!fs.existsSync(resolvedPath)) throw new Error(`File not found: ${resolvedPath}`);

  const stats = fs.statSync(resolvedPath);
  if (!stats.isFile()) throw new Error(`Path is not a file: ${resolvedPath}`);

  const defaultName = path.basename(resolvedPath);
  const manifestsDir = path.join(__dirname, "..", "manifests");
  fs.mkdirSync(manifestsDir, { recursive: true });

  const baseName = path.basename(resolvedPath, path.extname(resolvedPath));
  const manifestFileName = `${baseName}.manifest.yaml`;
  const manifestPath = path.join(manifestsDir, manifestFileName);

  const manifestYaml = buildManifestYaml({
    name: manifest.name || manifest.title || title || defaultName,
    description: manifest.description || description || "",
    version: manifest.version || "1.0.0",
    author: manifest.author || "",
    framework: manifest.framework || "",
    dependencies: manifest.dependencies || "",
  });

  fs.writeFileSync(manifestPath, manifestYaml, "utf8");

  const assetParsed = await uploadLocalFileToIpfs(resolvedPath);
  const manifestParsed = await uploadLocalFileToIpfs(manifestPath);

  const assetCid = assetParsed && assetParsed.Hash ? assetParsed.Hash : null;
  const manifestCid = manifestParsed && manifestParsed.Hash ? manifestParsed.Hash : null;

  if (!assetCid || !manifestCid) {
    throw new Error("IPFS upload succeeded but missing CID in response.");
  }

  return {
    assetCid,
    assetUri: `ipfs://${assetCid}`,
    assetContentHash: computeSha256Hex(resolvedPath),
    manifestCid,
    manifestUri: `ipfs://${manifestCid}`,
    manifestContentHash: computeSha256Hex(manifestPath),
    localPath: resolvedPath,
    manifestPath,
  };
}

function mapAsset(a) {
  return {
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
  };
}

function isEmptyAsset(asset) {
  const zeroAddress = "0x0000000000000000000000000000000000000000";
  const zeroHash = "0x0000000000000000000000000000000000000000000000000000000000000000";
  return (
    (asset.owner || "").toLowerCase() === zeroAddress &&
    String(asset.encryptedUri || "") === "" &&
    String(asset.manifestUri || "") === "" &&
    String(asset.contentHash || "").toLowerCase() === zeroHash &&
    String(asset.priceWei || "0") === "0" &&
    asset.active === false
  );
}

async function listAssetsByScanningIds() {
  const assets = [];
  let foundAny = false;
  let emptyStreakAfterFound = 0;
  const maxChecks = 5000;
  const maxEmptyAfterFound = 3;

  for (let id = 0; id < maxChecks; id += 1) {
    try {
      const raw = await contract.getAsset(BigInt(id));
      const asset = mapAsset(raw);
      if (isEmptyAsset(asset)) {
        if (foundAny) {
          emptyStreakAfterFound += 1;
          if (emptyStreakAfterFound >= maxEmptyAfterFound) break;
        }
        continue;
      }
      foundAny = true;
      emptyStreakAfterFound = 0;
      assets.push({ id, ...asset });
    } catch {
      if (foundAny) {
        emptyStreakAfterFound += 1;
        if (emptyStreakAfterFound >= maxEmptyAfterFound) break;
      }
    }
  }

  const datasets = assets.filter((a) => a.assetType === 0);
  const applications = assets.filter((a) => a.assetType === 1);
  return { all: assets, datasets, applications };
}

async function registerAsset({ assetType, filePath, priceWei, bloomFilter, title, description, manifest }) {
  const uploaded = await addFileToIpfsFlow({ filePath, manifest, title, description });
  const normalizedTitle = String(
    title ||
      manifest?.title ||
      manifest?.name ||
      path.basename(uploaded.localPath || filePath || "Untitled asset"),
  ).trim();
  const normalizedDescription = String(description || manifest?.description || "").trim();
  const tx = await contract.registerAsset(
    Number(assetType),
    normalizedTitle,
    normalizedDescription,
    uploaded.assetUri,
    uploaded.manifestUri,
    uploaded.assetContentHash,
    BigInt(priceWei || "0"),
    bloomFilter ? String(bloomFilter) : "0x",
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
      // ignore
    }
  }
  if (createdAssetId === null) {
    const nextAssetId = await contract.nextAssetId();
    createdAssetId = nextAssetId > 0n ? nextAssetId - 1n : 0n;
  }

  const onChainAsset = await contract.getAsset(createdAssetId);
  return {
    ...uploaded,
    registeredTx: receipt.hash,
    assetId: createdAssetId.toString(),
    onChainAsset: mapAsset(onChainAsset),
  };
}

async function purchaseAccess({ datasetId, applicationId }) {
  const dataset = await contract.getAsset(BigInt(datasetId));
  const app = await contract.getAsset(BigInt(applicationId));
  const total = dataset.price + app.price;

  const tx = await contract.purchaseAccess(BigInt(datasetId), BigInt(applicationId), { value: total });
  const receipt = await tx.wait();

  return {
    purchaseTx: receipt.hash,
    totalPaidWei: total.toString(),
  };
}

async function getAsset({ assetId }) {
  const a = await contract.getAsset(BigInt(assetId));
  return mapAsset(a);
}

async function hasAccessByIds({ user, datasetId, applicationId }) {
  const ok = await contract.hasAccessByIds(
    ethers.getAddress(user || wallet.address),
    BigInt(datasetId),
    BigInt(applicationId),
  );
  return { hasAccessByIds: ok };
}

async function hasAccessByUris({ user, datasetUri, applicationUri }) {
  const ok = await contract.hasAccess(
    ethers.getAddress(user || wallet.address),
    String(datasetUri),
    String(applicationUri),
  );
  return { hasAccess: ok };
}

async function updateAsset({ assetId, newPriceWei, newActive }) {
  const tx = await contract.updateAsset(BigInt(assetId), BigInt(newPriceWei || "0"), Boolean(newActive));
  const receipt = await tx.wait();
  return { updatedTx: receipt.hash };
}

async function revokeAsset({ assetId }) {
  const tx = await contract.revokeAsset(BigInt(assetId));
  const receipt = await tx.wait();
  return { revokedTx: receipt.hash };
}

async function listMyPurchases() {
  const filter = contract.filters.AccessPurchased(null, null, wallet.address);
  const logs = await contract.queryFilter(filter, 0, "latest");

  return logs.map((l) => ({
    tx: l.transactionHash,
    datasetId: l.args.datasetId.toString(),
    applicationId: l.args.applicationId.toString(),
    datasetPriceWei: l.args.datasetPrice.toString(),
    applicationPriceWei: l.args.applicationPrice.toString(),
  }));
}

async function runFromCids({ datasetCid, scriptCid, pythonBin, ipfsApiUrl }) {
  const runnerPath = path.resolve(__dirname, "..", "..", "executor", "ipfs_executor", "run_from_cids.py");
  if (!fs.existsSync(runnerPath)) throw new Error(`Runner not found: ${runnerPath}`);

  const args = [
    runnerPath,
    "--dataset-cid",
    String(datasetCid || ""),
    "--script-cid",
    String(scriptCid || ""),
    "--ipfs-api-url",
    String(ipfsApiUrl || IPFS_API_URL),
  ];

  return await new Promise((resolve, reject) => {
    const child = spawn(String(pythonBin || "python"), args);
    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    child.on("error", (err) => reject(err));
    child.on("close", (code) => {
      let parsed = null;
      try {
        parsed = JSON.parse(stdout);
      } catch {
        parsed = null;
      }

      resolve({
        exitCode: code,
        metadata: parsed,
        stdout,
        stderr,
      });
    });
  });
}

async function showContractInfo() {
  const network = await provider.getNetwork();
  const blockNumber = await provider.getBlockNumber();
  const nextAssetId = await contract.nextAssetId();
  const balance = await provider.getBalance(wallet.address);

  return {
    rpcUrl: RPC_URL,
    chainId: network.chainId.toString(),
    latestBlock: blockNumber,
    contractAddress,
    signer: wallet.address,
    signerBalanceWei: balance.toString(),
    signerBalanceEth: ethers.formatEther(balance),
    nextAssetId: nextAssetId.toString(),
  };
}

function readJsonIfExists(filePath) {
  if (!fs.existsSync(filePath)) return null;
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

function listExecutions() {
  const root = path.resolve(__dirname, "..", "..", "executor", "executions");
  if (!fs.existsSync(root)) return [];

  const dirs = fs
    .readdirSync(root, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .sort((a, b) => b.localeCompare(a));

  return dirs.map((id) => {
    const dir = path.join(root, id);
    const metadata = readJsonIfExists(path.join(dir, "metadata.json"));
    return {
      executionId: id,
      status: metadata?.status || "unknown",
      returnCode: metadata?.returnCode ?? null,
      createdAtUtc: metadata?.createdAtUtc || null,
    };
  });
}

function getExecutionById(executionId) {
  const root = path.resolve(__dirname, "..", "..", "executor", "executions");
  const dir = path.join(root, executionId);
  if (!fs.existsSync(dir)) {
    throw new Error(`Execution not found: ${executionId}`);
  }

  const metadataPath = path.join(dir, "metadata.json");
  const stdoutPath = path.join(dir, "stdout.txt");
  const stderrPath = path.join(dir, "stderr.txt");
  const resultPath = path.join(dir, "result.json");

  return {
    executionId,
    metadata: readJsonIfExists(metadataPath),
    stdout: fs.existsSync(stdoutPath) ? fs.readFileSync(stdoutPath, "utf8") : "",
    stderr: fs.existsSync(stderrPath) ? fs.readFileSync(stderrPath, "utf8") : "",
    result: readJsonIfExists(resultPath),
  };
}

function parseBoolean(value) {
  if (typeof value === "boolean") return value;
  if (typeof value === "string") return value.toLowerCase() === "true";
  return Boolean(value);
}

async function startServer() {
  await initContract();

  const app = express();
  app.use(cors());
  app.use(express.json());
  app.use(express.static(path.resolve(__dirname, "..", "web")));

  app.get("/api/health", async (_req, res) => {
    const info = await showContractInfo();
    res.json({ ok: true, info });
  });

  app.post("/api/register-dataset", async (req, res) => {
    try {
      const data = await registerAsset({ ...req.body, assetType: 0 });
      res.json(data);
    } catch (e) {
      res.status(400).json({ error: e.message });
    }
  });

  app.post("/api/register-application", async (req, res) => {
    try {
      const data = await registerAsset({ ...req.body, assetType: 1 });
      res.json(data);
    } catch (e) {
      res.status(400).json({ error: e.message });
    }
  });

  app.post("/api/get-asset", async (req, res) => {
    try {
      res.json(await getAsset(req.body));
    } catch (e) {
      res.status(400).json({ error: e.message });
    }
  });

  app.post("/api/purchase-access", async (req, res) => {
    try {
      res.json(await purchaseAccess(req.body));
    } catch (e) {
      res.status(400).json({ error: e.message });
    }
  });

  app.post("/api/check-access-by-ids", async (req, res) => {
    try {
      res.json(await hasAccessByIds(req.body));
    } catch (e) {
      res.status(400).json({ error: e.message });
    }
  });

  app.post("/api/check-access-by-uris", async (req, res) => {
    try {
      res.json(await hasAccessByUris(req.body));
    } catch (e) {
      res.status(400).json({ error: e.message });
    }
  });

  app.post("/api/update-asset", async (req, res) => {
    try {
      res.json(
        await updateAsset({
          ...req.body,
          newActive: parseBoolean(req.body.newActive),
        }),
      );
    } catch (e) {
      res.status(400).json({ error: e.message });
    }
  });

  app.post("/api/revoke-asset", async (req, res) => {
    try {
      res.json(await revokeAsset(req.body));
    } catch (e) {
      res.status(400).json({ error: e.message });
    }
  });

  app.get("/api/list-my-purchases", async (_req, res) => {
    try {
      res.json(await listMyPurchases());
    } catch (e) {
      res.status(400).json({ error: e.message });
    }
  });

  app.post("/api/run-from-cids", async (req, res) => {
    try {
      res.json(await runFromCids(req.body));
    } catch (e) {
      res.status(400).json({ error: e.message });
    }
  });

  app.get("/api/contract-info", async (_req, res) => {
    try {
      res.json(await showContractInfo());
    } catch (e) {
      res.status(400).json({ error: e.message });
    }
  });

  app.post("/api/add-file-to-ipfs", async (req, res) => {
    try {
      res.json(await addFileToIpfsFlow(req.body));
    } catch (e) {
      res.status(400).json({ error: e.message });
    }
  });

  app.get("/api/assets", async (_req, res) => {
    try {
      res.json(await listAssetsByScanningIds());
    } catch (e) {
      res.status(400).json({ error: e.message });
    }
  });

  app.get("/api/executions", (_req, res) => {
    try {
      res.json(listExecutions());
    } catch (e) {
      res.status(400).json({ error: e.message });
    }
  });

  app.get("/api/executions/:executionId", (req, res) => {
    try {
      res.json(getExecutionById(req.params.executionId));
    } catch (e) {
      res.status(404).json({ error: e.message });
    }
  });

  app.listen(PORT, () => {
    console.log(`DNAT Web UI running on http://localhost:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error(err);
  process.exit(1);
});
