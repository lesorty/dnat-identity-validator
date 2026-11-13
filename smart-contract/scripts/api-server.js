require("dotenv").config();
const { ethers } = require("hardhat");
const express = require("express");
const cors = require("cors");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const crypto = require("node:crypto");
const { spawn } = require("node:child_process");
const { pipeline } = require("node:stream/promises");
const { Readable } = require("node:stream");

const RPC_URL = process.env.RPC_URL || "http://127.0.0.1:8545";
const PRIVATE_KEY =
  process.env.PRIVATE_KEY ||
  "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
const CONTRACT_ADDRESS_ENV = process.env.CONTRACT_ADDRESS;
const IPFS_API_URL = process.env.IPFS_API_URL || "http://localhost:5001";
const EXECUTOR_URL = process.env.EXECUTOR_URL || "http://localhost:5000";
const PORT = Number(process.env.WEB_PORT || "3001");
const EXECUTIONS_ROOT = path.resolve(__dirname, "..", "executions");
const RUNNER_PATH = path.resolve(__dirname, "run_from_cids.py");
const BUILDER_URL = process.env.BUILDER_URL || "http://dnat-builder:5100";
const {
  APP_ARTIFACT_FORMAT,
  DATASET_FORMAT,
  encryptBuffer,
  decryptBufferEnvelope,
  encryptFileToFile,
  decryptFileToFile,
  hasEncryptedEnvelope,
} = require("./asset_envelope");
const {
  IdentityError,
  IdentityRegistry,
  RequestVerifier,
  DEFAULT_DIFFICULTY,
  RESERVE_COST,
  recordExecutionIdentity,
} = require("./identity");
const { getDerivative, retainDerivative, userSummary } = require("./retention");
const { MODEL_FORMAT } = require("./asset_envelope");
const { extractVerified, modelDirDigest } = require("./model_store");
const { judgeDerivative, loadAllowlist, ALLOWLIST_PATH } = require("./judge_flow");

// Estado da CVM1 ao lado de executions/: identidades (T-1702) e derivados retidos (T-803).
const IDENTITIES_PATH = process.env.DNAT_IDENTITIES_PATH || path.join(path.dirname(EXECUTIONS_ROOT), "identities.json");
const DERIVATIVES_PATH = process.env.DNAT_DERIVATIVES_PATH || path.join(path.dirname(EXECUTIONS_ROOT), "derivatives.json");
// Referências custodiadas dos pais (T-312), depositadas pelo operador no host (scripts/judge_cli.js).
const REFERENCES_PATH = process.env.DNAT_REFERENCES_PATH || path.join(path.dirname(EXECUTIONS_ROOT), "references.json");
// Pacote da bateria custodiado e chave do sorteio do S1 (T-807), também só da CVM1.
const BATTERY_PACK_PATH = process.env.DNAT_BATTERY_PACK_PATH || path.join(path.dirname(EXECUTIONS_ROOT), "battery_pack.json");
const SAMPLING_KEY_PATH = process.env.DNAT_SAMPLING_KEY_PATH || path.join(path.dirname(EXECUTIONS_ROOT), "sampling_key");
const MODEL_ASSET_TYPE = 2;
const IDENTITY_DIFFICULTY = Number(process.env.DNAT_IDENTITY_DIFFICULTY || DEFAULT_DIFFICULTY);

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
  // Derivado julgado (T-703, T-809): só o operador, que é a carteira desta CVM1.
  "function registerDerivative((uint256 parentId, bytes32 parentReferenceHash, bytes32 derivativeHash, bytes32 judgeHash, bytes32 batteryCommitment, bytes32 preregHash, bytes32 datasetHash, bytes32 verdictHash, bytes32 identityId, uint8 verdict, uint64 decidedAt) info, address owner, string title, string encryptedUri) returns (uint256)",
  "function getDerivative(uint256 assetId) view returns ((uint256 parentId, bytes32 parentReferenceHash, bytes32 derivativeHash, bytes32 judgeHash, bytes32 batteryCommitment, bytes32 preregHash, bytes32 datasetHash, bytes32 verdictHash, bytes32 identityId, uint8 verdict, uint64 decidedAt))",
  "function isDerivativeUsable(uint256 assetId) view returns (bool)",
  "event DerivativeRegistered(uint256 indexed id, uint256 indexed parentId, (uint256 parentId, bytes32 parentReferenceHash, bytes32 derivativeHash, bytes32 judgeHash, bytes32 batteryCommitment, bytes32 preregHash, bytes32 datasetHash, bytes32 verdictHash, bytes32 identityId, uint8 verdict, uint64 decidedAt) info)",
];

