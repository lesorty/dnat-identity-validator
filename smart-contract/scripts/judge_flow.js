/**
 * O Juiz como segundo job, do lado da CVM1 (T-807, T-808, T-809; E14 §3, §4, §10.1, §18.4).
 *
 * Depois que o job de fine-tuning devolve o derivado e a CVM1 o retém (T-803), a CVM1:
 * 1. confere que o Juiz que vai rodar está na lista permitida (judge_allowlist.json, T-808): a
 *    entrada fixa o hash do Juiz, o hash do prereg.yaml congelado e o compromisso da bateria;
 * 2. materializa as entradas num diretório temporário (base, derivado, referência do pai, dataset
 *    do job e prereg), escreve o manifesto dnat.judge-job.v1 com os digests que ela custodia e
 *    roda `python -m model_gate.job` (modo direto; numa CVM de uso único na T-801);
 * 3. lê o resultado: falha do job devolve a reserva da cota (T-107, T-1704); veredito vira recibo
 *    no contrato por registerDerivative (aprovado nasce ativo, os outros inativos e retidos) e a
 *    cota é acertada em 1, 2 ou 5 (T-809).
 *
 * O recibo só é gravado se o verdict.json bate com o que a CVM1 custodia: Juiz, prereg e bateria
 * da lista permitida, digest do derivado retido, contentHash do pai e identidade de quem pediu.
 * Se não bate, nada vai ao contrato, a reserva volta e o registro do derivado leva o alerta.
 */
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");
const { BATTERY_FORMAT, DERIVATIVE_FORMAT, MODEL_FORMAT, REFERENCE_FORMAT, decryptBufferEnvelope, encryptBuffer } = require("./asset_envelope");
const { extractVerified, fileSha256, modelDirDigest, packModelDir } = require("./model_store");
const { getDerivative, updateDerivative } = require("./retention");

const MODEL_GATE_DIR = process.env.DNAT_MODEL_GATE_DIR || path.resolve(__dirname, "..", "..", "model_gate");
const ALLOWLIST_PATH = process.env.DNAT_JUDGE_ALLOWLIST || path.resolve(__dirname, "..", "judge_allowlist.json");
const ALLOWLIST_SCHEMA = "dnat.judge-allowlist.v1";
const JOB_SCHEMA = "dnat.judge-job.v1";
const VERDICT_SCHEMA = "dnat.verdict.v1";
const VERDICT_FILE = "verdict.json";
const RESULT_FILE = "job_result.json";
const HASH_FIELDS = ["parent", "parent_reference", "derivative", "judge", "battery_commitment", "prereg", "dataset", "responses"];
// Verdict do contrato: Pending, Approved, Rejected, Inconclusive.
const VERDICT_ENUM = { aprovado: 1, reprovado: 2, inconclusivo: 3 };
const OUTCOME = { aprovado: "approved", reprovado: "rejected", inconclusivo: "inconclusive" };
const MODEL_ASSET_TYPE = 2;
const HEX64 = /^[0-9a-f]{64}$/;
const EVALUATOR_KINDS = ["guard", "rubric", "detector"];

class JudgeFlowError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.code = code;
    this.details = details;
  }
}

const hex = (v) => String(v ?? "").toLowerCase().replace(/^0x/, "");
const bytes32 = (v) => `0x${hex(v)}`;

// ---------------------------------------------------------------- lista permitida (T-808)

