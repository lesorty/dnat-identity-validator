#!/usr/bin/env node
/**
 * Operador da CVM1, no host (T-808, T-809). Nada disto é rota da API: só quem opera a CVM1 libera
 * um Juiz ou deposita a referência de um pai.
 *
 *   node scripts/judge_cli.js allow --battery-commitment HEX [--prereg CAMINHO] [--note TEXTO]
 *                              [--evaluator-kind guard|rubric|detector] [--evaluator-dir DIR]
 *       Calcula o hash do Juiz do model_gate local e o sha256 do prereg.yaml e grava a liberação na
 *       lista permitida (DNAT_JUDGE_ALLOWLIST, padrão smart-contract/judge_allowlist.json). Fixa
 *       também o avaliador (tipo e digest do diretório) e o pacote da bateria já depositado.
 *   node scripts/judge_cli.js battery --dir DIRETÓRIO [--source TEXTO]
 *       Cifra e guarda no IPFS o pacote da bateria (experiments.battery_pack) e o registra em
 *       DNAT_BATTERY_PACK_PATH (padrão smart-contract/battery_pack.json).
 *   node scripts/judge_cli.js reference --parent ID --dir DIRETÓRIO [--source TEXTO]
 *       Empacota, cifra e guarda no IPFS a referência medida do pai (T-312) e a registra em
 *       DNAT_REFERENCES_PATH (padrão smart-contract/references.json).
 *   node scripts/judge_cli.js show
 *       Mostra a lista permitida e as referências.
 *   node scripts/judge_cli.js record --execution ID --out DIRETÓRIO
 *       Abre o registro do Juiz de uma execução (verdict.json, responses.jsonl, job_result.json), cifrado
 *       no IPFS depois do veredito, conferindo o digest e o hash do verdict.json contra o recibo on-chain.
 *   node scripts/judge_cli.js revoke --asset ID --reason TEXTO
 *       Revoga um derivado (revokeDerivative, só o operador; definitivo). Usa RPC_URL, CONTRACT_ADDRESS e
 *       PRIVATE_KEY, como a CVM1.
 */
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const flow = require("./judge_flow");
const { fileSha256, modelDirDigest } = require("./model_store");

const ROOT = path.resolve(__dirname, "..");
const REFERENCES_PATH = process.env.DNAT_REFERENCES_PATH || path.join(ROOT, "references.json");
const BATTERY_PACK_PATH = process.env.DNAT_BATTERY_PACK_PATH || path.join(ROOT, "battery_pack.json");
const IPFS_API_URL = process.env.IPFS_API_URL || "http://localhost:5001";
const DERIVATIVES_PATH = process.env.DNAT_DERIVATIVES_PATH || path.join(ROOT, "derivatives.json");
const RPC_URL = process.env.RPC_URL || "http://127.0.0.1:8545";
const CONTRACT_ADDRESS = process.env.CONTRACT_ADDRESS || "0x5FbDB2315678afecb367f032d93F642f64180aa3";
const PRIVATE_KEY = process.env.PRIVATE_KEY || "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
const OPERATOR_ABI = [
  "function revokeDerivative(uint256 assetId, string reason)",
  "function derivativeRevoked(uint256 assetId) view returns (bool)",
  "function isDerivativeUsable(uint256 assetId) view returns (bool)",
  "function getDerivative(uint256 assetId) view returns ((uint256 parentId, bytes32 parentReferenceHash, bytes32 derivativeHash, bytes32 judgeHash, bytes32 batteryCommitment, bytes32 preregHash, bytes32 datasetHash, bytes32 verdictHash, bytes32 identityId, uint8 verdict, uint64 decidedAt))",
];

function operatorContract() {
  const { ethers } = require("ethers");
  const provider = new ethers.JsonRpcProvider(RPC_URL);
  return new ethers.Contract(CONTRACT_ADDRESS, OPERATOR_ABI, new ethers.Wallet(PRIVATE_KEY, provider));
}

