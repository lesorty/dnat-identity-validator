/**
 * Retenção do derivado na CVM1 (T-803; E14 §3 e §10.2, decisão 5 da T-101).
 *
 * O agente da CVM de job devolve o derivado só à CVM1; run_from_cids.py confere o digest e grava
 * o tar.gz num caminho temporário do plano de controle. Aqui a CVM1:
 * - cifra o pacote com o mesmo envelope dos datasets (AES-256-GCM, chave só na CVM1);
 * - guarda o envelope no IPFS e apaga o pacote em claro;
 * - anota o derivado como retido, com veredito pendente, em derivatives.json, na pasta de
 *   estado da CVM1 (ao lado de executions/ e de identities.json).
 *
 * O registro do derivado no contrato é do executor, com o veredito do Juiz (T-703, T-807).
 * Ao usuário só vai o resumo (digest e estado), nunca os pesos nem o CID do envelope.
 */
const fs = require("node:fs");
const path = require("node:path");
const { DERIVATIVE_FORMAT, encryptBuffer } = require("./asset_envelope");

function readLedger(statePath) {
  if (!fs.existsSync(statePath)) return { derivatives: {} };
  const parsed = JSON.parse(fs.readFileSync(statePath, "utf8"));
  return { derivatives: parsed.derivatives || {} };
}

function writeLedger(statePath, ledger) {
  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  const tmp = `${statePath}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(ledger, null, 2), "utf8");
  fs.renameSync(tmp, statePath);
}

/**
 * Cifra e guarda o derivado. `upload(buffer)` devolve o CID do envelope no IPFS.
 * O pacote em claro é apagado mesmo se a cifra ou o upload falharem.
 */
async function retainDerivative({ archivePath, digest, executionId, statePath, upload, context = {} }) {
  if (!/^[0-9a-f]{64}$/.test(String(digest || ""))) throw new Error("derivative digest must be a SHA-256 hex");
  let cid;
  try {
    const envelope = encryptBuffer(fs.readFileSync(archivePath), { digest, executionId }, DERIVATIVE_FORMAT);
    cid = await upload(envelope);
  } finally {
    fs.rmSync(archivePath, { force: true });
  }
  if (!cid) throw new Error("IPFS upload returned no CID for the derivative");

  const record = {
    executionId,
    digest,
    encryptedUri: `ipfs://${cid}`,
    format: DERIVATIVE_FORMAT,
    status: "retained",
    verdict: "pending",
    retainedAtUtc: new Date().toISOString(),
    ...context,
  };
  const ledger = readLedger(statePath);
  ledger.derivatives[executionId] = record;
  writeLedger(statePath, ledger);
  return record;
}

/** Registro de um derivado retido, ou null. */
function getDerivative(statePath, executionId) {
  return readLedger(statePath).derivatives[executionId] || null;
}

/** Junta campos ao registro do derivado (veredito, asset, recibo; T-809) e devolve o registro novo. */
function updateDerivative(statePath, executionId, patch) {
  const ledger = readLedger(statePath);
  const current = ledger.derivatives[executionId];
  if (!current) throw new Error(`derivative of execution ${executionId} not found`);
  ledger.derivatives[executionId] = { ...current, ...patch };
  writeLedger(statePath, ledger);
  return ledger.derivatives[executionId];
}

/** O que o dono da execução pode ver do derivado: digest, estado, veredito e o asset, se houver. */
function userSummary(record) {
  const out = { digest: record.digest, status: record.status, verdict: record.verdict };
  if (record.assetId) out.assetId = record.assetId;
  return out;
}

module.exports = { getDerivative, readLedger, retainDerivative, updateDerivative, userSummary };