function loadAllowlist(p = ALLOWLIST_PATH) {
  const raw = JSON.parse(fs.readFileSync(p, "utf8"));
  if (raw.schema !== ALLOWLIST_SCHEMA) throw new Error(`${p}: schema ${raw.schema}, esperava ${ALLOWLIST_SCHEMA}`);
  // Além do trio Juiz, prereg e bateria (T-808), a liberação fixa o avaliador e o pacote da
  // bateria que o job usa (T-807): sem eles, os estágios reais não rodam e o job falha.
  const judges = (raw.judges || []).map((j) => ({
    judgeHash: hex(j.judgeHash),
    preregSha256: hex(j.preregSha256),
    batteryCommitment: hex(j.batteryCommitment),
    evaluatorKind: j.evaluatorKind ? String(j.evaluatorKind) : null,
    evaluatorDigest: j.evaluatorDigest ? hex(j.evaluatorDigest) : null,
    batteryPackDigest: j.batteryPackDigest ? hex(j.batteryPackDigest) : null,
    note: String(j.note || ""),
  }));
  for (const j of judges) {
    for (const k of ["judgeHash", "preregSha256", "batteryCommitment"]) {
      if (!HEX64.test(j[k])) throw new Error(`${p}: ${k} inválido em ${JSON.stringify(j)}`);
    }
    for (const k of ["evaluatorDigest", "batteryPackDigest"]) {
      if (j[k] !== null && !HEX64.test(j[k])) throw new Error(`${p}: ${k} inválido em ${JSON.stringify(j)}`);
    }
    if (j.evaluatorKind !== null && !EVALUATOR_KINDS.includes(j.evaluatorKind)) {
      throw new Error(`${p}: evaluatorKind ${j.evaluatorKind} fora de ${EVALUATOR_KINDS}`);
    }
    if ((j.evaluatorKind === "guard" || j.evaluatorKind === "rubric") && !j.evaluatorDigest) {
      throw new Error(`${p}: o avaliador ${j.evaluatorKind} precisa de evaluatorDigest`);
    }
  }
  return judges;
}

function findRelease(allowlist, judgeHash) {
  return allowlist.find((j) => j.judgeHash === hex(judgeHash)) || null;
}

// ---------------------------------------------------------------- execução do job (modo direto)

/** Comando que roda o Python do Juiz: DNAT_JUDGE_CMD (array JSON) ou o ambiente uv do model_gate. */
function judgeCommand(modelGateDir = MODEL_GATE_DIR) {
  if (process.env.DNAT_JUDGE_CMD) return JSON.parse(process.env.DNAT_JUDGE_CMD);
  return ["uv", "run", "--project", modelGateDir, "--frozen", "--quiet", "python"];
}

function computeJudgeHash({ cmd = judgeCommand(), cwd = MODEL_GATE_DIR } = {}) {
  const r = spawnSync(cmd[0], [...cmd.slice(1), "-m", "model_gate.judge_package"], { cwd, encoding: "utf8" });
  if (r.error) throw r.error;
  const out = String(r.stdout).trim();
  if (r.status !== 0 || !HEX64.test(out)) throw new Error(`judge_package falhou (${r.status}): ${String(r.stderr).slice(-300)}`);
  return out;
}

function writeJudgeManifest(manifestPath, { inputs, release, identityId, decidedAt, samplingKey = null }) {
  const doc = {
    schema: JOB_SCHEMA,
    inputs,
    judge_hash: release.judgeHash,
    battery_commitment: release.batteryCommitment,
    identity_id: hex(identityId),
    decided_at: decidedAt,
    ...(release.evaluatorKind ? { evaluator: { kind: release.evaluatorKind } } : {}),
    ...(samplingKey ? { sampling_key: samplingKey } : {}),
  };
  fs.writeFileSync(manifestPath, JSON.stringify(doc, null, 2));
  return doc;
}

function readJobResult(outDir) {
  const p = path.join(outDir, RESULT_FILE);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, "utf8")) : null;
}

/** Roda o job e devolve o job_result.json; sem ele (o processo caiu), devolve uma falha. */
function runJudgeJob({ manifestPath, outDir, cmd = judgeCommand(), cwd = MODEL_GATE_DIR, timeoutMs = 4 * 3600 * 1000 }) {
  return new Promise((resolve) => {
    const child = spawn(cmd[0], [...cmd.slice(1), "-m", "model_gate.job", "--manifest", manifestPath, "--out", outDir], {
      cwd,
      stdio: ["ignore", "ignore", "pipe"],
    });
    let stderr = "";
    child.stderr.on("data", (c) => (stderr = (stderr + c).slice(-2000)));
    const timer = setTimeout(() => child.kill("SIGKILL"), timeoutMs);
    const done = (code, error) => {
      clearTimeout(timer);
      resolve(
        readJobResult(outDir) || {
          status: "failure",
          outcome: "inconclusive_failure",
          error: String(error || `judge job exited ${code}: ${stderr.slice(-400)}`),
        },
      );
    };
    child.on("error", (e) => done(null, e.message));
    child.on("close", (code) => done(code));
  });
}

