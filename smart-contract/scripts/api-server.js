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
const EXECUTOR_URL = process.env.EXECUTOR_URL || "http://localhost:5000";
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

function resolvePythonBin(pythonBin) {
  const requested = String(pythonBin || "").trim();
  if (requested) {
    if (requested.toLowerCase() === "python") return "python3";
    return requested;
  }

  const repoPython = path.resolve(__dirname, "..", "..", ".venv", "Scripts", "python.exe");
  if (fs.existsSync(repoPython)) return repoPython;

  return "python3";
}

function normalizeExecutorBaseUrl(rawUrl) {
  const value = String(rawUrl || "").trim().replace(/\/+$/, "");
  if (!value) {
    throw new Error("Executor URL is required");
  }
  return value.endsWith("/execute") ? value.slice(0, -"/execute".length) : value;
}

function normalizeExecutorUrl(rawUrl) {
  return `${normalizeExecutorBaseUrl(rawUrl)}/execute`;
}

async function probeExecutor(executorUrl) {
  const baseUrl = normalizeExecutorBaseUrl(executorUrl);
  const url = `${baseUrl}/health`;

  try {
    const response = await fetch(url, {
      method: "GET",
      signal: AbortSignal.timeout(3000),
    });

    return {
      ok: true,
      url,
      status: response.status,
      statusText: response.statusText,
    };
  } catch (error) {
    return {
      ok: false,
      url,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

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

function parseMultipartForm(req) {
  const contentType = String(req.headers["content-type"] || "");
  const boundaryMatch = contentType.match(/boundary=(?:"([^"]+)"|([^;]+))/i);
  if (!boundaryMatch) throw new Error("Multipart boundary not found");

  const boundary = Buffer.from(`--${boundaryMatch[1] || boundaryMatch[2]}`);
  const bodyBuffer = Buffer.isBuffer(req.body) ? req.body : Buffer.from(req.body || []);
  const parts = [];
  let start = bodyBuffer.indexOf(boundary);

  while (start !== -1) {
    start += boundary.length;
    if (bodyBuffer.slice(start, start + 2).equals(Buffer.from("--"))) break;
    if (bodyBuffer[start] === 13 && bodyBuffer[start + 1] === 10) start += 2;

    const nextBoundary = bodyBuffer.indexOf(boundary, start);
    if (nextBoundary === -1) break;

    let partBuffer = bodyBuffer.slice(start, nextBoundary);
    if (partBuffer.slice(-2).equals(Buffer.from("\r\n"))) {
      partBuffer = partBuffer.slice(0, -2);
    }
    parts.push(partBuffer);
    start = nextBoundary;
  }

  const fields = {};
  let file = null;

  for (const part of parts) {
    const headerEnd = part.indexOf(Buffer.from("\r\n\r\n"));
    if (headerEnd === -1) continue;

    const headerText = part.slice(0, headerEnd).toString("utf8");
    const content = part.slice(headerEnd + 4);
    const disposition = headerText
      .split("\r\n")
      .find((line) => line.toLowerCase().startsWith("content-disposition:"));

    if (!disposition) continue;

    const nameMatch = disposition.match(/name="([^"]+)"/i);
    if (!nameMatch) continue;

    const fieldName = nameMatch[1];
    const fileNameMatch = disposition.match(/filename="([^"]*)"/i);

    if (fileNameMatch) {
      const originalName = path.basename(fileNameMatch[1] || "").trim();
      if (originalName) {
        file = {
          fieldName,
          originalName,
          buffer: content,
        };
      }
      continue;
    }

    fields[fieldName] = content.toString("utf8");
  }

  const manifest = {};
  for (const [key, value] of Object.entries(fields)) {
    if (key.startsWith("manifest.")) {
      manifest[key.slice("manifest.".length)] = value;
    }
  }

  return {
    ...fields,
    manifest,
    fileName: file?.originalName || "",
    fileBuffer: file?.buffer || null,
  };
}

function normalizeUploadRequest(req) {
  const contentType = String(req.headers["content-type"] || "").toLowerCase();
  if (contentType.startsWith("multipart/form-data")) {
    return parseMultipartForm(req);
  }
  return req.body || {};
}

function materializeUploadedFile({ filePath, fileName, fileBase64, fileBuffer }) {
  const requestedPath = String(filePath || "").trim();
  if (requestedPath) {
    const resolvedPath = path.resolve(requestedPath);
    if (!fs.existsSync(resolvedPath)) throw new Error(`File not found: ${resolvedPath}`);
    return {
      localPath: resolvedPath,
      cleanup: () => {},
    };
  }

  if (fileBuffer && Buffer.isBuffer(fileBuffer) && fileBuffer.length > 0) {
    const uploadsDir = path.join(__dirname, "..", "uploads");
    fs.mkdirSync(uploadsDir, { recursive: true });

    const safeName = path.basename(String(fileName || "uploaded-file").trim()) || "uploaded-file";
    const tempPath = path.join(uploadsDir, `${Date.now()}-${crypto.randomUUID()}-${safeName}`);
    fs.writeFileSync(tempPath, fileBuffer);

    return {
      localPath: tempPath,
      cleanup: () => {
        if (fs.existsSync(tempPath)) fs.unlinkSync(tempPath);
      },
    };
  }

  const encoded = String(fileBase64 || "").trim();
  if (!encoded) throw new Error("filePath or uploaded file is required");

  const uploadsDir = path.join(__dirname, "..", "uploads");
  fs.mkdirSync(uploadsDir, { recursive: true });

  const safeName = path.basename(String(fileName || "uploaded-file").trim()) || "uploaded-file";
  const tempPath = path.join(uploadsDir, `${Date.now()}-${crypto.randomUUID()}-${safeName}`);
  fs.writeFileSync(tempPath, Buffer.from(encoded, "base64"));

  return {
    localPath: tempPath,
    cleanup: () => {
      if (fs.existsSync(tempPath)) fs.unlinkSync(tempPath);
    },
  };
}

async function addFileToIpfsFlow({ filePath, fileName, fileBase64, fileBuffer, manifest = {} }) {
  const uploadedInput = materializeUploadedFile({ filePath, fileName, fileBase64, fileBuffer });
  const resolvedPath = uploadedInput.localPath;

  try {
    const stats = fs.statSync(resolvedPath);
    if (!stats.isFile()) throw new Error(`Path is not a file: ${resolvedPath}`);

    const defaultName = path.basename(resolvedPath);
    const manifestsDir = path.join(__dirname, "..", "manifests");
    fs.mkdirSync(manifestsDir, { recursive: true });

    const baseName = path.basename(resolvedPath, path.extname(resolvedPath));
    const manifestFileName = `${baseName}.manifest.yaml`;
    const manifestPath = path.join(manifestsDir, manifestFileName);

    const manifestYaml = buildManifestYaml({
      name: manifest.name || defaultName,
      description: manifest.description || "",
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
  } finally {
    uploadedInput.cleanup();
  }
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

async function registerAsset({ assetType, filePath, fileName, fileBase64, fileBuffer, priceWei, bloomFilter, manifest }) {
  const uploaded = await addFileToIpfsFlow({ filePath, fileName, fileBase64, fileBuffer, manifest });
  const title = String(manifest?.name || path.basename(uploaded.localPath || fileName || filePath || "Untitled asset")).trim();
  const description = String(manifest?.description || "").trim();
  const tx = await contract.registerAsset(
    Number(assetType),
    title,
    description,
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

async function resolveExecutionAssets(datasetId, applicationId) {
  const dataset = mapAsset(await contract.getAsset(BigInt(datasetId)));
  const application = mapAsset(await contract.getAsset(BigInt(applicationId)));

  if (dataset.assetType !== 0) {
    throw new Error(`Asset ${datasetId} is not a dataset.`);
  }
  if (application.assetType !== 1) {
    throw new Error(`Asset ${applicationId} is not an application.`);
  }
  if (!String(dataset.encryptedUri || "").trim()) {
    throw new Error(`Dataset ${datasetId} does not have an execution URI.`);
  }
  if (!String(application.encryptedUri || "").trim()) {
    throw new Error(`Application ${applicationId} does not have an execution URI.`);
  }

  return {
    dataset,
    application,
  };
}

async function runFromCids({ datasetId, applicationId, pythonBin, ipfsApiUrl, user }) {
  if (datasetId === undefined || datasetId === null || applicationId === undefined || applicationId === null) {
    throw new Error("datasetId and applicationId are required");
  }

  const access = await hasAccessByIds({ user, datasetId, applicationId });
  if (!access.hasAccessByIds) {
    throw new Error("Access denied. Purchase access to the selected dataset and application before executing.");
  }
  const { dataset, application } = await resolveExecutionAssets(datasetId, applicationId);

  const runnerPath = path.resolve(__dirname, "..", "..", "executor", "ipfs_executor", "run_from_cids.py");
  if (!fs.existsSync(runnerPath)) throw new Error(`Runner not found: ${runnerPath}`);
  const resolvedPythonBin = resolvePythonBin(pythonBin);
  const executorProbe = await probeExecutor(EXECUTOR_URL);
  if (!executorProbe.ok) {
    throw new Error(
      `Executor unreachable at ${executorProbe.url}. ` +
        `Verify the VM/container is running and listening on port 5000. ` +
        `Probe error: ${executorProbe.error}`,
    );
  }

  const args = [
    runnerPath,
    "--dataset-cid",
    String(dataset.encryptedUri),
    "--script-cid",
    String(application.encryptedUri),
    "--ipfs-api-url",
    String(ipfsApiUrl || IPFS_API_URL),
    "--executor-url",
    EXECUTOR_URL,
  ];

  return await new Promise((resolve, reject) => {
    const child = spawn(resolvedPythonBin, args);
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

      const executionId = parsed?.executionId;
      const execution = executionId ? getExecutionById(executionId) : null;

      resolve({
        exitCode: code,
        pythonBin: resolvedPythonBin,
        metadata: parsed,
        runnerStdout: stdout,
        runnerStderr: stderr,
        stdout: execution?.stdout || "",
        stderr: execution?.stderr || "",
        result: execution?.result || null,
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
  const multipartParser = express.raw({ type: "multipart/form-data", limit: "100mb" });

  app.get("/api/health", async (_req, res) => {
    const info = await showContractInfo();
    const executor = await probeExecutor(EXECUTOR_URL);
    res.json({
      ok: executor.ok,
      info,
      executor,
    });
  });

  app.post("/api/register-dataset", multipartParser, async (req, res) => {
    try {
      const data = await registerAsset({ ...normalizeUploadRequest(req), assetType: 0 });
      res.json(data);
    } catch (e) {
      res.status(400).json({ error: e.message });
    }
  });

  app.post("/api/register-application", multipartParser, async (req, res) => {
    try {
      const data = await registerAsset({ ...normalizeUploadRequest(req), assetType: 1 });
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

  app.post("/api/add-file-to-ipfs", multipartParser, async (req, res) => {
    try {
      res.json(await addFileToIpfsFlow(normalizeUploadRequest(req)));
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
