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

function arg(argv, name, fallback = null) {
  const i = argv.indexOf(name);
  return i >= 0 && i + 1 < argv.length ? argv[i + 1] : fallback;
}

async function ipfsUpload(buffer) {
  const form = new FormData();
  form.append("file", new Blob([buffer]), `reference-${crypto.randomUUID()}.enc`);
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
  else if (cmd === "show") {
    out = { allowlist: readAllowlistFile(flow.ALLOWLIST_PATH), references: flow.readReferences(REFERENCES_PATH),
      batteryPack: flow.readBatteryPack(BATTERY_PACK_PATH) };
  } else throw new Error("usage: judge_cli.js allow|battery|reference|show (see the header of this file)");
  console.log(JSON.stringify(out, null, 2));
}

if (require.main === module) {
  main(process.argv.slice(2)).catch((e) => {
    console.error(e.message);
    process.exit(1);
  });
}

module.exports = { allow, battery, main, reference };