// ---------------------------------------------------------------- veredito e recibo (T-809)

/** Lê o verdict.json: {doc, sha256 dos bytes}. Confere o esquema mínimo que o recibo usa. */
function readVerdict(p) {
  const raw = fs.readFileSync(p);
  const sha256 = crypto.createHash("sha256").update(raw).digest("hex");
  const doc = JSON.parse(raw.toString("utf8"));
  if (doc.schema !== VERDICT_SCHEMA) throw new JudgeFlowError("bad_verdict", `schema ${doc.schema}`);
  if (!(doc.state in VERDICT_ENUM)) throw new JudgeFlowError("bad_verdict", `state ${doc.state}`);
  for (const k of HASH_FIELDS) {
    if (!HEX64.test(String(doc.hashes?.[k]))) throw new JudgeFlowError("bad_verdict", `hashes.${k}`);
  }
  if (!HEX64.test(String(doc.identity_id))) throw new JudgeFlowError("bad_verdict", "identity_id");
  const t = Date.parse(doc.decided_at);
  if (!/Z$/.test(String(doc.decided_at)) || Number.isNaN(t)) throw new JudgeFlowError("bad_verdict", "decided_at");
  return { doc, sha256 };
}

/** DerivativeInfo do contrato a partir do veredito. */
function receiptFromVerdict(doc, verdictSha256, parentId) {
  const h = doc.hashes;
  return {
    parentId: BigInt(parentId),
    parentReferenceHash: bytes32(h.parent_reference),
    derivativeHash: bytes32(h.derivative),
    judgeHash: bytes32(h.judge),
    batteryCommitment: bytes32(h.battery_commitment),
    preregHash: bytes32(h.prereg),
    datasetHash: bytes32(h.dataset),
    verdictHash: bytes32(verdictSha256),
    identityId: bytes32(doc.identity_id),
    verdict: VERDICT_ENUM[doc.state],
    decidedAt: BigInt(Math.floor(Date.parse(doc.decided_at) / 1000)),
  };
}

/** Diferenças entre o veredito e o que a CVM1 custodia; vazio quando o recibo pode ser gravado. */
function receiptProblems(doc, { allowlist, record, parentContentHash }) {
  const problems = [];
  const release = findRelease(allowlist, doc.hashes.judge);
  if (!release) problems.push("judge_not_allowed");
  else {
    if (doc.hashes.prereg !== release.preregSha256) problems.push("prereg_not_frozen");
    if (doc.hashes.battery_commitment !== release.batteryCommitment) problems.push("battery_commitment");
  }
  if (doc.hashes.derivative !== hex(record.digest)) problems.push("derivative_digest");
  if (doc.hashes.parent !== hex(parentContentHash)) problems.push("parent_hash");
  if (record.identityId && doc.identity_id !== hex(record.identityId)) problems.push("identity");
  return problems;
}

function settleQuota(ledger, reservationId, outcome) {
  if (!ledger || !reservationId) return null;
  return ledger.settle(reservationId, outcome);
}

function registeredId(contract, receipt) {
  for (const log of receipt.logs || []) {
    try {
      const parsed = contract.interface.parseLog(log);
      if (parsed?.name === "DerivativeRegistered") return parsed.args.id;
    } catch {
      // log de outro contrato
    }
  }
  throw new Error("DerivativeRegistered not found in receipt");
}

/**
 * Aplica o resultado do job do Juiz ao derivado retido de executionId: recibo no contrato, cota e
 * registro em derivatives.json. Idempotente: um derivado já registrado não é registrado de novo.
 */