const provider = new ethers.JsonRpcProvider(RPC_URL);
const wallet = new ethers.Wallet(PRIVATE_KEY, provider);
// A CVM1 manda transações em sequência rápida (registro, derivado); o provider guarda a contagem de
// transações por alguns ms e duas seguidas sairiam com o mesmo nonce. O NonceManager conta localmente.
const signer = new ethers.NonceManager(wallet);
let contractAddress = CONTRACT_ADDRESS_ENV || "0x5FbDB2315678afecb367f032d93F642f64180aa3";
let contract = new ethers.Contract(contractAddress, abi, signer);

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

function normalizeBuilderBaseUrl(rawUrl) {
  const value = String(rawUrl || "").trim().replace(/\/+$/, "");
  if (!value) {
    throw new Error("Builder URL is required");
  }
  return value.endsWith("/build") ? value.slice(0, -"/build".length) : value;
}

function normalizeBuilderUrl(rawUrl) {
  return `${normalizeBuilderBaseUrl(rawUrl)}/build`;
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

async function probeBuilder(builderUrl) {
  const baseUrl = normalizeBuilderBaseUrl(builderUrl);
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
  contract = new ethers.Contract(contractAddress, abi, signer);
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

function normalizeCid(cidOrUri) {
  const value = String(cidOrUri || "").trim();
  if (value.startsWith("ipfs://")) {
    return value.slice("ipfs://".length);
  }
  return value;
}

function runCommand(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      stdio: ["ignore", "pipe", "pipe"],
      ...options,
    });
    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(`${command} exited with code ${code}: ${stderr || stdout}`.trim()));
        return;
      }
      resolve({ stdout, stderr });
    });
  });
}

function parseManifestDependencies(rawDependencies) {
  const rawValue = String(rawDependencies || "").trim();
  if (!rawValue) return [];

  try {
    const parsed = JSON.parse(rawValue);
    if (Array.isArray(parsed)) {
      return parsed.map((value) => String(value).trim()).filter(Boolean);
    }
  } catch {
    // Fall through to line-based parsing.
  }

  const lines = rawValue
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"));
  if (lines.length === 0) return [];

  if (lines.length === 1 && lines[0].includes(",")) {
    return lines[0]
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean);
  }

  return lines;
}