// CID -> arquivo, pela API do IPFS (o mesmo nó da CVM1).
async function ipfsDownload(uri, dest) {
  const cid = String(uri).replace(/^ipfs:\/\//, "");
  const res = await fetch(`${IPFS_API_URL.replace(/\/$/, "")}/api/v0/cat?arg=${encodeURIComponent(cid)}`, { method: "POST" });
  if (!res.ok) throw new Error(`IPFS download failed (${res.status}) for ${cid}`);
  fs.writeFileSync(dest, Buffer.from(await res.arrayBuffer()));
}

async function record(argv) {
  const execution = arg(argv, "--execution");
  const out = arg(argv, "--out");
  if (!execution || !out) throw new Error("--execution ID and --out DIRECTORY are required");
  const { getDerivative } = require("./retention");
  const rec = getDerivative(DERIVATIVES_PATH, execution);
  if (!rec) throw new Error(`no retained derivative for execution ${execution}`);
  const jr = await flow.openJudgeRecord(rec, ipfsDownload, path.resolve(out));
  const verdictFile = path.join(path.resolve(out), "verdict.json");
  const verdictSha = fs.existsSync(verdictFile) ? fileSha256(verdictFile) : null;
  let onChain = null;
  if (rec.assetId) {
    const info = await operatorContract().getDerivative(BigInt(rec.assetId));
    onChain = String(info.verdictHash).replace(/^0x/, "");
  }
  return { execution, out: path.resolve(out), digest: jr.digest, files: jr.files, verdictSha256: verdictSha,
    receiptVerdictHash: onChain, matchesReceipt: onChain ? onChain === verdictSha : null };
}

async function revoke(argv) {
  const asset = arg(argv, "--asset");
  const reason = String(arg(argv, "--reason", "")).trim();
  if (!asset || !reason) throw new Error("--asset ID and --reason TEXT are required");
  const c = operatorContract();
  const receipt = await (await c.revokeDerivative(BigInt(asset), reason)).wait();
  return { asset, reason, tx: receipt.hash, revoked: await c.derivativeRevoked(BigInt(asset)), usable: await c.isDerivativeUsable(BigInt(asset)) };
}

function arg(argv, name, fallback = null) {
  const i = argv.indexOf(name);
  return i >= 0 && i + 1 < argv.length ? argv[i + 1] : fallback;
}

// Envelope em arquivo -> CID (T-805: lido em fluxo pelo fetch).
async function ipfsUpload(envelopePath) {
  const form = new FormData();
  form.append("file", await fs.openAsBlob(envelopePath), `envelope-${crypto.randomUUID()}.enc`);
  const res = await fetch(`${IPFS_API_URL.replace(/\/$/, "")}/api/v0/add?pin=true`, { method: "POST", body: form });
  const raw = await res.text();
  if (!res.ok) throw new Error(`IPFS upload failed (${res.status}): ${raw}`);
  return JSON.parse(raw.trim().split("\n").pop()).Hash;
}

function readAllowlistFile(p) {
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, "utf8")) : { schema: "dnat.judge-allowlist.v1", judges: [] };
}

function allow(argv) {
  const battery = String(arg(argv, "--battery-commitment", "")).toLowerCase().replace(/^0x/, "");
  if (!/^[0-9a-f]{64}$/.test(battery)) throw new Error("--battery-commitment HEX (64 hex) is required");
  const prereg = path.resolve(arg(argv, "--prereg", path.join(flow.MODEL_GATE_DIR, "prereg.yaml")));
  const kind = arg(argv, "--evaluator-kind", null);
  const evaluatorDir = arg(argv, "--evaluator-dir", null);
  if ((kind === "guard" || kind === "rubric") && !evaluatorDir) throw new Error(`--evaluator-dir is required for ${kind}`);
  const pack = flow.readBatteryPack(BATTERY_PACK_PATH);
  const entry = {
    judgeHash: flow.computeJudgeHash(),
    preregSha256: fileSha256(prereg),
    // A CVM1 lê este arquivo no job; dentro do model_gate fica relativo, para valer no container.
    preregPath: prereg.startsWith(flow.MODEL_GATE_DIR + path.sep) ? path.relative(flow.MODEL_GATE_DIR, prereg) : prereg,
    batteryCommitment: battery,
    ...(kind ? { evaluatorKind: kind } : {}),
    ...(evaluatorDir ? { evaluatorDigest: modelDirDigest(path.resolve(evaluatorDir)).digest } : {}),
    ...(pack ? { batteryPackDigest: pack.digest } : {}),
    note: String(arg(argv, "--note", "")),
    allowedAtUtc: new Date().toISOString(),
  };
  const doc = readAllowlistFile(flow.ALLOWLIST_PATH);
  doc.judges = doc.judges.filter((j) => j.judgeHash !== entry.judgeHash).concat([entry]);
  fs.writeFileSync(flow.ALLOWLIST_PATH, JSON.stringify(doc, null, 2) + "\n");
  flow.loadAllowlist(flow.ALLOWLIST_PATH); // confere o que foi gravado
  return entry;
}

async function reference(argv) {
  const parent = arg(argv, "--parent");
  const dir = arg(argv, "--dir");
  if (!parent || !dir) throw new Error("--parent ID and --dir DIRECTORY are required");
  return flow.depositReference({
    statePath: REFERENCES_PATH,
    parentId: parent,
    dir: path.resolve(dir),
    upload: ipfsUpload,
    source: String(arg(argv, "--source", "")),
  });
}

async function battery(argv) {
  const dir = arg(argv, "--dir");
  if (!dir) throw new Error("--dir DIRECTORY is required");
  return flow.depositBattery({ statePath: BATTERY_PACK_PATH, dir: path.resolve(dir), upload: ipfsUpload, source: String(arg(argv, "--source", "")) });
}

async function main(argv) {
  const cmd = argv[0];
  let out;
  if (cmd === "allow") out = allow(argv);
  else if (cmd === "battery") out = await battery(argv);
  else if (cmd === "reference") out = await reference(argv);
  else if (cmd === "record") out = await record(argv);
  else if (cmd === "revoke") out = await revoke(argv);
  else if (cmd === "show") {
    out = { allowlist: readAllowlistFile(flow.ALLOWLIST_PATH), references: flow.readReferences(REFERENCES_PATH),
      batteryPack: flow.readBatteryPack(BATTERY_PACK_PATH) };
  } else throw new Error("usage: judge_cli.js allow|battery|reference|show|record|revoke (see the header of this file)");
  console.log(JSON.stringify(out, null, 2));
}

if (require.main === module) {
  main(process.argv.slice(2)).catch((e) => {
    console.error(e.message);
    process.exit(1);
  });
}

module.exports = { allow, battery, main, record, reference, revoke };