async function applyJudgeResult({
  contract,
  ledger,
  derivativesPath,
  executionId,
  outDir,
  jobResult = null,
  allowlist,
  parentId,
  parentContentHash,
  owner,
  title,
}) {
  const record = getDerivative(derivativesPath, executionId);
  if (!record) throw new JudgeFlowError("not_retained", `derivative of ${executionId} not retained`);
  if (record.assetId) return { outcome: record.verdict, assetId: record.assetId, repeated: true, record };

  const result = jobResult || readJobResult(outDir) || { status: "failure", error: "job_result.json missing" };
  const judgedAtUtc = new Date().toISOString();
  const fail = (alert, extra = {}) => {
    settleQuota(ledger, record.quotaReservationId, "failure");
    const updated = updateDerivative(derivativesPath, executionId, {
      verdict: "failure",
      judgeAlert: alert,
      judgeError: extra.error ? String(extra.error).slice(0, 500) : undefined,
      judgeProblems: extra.problems,
      judgedAtUtc,
    });
    return { outcome: "failure", alert, record: updated, ...extra };
  };

  if (result.status !== "verdict") return fail(result.alert || "judge_failure", { error: result.error });

  let doc;
  let sha256;
  try {
    ({ doc, sha256 } = readVerdict(path.join(outDir, VERDICT_FILE)));
  } catch (e) {
    return fail("bad_verdict", { error: e.message });
  }
  if (result.verdict_sha256 && result.verdict_sha256 !== sha256) return fail("bad_verdict", { error: "verdict hash differs from job_result" });
  const problems = receiptProblems(doc, { allowlist, record, parentContentHash });
  if (problems.length) return fail("receipt_mismatch", { problems });

  const info = receiptFromVerdict(doc, sha256, parentId);
  const tx = await contract.registerDerivative(info, owner, title, record.encryptedUri);
  const receipt = await tx.wait();
  const assetId = registeredId(contract, receipt).toString();
  const outcome = OUTCOME[doc.state];
  settleQuota(ledger, record.quotaReservationId, outcome);
  const updated = updateDerivative(derivativesPath, executionId, {
    verdict: outcome,
    rule: doc.rule,
    reasons: (doc.reasons || []).map((r) => r.code),
    status: outcome === "approved" ? "released" : "retained",
    assetId,
    parentId: String(parentId),
    verdictHash: sha256,
    judgeHash: doc.hashes.judge,
    registeredTx: receipt.hash,
    decidedAt: doc.decided_at,
    judgedAtUtc,
  });
  return { outcome, assetId, verdictHash: sha256, txHash: receipt.hash, record: updated };
}

// ---------------------------------------------------------------- referência do pai (T-312)

/**
 * Referências custodiadas: references.json na pasta de estado da CVM1, {parentId: {encryptedUri,
 * digest, ...}}. A referência real é o S1 do pai medido na nuvem (T-312); quem a deposita é o
 * operador, no host da CVM1 (scripts/reference_cli.js), nunca um usuário pela API.
 */
function readReferences(statePath) {
  return fs.existsSync(statePath) ? JSON.parse(fs.readFileSync(statePath, "utf8")).references || {} : {};
}