function computeBufferSha256Hex(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

async function downloadFromIpfsBytes(cidOrUri, ipfsApiUrl = IPFS_API_URL) {
  const cid = normalizeCid(cidOrUri);
  if (!cid) throw new Error("CID is required");

  const url = `${String(ipfsApiUrl || IPFS_API_URL).replace(/\/$/, "")}/api/v0/cat?arg=${encodeURIComponent(cid)}`;
  const response = await fetch(url, { method: "POST" });
  if (!response.ok) {
    throw new Error(`IPFS download failed (${response.status}) for CID ${cid}`);
  }
  const arrayBuffer = await response.arrayBuffer();
  return Buffer.from(arrayBuffer);
}

// T-805: baixa do IPFS direto para um arquivo, sem montar o conteúdo na memória.
async function downloadFromIpfsToFile(cidOrUri, destPath, ipfsApiUrl = IPFS_API_URL) {
  const cid = normalizeCid(cidOrUri);
  if (!cid) throw new Error("CID is required");
  const url = `${String(ipfsApiUrl || IPFS_API_URL).replace(/\/$/, "")}/api/v0/cat?arg=${encodeURIComponent(cid)}`;
  const response = await fetch(url, { method: "POST" });
  if (!response.ok || !response.body) {
    throw new Error(`IPFS download failed (${response.status}) for CID ${cid}`);
  }
  await pipeline(Readable.fromWeb(response.body), fs.createWriteStream(destPath));
  return destPath;
}

async function uploadLocalFileToIpfs(localPath) {
  // openAsBlob lê o arquivo em fluxo quando o fetch envia (T-805: envelopes de GB).
  const formData = new FormData();
  formData.append("file", await fs.openAsBlob(localPath), path.basename(localPath));

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

// Pedido da API: o arquivo vem no corpo. filePath (caminho no disco desta CVM1) só vale para o
// CLI local; aceito pela rede, deixaria qualquer identidade publicar arquivos do servidor.
function normalizeUploadRequest(req) {
  const contentType = String(req.headers["content-type"] || "").toLowerCase();
  const fields = contentType.startsWith("multipart/form-data") ? parseMultipartForm(req) : { ...(req.body || {}) };
  delete fields.filePath;
  return fields;
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

async function buildApplicationArtifact({ sourceFilePath, manifest = {} }) {
  const builderProbe = await probeBuilder(BUILDER_URL);
  if (!builderProbe.ok) {
    throw new Error(
      `Builder unreachable at ${builderProbe.url}. ` +
        `Verify the CVM3 builder service is running and reachable from the CVM1. ` +
        `Probe error: ${builderProbe.error}`,
    );
  }

  const dependencies = parseManifestDependencies(manifest.dependencies);
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-build-request-"));
  const sourceDir = path.join(tempRoot, "source");
  const requestBundlePath = path.join(tempRoot, "request.tar.gz");
  const responseBundlePath = path.join(tempRoot, "response.tar.gz");
  const responseDir = path.join(tempRoot, "response");
  try {
    fs.mkdirSync(sourceDir, { recursive: true });
    fs.mkdirSync(responseDir, { recursive: true });

    const requestManifest = {
      name: String(manifest.name || ""),
      description: String(manifest.description || ""),
      framework: String(manifest.framework || "python"),
      dependencies,
    };
    fs.copyFileSync(sourceFilePath, path.join(sourceDir, "application.py"));
    fs.writeFileSync(path.join(tempRoot, "manifest.json"), JSON.stringify(requestManifest, null, 2), "utf8");

    await runCommand("tar", ["-czf", requestBundlePath, "-C", tempRoot, "source", "manifest.json"]);

    const response = await fetch(normalizeBuilderUrl(BUILDER_URL), {
      method: "POST",
      headers: { "Content-Type": "application/gzip" },
      body: fs.readFileSync(requestBundlePath),
      signal: AbortSignal.timeout(2_100_000),
    });

    if (!response.ok) {
      const raw = await response.text();
      let parsedError = null;
      try {
        const parsed = JSON.parse(raw);
        parsedError = parsed.error ? `${parsed.error}${parsed.stderr ? ` | stderr: ${parsed.stderr}` : ""}` : raw;
      } catch {
        parsedError = raw;
      }
      throw new Error(`Builder request failed (${response.status}): ${parsedError}`);
    }

    fs.writeFileSync(responseBundlePath, Buffer.from(await response.arrayBuffer()));
    await runCommand("tar", ["-xzf", responseBundlePath, "-C", responseDir]);

    const artifactPath = path.join(responseDir, "application.ext4");
    if (!fs.existsSync(artifactPath)) {
      throw new Error("Builder response did not contain application.ext4");
    }

    return {
      artifactPath,
      cleanup: () => {
        fs.rmSync(tempRoot, { recursive: true, force: true });
      },
    };
  } catch (error) {
    fs.rmSync(tempRoot, { recursive: true, force: true });
    throw error;
  }
}

async function addFileToIpfsFlow({ filePath, fileName, fileBase64, fileBuffer, manifest = {}, encrypt = false }) {
  const uploadedInput = materializeUploadedFile({ filePath, fileName, fileBase64, fileBuffer });
  const resolvedPath = uploadedInput.localPath;
  let encryptedTempPath = null;

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

    // O ativo sobe cifrado; o hash on-chain continua sendo o do conteudo em claro,
    // porque o CID e hash do ciphertext e o IV e aleatorio a cada cifra.
    let assetUploadPath = resolvedPath;
    if (encrypt) {
      encryptedTempPath = path.join(os.tmpdir(), `dnat-asset-${crypto.randomUUID()}.enc`);
      fs.writeFileSync(
        encryptedTempPath,
        encryptBuffer(fs.readFileSync(resolvedPath), { sourceFileName: defaultName }, DATASET_FORMAT),
      );
      assetUploadPath = encryptedTempPath;
    }

    const assetParsed = await uploadLocalFileToIpfs(assetUploadPath);
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
    if (encryptedTempPath && fs.existsSync(encryptedTempPath)) fs.unlinkSync(encryptedTempPath);
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
  const models = assets.filter((a) => a.assetType === MODEL_ASSET_TYPE);
  return { all: assets, datasets, applications, models };
}

// Modelo base (T-809): o dono envia o tar.gz do diretório do modelo. A CVM1 extrai com cuidado,
// calcula o digest de model_gate.io.digest (o contentHash on-chain, que o Juiz confere) e guarda o
// pacote cifrado no IPFS.
async function uploadModelArchive({ filePath, fileName, fileBase64, fileBuffer, manifest = {} }) {
  const uploadedInput = materializeUploadedFile({ filePath, fileName, fileBase64, fileBuffer });
  const work = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-model-"));
  const encryptedPath = path.join(work, "model.enc");
  try {
    const digest = extractVerified(uploadedInput.localPath, path.join(work, "model"), null);
    await encryptFileToFile(uploadedInput.localPath, encryptedPath,
      { digest, files: modelDirDigest(path.join(work, "model")).files.length }, MODEL_FORMAT);
    const uploaded = await addFileToIpfsFlow({ filePath: encryptedPath, manifest: { ...manifest, framework: "model-dir" } });
    return { ...uploaded, localPath: String(fileName || "model"), assetContentHash: `0x${digest}`, modelDigest: digest };
  } finally {
    uploadedInput.cleanup();
    fs.rmSync(work, { recursive: true, force: true });
  }
}

async function registerAsset({ assetType, filePath, fileName, fileBase64, fileBuffer, priceWei, bloomFilter, manifest }) {
  let uploaded;

  if (Number(assetType) === MODEL_ASSET_TYPE) {
    uploaded = await uploadModelArchive({ filePath, fileName, fileBase64, fileBuffer, manifest });
  } else if (Number(assetType) === 1) {
    const uploadedInput = materializeUploadedFile({ filePath, fileName, fileBase64, fileBuffer });
    let builtArtifact = null;
    let encryptedPath = null;

    try {
      builtArtifact = await buildApplicationArtifact({
        sourceFilePath: uploadedInput.localPath,
        manifest,
      });

      const artifactBuffer = fs.readFileSync(builtArtifact.artifactPath);
      const encryptedBuffer = encryptBuffer(artifactBuffer, {
        sourceFileName: path.basename(uploadedInput.localPath),
        artifactType: APP_ARTIFACT_FORMAT,
        framework: String(manifest?.framework || "python"),
        dependencies: String(manifest?.dependencies || ""),
      });

      const uploadsDir = path.join(__dirname, "..", "uploads");
      fs.mkdirSync(uploadsDir, { recursive: true });
      encryptedPath = path.join(uploadsDir, `${Date.now()}-${crypto.randomUUID()}-application-artifact.enc.json`);
      fs.writeFileSync(encryptedPath, encryptedBuffer);

      uploaded = await addFileToIpfsFlow({
        filePath: encryptedPath,
        manifest: {
          ...manifest,
          framework: manifest?.framework || "python",
          dependencies: manifest?.dependencies || "",
        },
      });

      uploaded.assetType = APP_ARTIFACT_FORMAT;
      uploaded.plaintextArtifactContentHash = computeSha256Hex(builtArtifact.artifactPath);
    } finally {
      uploadedInput.cleanup();
      builtArtifact?.cleanup?.();
      if (encryptedPath && fs.existsSync(encryptedPath)) fs.unlinkSync(encryptedPath);
    }
  } else {
    uploaded = await addFileToIpfsFlow({ filePath, fileName, fileBase64, fileBuffer, manifest, encrypt: true });
  }

  const title = String(manifest?.name || path.basename(uploaded.localPath || fileName || filePath || "Untitled asset")).trim();
  const description = String(manifest?.description || "").trim();
  const tx = await contract.registerAsset(
    Number(assetType),
    title,
    description,
    uploaded.assetUri,
    uploaded.manifestUri,
    uploaded.plaintextArtifactContentHash || uploaded.assetContentHash,
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

// Envelope já cifrado em arquivo (retention.sealAndUpload) -> CID.
async function uploadEnvelopeFile(envelopePath) {
  const parsed = await uploadLocalFileToIpfs(envelopePath);
  return parsed?.Hash || null;
}

// Cifra o derivado, guarda no IPFS e o anota como retido; ao usuario volta so o resumo (T-803).
async function retainExecutionDerivative({ executionId, digest, archivePath, context }) {
  try {
    const record = await retainDerivative({
      archivePath,
      digest,
      executionId,
      statePath: DERIVATIVES_PATH,
      upload: uploadEnvelopeFile,
      context,
    });
    return userSummary(record);
  } catch (e) {
    return { digest, status: "retention_failed", error: e.message };
  }
}

// Lista de Juízes permitidos da implantação (T-808); sem o arquivo, nenhum Juiz roda.
function loadJudgeAllowlist() {
  return fs.existsSync(ALLOWLIST_PATH) ? loadAllowlist(ALLOWLIST_PATH) : [];
}

// Modelo base de um fine-tuning (T-809): tem de ser um Model ativo, com pacote no IPFS.
async function resolveParentModel(parentModelId) {
  if (parentModelId === undefined || parentModelId === null || parentModelId === "") return null;
  const parent = mapAsset(await contract.getAsset(BigInt(parentModelId)));
  if (parent.assetType !== MODEL_ASSET_TYPE) throw new Error(`Asset ${parentModelId} is not a model.`);
  if (!parent.active) throw new Error(`Model ${parentModelId} is inactive.`);
  if (!String(parent.encryptedUri || "").trim()) throw new Error(`Model ${parentModelId} does not have an execution URI.`);
  return parent;
}

// O pacote do base em claro só existe no diretório temporário do pedido, conferido pelo contentHash.
async function materializeParentModel(parent, destDir, ipfsApiUrl) {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-base-"));
  try {
    const envelope = path.join(work, "model.enc");
    const archive = path.join(work, "model.tar.gz");
    await downloadFromIpfsToFile(parent.encryptedUri, envelope, ipfsApiUrl || IPFS_API_URL);
    await decryptFileToFile(envelope, archive, [MODEL_FORMAT]);
    fs.rmSync(envelope, { force: true });
    return extractVerified(archive, destDir, parent.contentHash);
  } finally {
    fs.rmSync(work, { recursive: true, force: true });
  }
}

async function runFromCids({ datasetId, applicationId, parentModelId, pythonBin, ipfsApiUrl, user, identityId, ledger = null }) {
  if (datasetId === undefined || datasetId === null || applicationId === undefined || applicationId === null) {
    throw new Error("datasetId and applicationId are required");
  }

  const access = await hasAccessByIds({ user, datasetId, applicationId });
  if (!access.hasAccessByIds) {
    throw new Error("Access denied. Purchase access to the selected dataset and application before executing.");
  }
  const { dataset, application } = await resolveExecutionAssets(datasetId, applicationId);
  const parent = await resolveParentModel(parentModelId);

  if (!fs.existsSync(RUNNER_PATH)) throw new Error(`Runner not found: ${RUNNER_PATH}`);
  const resolvedPythonBin = resolvePythonBin(pythonBin);
  const executorProbe = await probeExecutor(EXECUTOR_URL);
  if (!executorProbe.ok) {
    throw new Error(
      `Executor unreachable at ${executorProbe.url}. ` +
        `Verify the VM/container is running and listening on port 5000. ` +
        `Probe error: ${executorProbe.error}`,
    );
  }

  // Cota (T-1704, E14 §18.4): a reserva sai do saldo da identidade no aceite, depois das checagens
  // baratas (acesso, ativos, executor) e antes de gastar a CVM. Sem saldo, IdentityError 402.
  // O acerto pelo veredito (1, 2 ou 5) é do Juiz como segundo job (T-807, T-809), quando há modelo
  // pai; job sem veredito (falha, sem pai ou sem derivado) devolve a reserva.
  const reservationId = ledger && identityId ? crypto.randomUUID() : null;
  if (reservationId) ledger.reserve(identityId, reservationId);
  let quotaSettled = false;
  const settleFailure = () => {
    if (!reservationId || quotaSettled) return;
    quotaSettled = true;
    ledger.settle(reservationId, "failure");
  };

  const preparationDir = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-execution-"));
  const datasetPath = path.join(preparationDir, "dataset.csv");
  const applicationArtifactPath = path.join(preparationDir, "application.ext4");
  // O derivado em claro so passa por aqui, dentro do diretorio temporario (T-803).
  const derivativeArchivePath = path.join(preparationDir, "derivative.tar.gz");
  const baseModelDir = path.join(preparationDir, "base-model");

  try {
    const datasetBytes = await downloadFromIpfsBytes(dataset.encryptedUri, ipfsApiUrl || IPFS_API_URL);
    // Datasets registrados antes da cifra estao em claro no IPFS; o envelope distingue os novos.
    fs.writeFileSync(
      datasetPath,
      hasEncryptedEnvelope(datasetBytes)
        ? decryptBufferEnvelope(datasetBytes, [DATASET_FORMAT]).plaintext
        : datasetBytes,
    );

    const encryptedApplicationBytes = await downloadFromIpfsBytes(application.encryptedUri, ipfsApiUrl || IPFS_API_URL);
    const decryptedApplication = decryptBufferEnvelope(encryptedApplicationBytes);
    fs.writeFileSync(applicationArtifactPath, decryptedApplication.plaintext);
    if (parent) await materializeParentModel(parent, baseModelDir, ipfsApiUrl);

  const args = [
    RUNNER_PATH,
    "--local-dataset-path",
    datasetPath,
    "--application-artifact-path",
    applicationArtifactPath,
    "--dataset-cid",
    String(dataset.encryptedUri),
    "--application-cid",
    String(application.encryptedUri),
    "--executor-url",
    EXECUTOR_URL,
    "--derivative-out",
    derivativeArchivePath,
    ...(parent ? ["--base-model-dir", baseModelDir] : []),
  ];

    const { code, stdout, stderr } = await new Promise((resolve, reject) => {
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
      child.on("close", (code) => resolve({ code, stdout, stderr }));
    });

    let parsed = null;
    try {
      parsed = JSON.parse(stdout);
    } catch {
      parsed = null;
    }

    const executionId = parsed?.executionId;
    // Id da identidade que assinou o pedido, em toda execução (T-1703); a T-809 o leva ao recibo.
    if (executionId) {
      recordExecutionIdentity(path.join(EXECUTIONS_ROOT, executionId, "metadata.json"), identityId,
        reservationId ? { quotaReservationId: reservationId } : {});
    }
    if (executionId && parsed.derivative?.status === "received") {
      parsed.derivative = await retainExecutionDerivative({
        executionId,
        digest: parsed.derivative.digest,
        archivePath: derivativeArchivePath,
        context: {
          datasetId: String(datasetId),
          applicationId: String(applicationId),
          user: user || wallet.address,
          ...(identityId ? { identityId } : {}),
          ...(reservationId ? { quotaReservationId: reservationId } : {}),
          ...(parent ? { parentModelId: String(parentModelId) } : {}),
        },
      });
      const metadataPath = path.join(EXECUTIONS_ROOT, executionId, "metadata.json");
      const metadata = readJsonIfExists(metadataPath);
      if (metadata) {
        fs.writeFileSync(metadataPath, JSON.stringify({ ...metadata, derivative: parsed.derivative }, null, 2), "utf8");
      }
    }
    const execution = executionId ? getExecutionById(executionId) : null;

    // Falha do job (T-107): sem execução, saída não zero ou resultado inconclusivo por falha.
    // A reserva volta inteira e não conta.
    if (code !== 0 || !executionId || execution?.metadata?.outcome === "inconclusive_failure") settleFailure();

    // Segundo job (T-807, T-809): com modelo pai e derivado retido, o Juiz julga e a CVM1 grava o
    // recibo e acerta a cota. Sem derivado não há veredito, e a reserva volta.
    let judge = null;
    if (parent && !quotaSettled) {
      if (parsed.derivative?.status === "retained") {
        judge = await judgeDerivative({
          contract,
          ledger,
          derivativesPath: DERIVATIVES_PATH,
          referencesPath: REFERENCES_PATH,
          batteryPath: BATTERY_PACK_PATH,
          samplingKeyPath: SAMPLING_KEY_PATH,
          executionId,
          parentId: String(parentModelId),
          datasetPath,
          fetchToFile: (uri, dest) => downloadFromIpfsToFile(uri, dest, ipfsApiUrl || IPFS_API_URL),
          allowlist: loadJudgeAllowlist(),
          owner: user || wallet.address,
          title: `Derivado de ${parent.title} (${executionId})`,
        });
        quotaSettled = true;
        parsed.derivative = userSummary(getDerivative(DERIVATIVES_PATH, executionId));
        const metadataPath = path.join(EXECUTIONS_ROOT, executionId, "metadata.json");
        const metadata = readJsonIfExists(metadataPath);
        if (metadata) {
          const verdict = { outcome: judge.outcome, assetId: judge.assetId || null, alert: judge.alert || null };
          fs.writeFileSync(metadataPath, JSON.stringify({ ...metadata, derivative: parsed.derivative, judge: verdict }, null, 2), "utf8");
        }
      } else {
        settleFailure();
      }
    } else if (!parent) {
      settleFailure();
    }
    const quota = reservationId
      ? { reservationId, reserved: quotaSettled ? 0 : RESERVE_COST, balance: ledger.summary(identityId).balance }
      : null;

    return {
      quota,
      judge: judge ? { outcome: judge.outcome, assetId: judge.assetId || null, alert: judge.alert || null } : null,
      exitCode: code,
      pythonBin: resolvedPythonBin,
      metadata: parsed,
      runnerStdout: stdout,
      runnerStderr: stderr,
      stdout: execution?.stdout || "",
      stderr: execution?.stderr || "",
      result: execution?.result || null,
    };
  } catch (e) {
    settleFailure();
    throw e;
  } finally {
    fs.rmSync(preparationDir, { recursive: true, force: true });
  }
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
  if (!fs.existsSync(EXECUTIONS_ROOT)) return [];

  const dirs = fs
    .readdirSync(EXECUTIONS_ROOT, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .sort((a, b) => b.localeCompare(a));

  return dirs.map((id) => {
    const dir = path.join(EXECUTIONS_ROOT, id);
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
  const dir = path.join(EXECUTIONS_ROOT, executionId);
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
  const identities = new IdentityRegistry({
    statePath: IDENTITIES_PATH,
    difficulty: IDENTITY_DIFFICULTY,
    challenge: process.env.DNAT_IDENTITY_CHALLENGE || null,
  });
  // Pedidos assinados pela identidade (T-1703, E14 §18.2): só nas rotas que criam trabalho.
  const requireSignedRequest = new RequestVerifier({ registry: identities }).middleware();

  const app = express();
  app.use(cors());
  app.use(express.json({ verify: (req, _res, buf) => { req.rawBody = buf; } }));
  app.use(express.static(path.resolve(__dirname, "..", "web")));
  // DNAT_UPLOAD_LIMIT: o depósito de um modelo base passa de 100 MB (T-805); padrão mantido.
  const multipartParser = express.raw({ type: "multipart/form-data", limit: process.env.DNAT_UPLOAD_LIMIT || "100mb" });

  app.get("/api/health", async (_req, res) => {
    const info = await showContractInfo();
    const executor = await probeExecutor(EXECUTOR_URL);
    const builder = await probeBuilder(BUILDER_URL);
    res.json({
      ok: executor.ok && builder.ok,
      info,
      executor,
      builder,
    });
  });

  // Identidade cara (T-1702, E14 §18): desafio da implantação e d; registro com prova de trabalho.
  app.get("/api/identity/challenge", (_req, res) => {
    res.json(identities.challenge());
  });

  // Saldo e contagens por desfecho (T-1704): o que o auditor e o modelo do atacante leem.
  app.get("/api/identity/:id", (req, res) => {
    const summary = identities.summary(req.params.id);
    if (!summary) return res.status(404).json({ error: "unknown identity" });
    res.json(summary);
  });

  app.post("/api/identity/register", (req, res) => {
    try {
      res.status(201).json(identities.register(req.body || {}));
    } catch (e) {
      res.status(e instanceof IdentityError ? e.status : 500).json({ error: e.message });
    }
  });

  app.post("/api/register-dataset", multipartParser, requireSignedRequest, async (req, res) => {
    try {
      const data = await registerAsset({ ...normalizeUploadRequest(req), assetType: 0 });
      res.json(data);
    } catch (e) {
      res.status(400).json({ error: e.message });
    }
  });

  // Modelo base custodiado (T-809): multipart com o tar.gz do diretório do modelo.
  app.post("/api/register-model", multipartParser, requireSignedRequest, async (req, res) => {
    try {
      res.json(await registerAsset({ ...normalizeUploadRequest(req), assetType: MODEL_ASSET_TYPE }));
    } catch (e) {
      res.status(400).json({ error: e.message });
    }
  });

  app.post("/api/register-application", multipartParser, requireSignedRequest, async (req, res) => {
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

  app.post("/api/run-from-cids", requireSignedRequest, async (req, res) => {
    try {
      res.json(await runFromCids({ ...req.body, identityId: req.identity.id, ledger: identities }));
    } catch (e) {
      res.status(e instanceof IdentityError ? e.status : 400).json({ error: e.message });
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