async function depositReference({ statePath, parentId, dir, upload, source = "" }) {
  const { digest } = modelDirDigest(dir);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-ref-"));
  try {
    const archive = packModelDir(dir, path.join(tmp, "reference.tar.gz"));
    const cid = await upload(encryptBuffer(fs.readFileSync(archive), { parentId: String(parentId), digest }, REFERENCE_FORMAT));
    if (!cid) throw new Error("upload returned no CID for the reference");
    const refs = readReferences(statePath);
    refs[String(parentId)] = { encryptedUri: `ipfs://${cid}`, digest, source, createdAtUtc: new Date().toISOString() };
    fs.mkdirSync(path.dirname(statePath), { recursive: true });
    fs.writeFileSync(statePath, JSON.stringify({ references: refs }, null, 2));
    return refs[String(parentId)];
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

/**
 * Pacote da bateria custodiado (T-807): battery_pack.json na pasta de estado, {encryptedUri,
 * digest}. O digest é o de diretório (model_store) e tem de bater com batteryPackDigest da
 * liberação. Quem deposita é o operador (judge_cli.js battery).
 */
function readBatteryPack(statePath) {
  return fs.existsSync(statePath) ? JSON.parse(fs.readFileSync(statePath, "utf8")) : null;
}

async function depositBattery({ statePath, dir, upload, source = "" }) {
  const { digest } = modelDirDigest(dir);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-bat-"));
  try {
    const archive = packModelDir(dir, path.join(tmp, "battery.tar.gz"));
    const cid = await upload(encryptBuffer(fs.readFileSync(archive), { digest }, BATTERY_FORMAT));
    if (!cid) throw new Error("upload returned no CID for the battery pack");
    const doc = { encryptedUri: `ipfs://${cid}`, digest, source, createdAtUtc: new Date().toISOString() };
    fs.mkdirSync(path.dirname(statePath), { recursive: true });
    fs.writeFileSync(statePath, JSON.stringify(doc, null, 2));
    return doc;
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

/**
 * Chave do sorteio do S1 (sampling_key), fixa por implantação e guardada só na CVM1: o mesmo
 * derivado tem sempre o mesmo sorteio (não adianta reenviar), e quem treina não o prevê.
 */
function samplingKey(keyPath) {
  if (!fs.existsSync(keyPath)) {
    fs.mkdirSync(path.dirname(keyPath), { recursive: true });
    fs.writeFileSync(keyPath, crypto.randomBytes(32).toString("hex"), { mode: 0o600, flag: "wx" });
  }
  const key = fs.readFileSync(keyPath, "utf8").trim();
  if (!HEX64.test(key)) throw new Error(`${keyPath}: chave do sorteio inválida`);
  return key;
}

// ---------------------------------------------------------------- orquestração

function decryptToDir(envelope, formats, destDir, expectedDigest) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-unpack-"));
  try {
    const archive = path.join(tmp, "a.tar.gz");
    fs.writeFileSync(archive, decryptBufferEnvelope(envelope, formats).plaintext);
    return extractVerified(archive, destDir, expectedDigest);
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

/** Instante do veredito: segundos inteiros em UTC (E14 §4: fixado pela CVM1). */
function decidedAtNow() {
  return new Date(Math.floor(Date.now() / 1000) * 1000).toISOString().replace(".000Z", "Z");
}

/**
 * Roda o Juiz sobre o derivado retido de executionId e aplica o resultado.
 *
 * fetchEnvelope(uri) devolve os bytes cifrados (IPFS). datasetPath é o dataset do job em claro, que
 * só existe no diretório temporário da CVM1 durante o pedido. Qualquer erro antes do job (pai
 * inativo, Juiz fora da lista, referência ausente, digest que não bate) vira falha: a reserva volta.
 */
async function judgeDerivative({
  contract,
  ledger,
  derivativesPath,
  referencesPath,
  batteryPath = null,
  samplingKeyPath = null,
  evaluatorDir = process.env.DNAT_EVALUATOR_DIR || null,
  executionId,
  parentId,
  datasetPath,
  fetchEnvelope,
  allowlist = loadAllowlist(),
  preregPath = path.join(MODEL_GATE_DIR, "prereg.yaml"),
  cmd = judgeCommand(),
  modelGateDir = MODEL_GATE_DIR,
  owner,
  title,
}) {
  const record = getDerivative(derivativesPath, executionId);
  if (!record) throw new JudgeFlowError("not_retained", `derivative of ${executionId} not retained`);
  if (record.assetId) return { outcome: record.verdict, assetId: record.assetId, repeated: true, record };
  const failBeforeJob = (alert, error) =>
    applyJudgeResult({
      contract, ledger, derivativesPath, executionId, outDir: null, allowlist, parentId,
      parentContentHash: null, owner, title,
      jobResult: { status: "failure", alert, error },
    });

  const parent = await contract.getAsset(BigInt(parentId));
  if (Number(parent.assetType) !== MODEL_ASSET_TYPE) return failBeforeJob("parent_not_model", `asset ${parentId} is not a model`);
  if (!parent.active) return failBeforeJob("parent_inactive", `model ${parentId} is inactive`);
  const parentContentHash = hex(parent.contentHash);

  let release;
  try {
    const running = computeJudgeHash({ cmd, cwd: modelGateDir });
    release = findRelease(allowlist, running);
    if (!release) return failBeforeJob("judge_not_allowed", `judge ${running} not in allowlist`);
    if (fileSha256(preregPath) !== release.preregSha256) return failBeforeJob("prereg_not_frozen", "prereg.yaml differs from the allowlist");
  } catch (e) {
    return failBeforeJob("judge_unavailable", e.message);
  }
  const reference = readReferences(referencesPath)[String(parentId)];
  if (!reference) return failBeforeJob("reference_missing", `no custodied reference for model ${parentId} (T-312)`);
  const battery = batteryPath ? readBatteryPack(batteryPath) : null;
  if (release.batteryPackDigest && (!battery || battery.digest !== release.batteryPackDigest)) {
    return failBeforeJob("battery_missing", "battery pack missing or differs from the allowlist (judge_cli.js battery)");
  }
  if (release.evaluatorDigest && !evaluatorDir) {
    return failBeforeJob("evaluator_missing", "DNAT_EVALUATOR_DIR not set for the allowed evaluator");
  }

  const work = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-judge-"));
  try {
    const inputs = {};
    try {
      inputs.base = { path: "base", kind: "dir", digest: parentContentHash };
      decryptToDir(await fetchEnvelope(parent.encryptedUri), [MODEL_FORMAT], path.join(work, "base"), parentContentHash);
      inputs.derivative = { path: "derivative", kind: "dir", digest: hex(record.digest) };
      decryptToDir(await fetchEnvelope(record.encryptedUri), [DERIVATIVE_FORMAT], path.join(work, "derivative"), record.digest);
      inputs.parent_reference = { path: "parent_reference", kind: "dir", digest: reference.digest };
      decryptToDir(await fetchEnvelope(reference.encryptedUri), [REFERENCE_FORMAT], path.join(work, "parent_reference"), reference.digest);
      if (release.batteryPackDigest) {
        inputs.battery = { path: "battery", kind: "dir", digest: release.batteryPackDigest };
        decryptToDir(await fetchEnvelope(battery.encryptedUri), [BATTERY_FORMAT], path.join(work, "battery"), release.batteryPackDigest);
      }
    } catch (e) {
      return failBeforeJob("custody_error", e.message);
    }
    fs.copyFileSync(datasetPath, path.join(work, "dataset.csv"));
    inputs.dataset = { path: "dataset.csv", kind: "file", digest: fileSha256(datasetPath) };
    fs.copyFileSync(preregPath, path.join(work, "prereg.yaml"));
    inputs.prereg = { path: "prereg.yaml", kind: "file", digest: release.preregSha256 };

    if (release.evaluatorDigest) {
      // O avaliador fica no host da CVM1 (vários GB); o job confere o digest antes de carregar.
      inputs.evaluator = { path: path.resolve(evaluatorDir), kind: "dir", digest: release.evaluatorDigest };
    }
    const manifestPath = path.join(work, "job.json");
    writeJudgeManifest(manifestPath, {
      inputs, release, identityId: record.identityId || "0".repeat(64), decidedAt: decidedAtNow(),
      samplingKey: samplingKeyPath ? samplingKey(samplingKeyPath) : null,
    });
    const outDir = path.join(work, "out");
    const jobResult = await runJudgeJob({ manifestPath, outDir, cmd, cwd: modelGateDir });
    return await applyJudgeResult({
      contract, ledger, derivativesPath, executionId, outDir, jobResult, allowlist, parentId, parentContentHash, owner, title,
    });
  } finally {
    // Pesos em claro só existem aqui, durante o job.
    fs.rmSync(work, { recursive: true, force: true });
  }
}

module.exports = {
  ALLOWLIST_PATH,
  JudgeFlowError,
  MODEL_GATE_DIR,
  OUTCOME,
  VERDICT_ENUM,
  applyJudgeResult,
  computeJudgeHash,
  decidedAtNow,
  depositBattery,
  depositReference,
  findRelease,
  judgeCommand,
  judgeDerivative,
  loadAllowlist,
  readBatteryPack,
  readReferences,
  readVerdict,
  receiptFromVerdict,
  receiptProblems,
  runJudgeJob,
  samplingKey,
  writeJudgeManifest,
};
