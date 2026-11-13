/* T-808 e T-809: o Juiz como segundo job do lado da CVM1 — lista permitida, recibo no contrato e cota. */
const assert = require("node:assert");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const { ethers } = require("hardhat");
const { IdentityRegistry, RESERVE_COST } = require("../scripts/identity");
const { getDerivative, retainDerivative } = require("../scripts/retention");
const { MODEL_FORMAT, encryptBuffer } = require("../scripts/asset_envelope");
const { modelDirDigest, packModelDir, safeExtractTarGz } = require("../scripts/model_store");
const flow = require("../scripts/judge_flow");

const AssetType = { Model: 2 };
const sha = (s) => crypto.createHash("sha256").update(s).digest("hex");
const tmp = (p) => fs.mkdtempSync(path.join(os.tmpdir(), `dnat-jf-${p}-`));
const parsed = (c, r, name) => r.logs.map((l) => { try { return c.interface.parseLog(l); } catch { return null; } }).find((e) => e && e.name === name);

const JUDGE = sha("juiz auditado");
const PREREG = sha("prereg congelado");
const BATTERY = sha("compromisso da bateria");
const ALLOW = [{ judgeHash: JUDGE, preregSha256: PREREG, batteryCommitment: BATTERY, note: "teste" }];

function modelDir(seed) {
  const d = tmp("model");
  fs.writeFileSync(path.join(d, "config.json"), JSON.stringify({ seed }));
  fs.writeFileSync(path.join(d, "model.safetensors"), crypto.createHash("sha512").update(String(seed)).digest());
  fs.writeFileSync(path.join(d, "README.md"), "fora do digest");
  return d;
}

function verdictDoc({ state = "aprovado", parent, derivative, identity, judge = JUDGE, prereg = PREREG }) {
  return {
    schema: "dnat.verdict.v1",
    state,
    rule: state === "aprovado" ? "-" : "1",
    reasons: state === "aprovado" ? [] : [{ code: "harm_veto" }],
    instruments: { s1: [], integrity: [], guards: [], second_line: [] },
    measures: { n_tests: 0, s1: [], signals: [], utility: null },
    thresholds: null,
    hashes: {
      parent, parent_reference: sha("ref"), derivative, judge, battery_commitment: BATTERY,
      prereg, dataset: sha("dataset"), responses: sha("respostas"),
    },
    identity_id: identity,
    decided_at: "2026-11-13T12:00:00Z",
  };
}

function writeOut(doc) {
  const out = tmp("out");
  const bytes = Buffer.from(JSON.stringify(doc));
  fs.writeFileSync(path.join(out, "verdict.json"), bytes);
  fs.writeFileSync(path.join(out, "job_result.json"), JSON.stringify({ status: "verdict", state: doc.state, verdict_sha256: sha(bytes) }));
  return { out, verdictSha: sha(bytes) };
}

describe("model_store.js: digest e extração (T-809)", function () {
  it("o digest do diretório é o mesmo do model_gate.io.digest (Python)", function () {
    const d = modelDir(1);
    fs.mkdirSync(path.join(d, "sub"));
    fs.writeFileSync(path.join(d, "sub", "tokenizer.json"), "{}");
    fs.writeFileSync(path.join(d, ".oculto"), "x");
    const node = modelDirDigest(d).digest;
    const mg = path.resolve(__dirname, "..", "..", "model_gate");
    const r = spawnSync("uv", ["run", "--project", mg, "--frozen", "--quiet", "python", "-c",
      "import sys; from pathlib import Path; from model_gate.io.load import dir_digest; print(dir_digest(Path(sys.argv[1]))[0])", d],
    { cwd: mg, encoding: "utf8" });
    if (r.error) this.skip();
    assert.strictEqual(r.status, 0, r.stderr);
    assert.strictEqual(node, r.stdout.trim());
  });

  it("empacota e extrai de volta com o mesmo digest; recusa link e caminho para fora", function () {
    const d = modelDir(2);
    const archive = path.join(tmp("pack"), "m.tar.gz");
    packModelDir(d, archive);
    const back = path.join(tmp("x"), "m");
    safeExtractTarGz(archive, back);
    assert.strictEqual(modelDirDigest(back).digest, modelDirDigest(d).digest);

    const evil = tmp("evil");
    fs.symlinkSync("/etc/passwd", path.join(evil, "link"));
    const bad = path.join(tmp("bad"), "b.tar.gz");
    spawnSync("tar", ["-czf", bad, "-C", evil, "link"]);
    assert.throws(() => safeExtractTarGz(bad, tmp("y")), /unsafe archive entry/);
    const dotdot = path.join(tmp("bad2"), "c.tar.gz");
    spawnSync("tar", ["-czf", dotdot, "-P", "--transform", "s,^,../,", "-C", d, "config.json"]);
    assert.throws(() => safeExtractTarGz(dotdot, tmp("z")), /unsafe archive path/);
  });
});

describe("judge_flow.js: veredito vira recibo e acerta a cota (T-808, T-809)", function () {
  let contract;
  let operator;
  let user;
  let parentId;
  let parentDigest;
  let registry;
  let identity;
  let derivativesPath;
  let derivativeDigest;
  let executionId;
  let reservationId;

  const balance = () => registry.summary(identity.id).balance;
  const apply = (out, extra = {}) =>
    flow.applyJudgeResult({
      contract: contract.connect(operator), ledger: registry, derivativesPath, executionId, outDir: out,
      allowlist: ALLOW, parentId, parentContentHash: parentDigest, owner: user.address, title: "derivado", ...extra,
    });

  beforeEach(async function () {
    [, operator, user] = await ethers.getSigners();
    contract = await ethers.deployContract("DnatMarketplace", [operator.address]);
    parentDigest = modelDirDigest(modelDir("base")).digest;
    const r = await (await contract.connect(user)
      .registerAsset(AssetType.Model, "base", "", "ipfs://base", "ipfs://bm", `0x${parentDigest}`, 0n, "0x")).wait();
    parentId = parsed(contract, r, "AssetRegistered").args.id;

    registry = new IdentityRegistry({ statePath: path.join(tmp("id"), "identities.json"), difficulty: 0 });
    const { publicKey } = crypto.generateKeyPairSync("ed25519");
    identity = registry.register({ publicKey: Buffer.from(publicKey.export({ format: "jwk" }).x, "base64url").toString("hex"), nonce: "0" });
    reservationId = crypto.randomUUID();
    registry.reserve(identity.id, reservationId);

    const der = modelDir("derivado");
    derivativeDigest = modelDirDigest(der).digest;
    const archive = path.join(tmp("a"), "d.tar.gz");
    packModelDir(der, archive);
    derivativesPath = path.join(tmp("state"), "derivatives.json");
    executionId = `exec_${crypto.randomUUID().slice(0, 8)}`;
    await retainDerivative({
      archivePath: archive, digest: derivativeDigest, executionId, statePath: derivativesPath,
      upload: async () => "QmDerivado", context: { identityId: identity.id, quotaReservationId: reservationId },
    });
  });

  it("aprovado: recibo no contrato com os hashes do verdict.json, derivado usável, cota 1", async function () {
    const doc = verdictDoc({ parent: parentDigest, derivative: derivativeDigest, identity: identity.id });
    const { out, verdictSha } = writeOut(doc);
    const res = await apply(out);
    assert.strictEqual(res.outcome, "approved");
    const id = BigInt(res.assetId);
    assert.strictEqual(await contract.isDerivativeUsable(id), true);
    const info = await contract.getDerivative(id);
    assert.strictEqual(info.verdictHash, `0x${verdictSha}`);
    assert.strictEqual(info.derivativeHash, `0x${derivativeDigest}`);
    assert.strictEqual(info.judgeHash, `0x${JUDGE}`);
    assert.strictEqual(info.identityId, `0x${identity.id}`);
    assert.strictEqual(info.decidedAt, BigInt(Date.parse("2026-11-13T12:00:00Z") / 1000));
    const asset = await contract.getAsset(id);
    assert.strictEqual(asset.owner, user.address);
    assert.strictEqual(asset.encryptedUri, "ipfs://QmDerivado");
    assert.strictEqual(balance(), 20 - 1);
    const rec = getDerivative(derivativesPath, executionId);
    assert.deepStrictEqual([rec.status, rec.verdict, rec.assetId, rec.verdictHash], ["released", "approved", res.assetId, verdictSha]);

    // de novo: não registra outra vez nem cobra de novo
    const again = await apply(out);
    assert.strictEqual(again.repeated, true);
    assert.strictEqual(await contract.nextAssetId(), id);
    assert.strictEqual(balance(), 19);
  });

  it("reprovado e inconclusivo: recibo gravado, derivado inativo e retido, cota 5 e 2", async function () {
    const { out } = writeOut(verdictDoc({ state: "reprovado", parent: parentDigest, derivative: derivativeDigest, identity: identity.id }));
    const res = await apply(out);
    assert.strictEqual(res.outcome, "rejected");
    assert.strictEqual((await contract.getAsset(BigInt(res.assetId))).active, false);
    assert.strictEqual((await contract.getDerivative(BigInt(res.assetId))).verdict, 2n);
    assert.strictEqual(getDerivative(derivativesPath, executionId).status, "retained");
    assert.strictEqual(balance(), 20 - 5);

    const r2 = crypto.randomUUID();
    registry.reserve(identity.id, r2);
    const exec2 = `${executionId}_2`;
    const archive = path.join(tmp("a"), "d.tar.gz");
    packModelDir(modelDir("derivado"), archive);
    await retainDerivative({ archivePath: archive, digest: derivativeDigest, executionId: exec2, statePath: derivativesPath,
      upload: async () => "QmD2", context: { identityId: identity.id, quotaReservationId: r2 } });
    const { out: out2 } = writeOut(verdictDoc({ state: "inconclusivo", parent: parentDigest, derivative: derivativeDigest, identity: identity.id }));
    const res2 = await apply(out2, { executionId: exec2 });
    assert.strictEqual(res2.outcome, "inconclusive");
    assert.strictEqual((await contract.getAsset(BigInt(res2.assetId))).active, false);
    assert.strictEqual(balance(), 20 - 5 - 2);
  });

  it("Juiz fora da lista, prereg diferente ou derivado trocado: nada vai ao contrato e a reserva volta", async function () {
    const cases = [
      [{ judge: sha("outro juiz") }, "judge_not_allowed"],
      [{ prereg: sha("prereg editado") }, "prereg_not_frozen"],
      [{ derivative: sha("outro derivado") }, "derivative_digest"],
      [{ parent: sha("outro pai") }, "parent_hash"],
      [{ identity: sha("outra identidade") }, "identity"],
    ];
    for (const [over, problem] of cases) {
      const rid = crypto.randomUUID();
      registry.reserve(identity.id, rid);
      const exec = `${executionId}_${problem}`;
      const archive = path.join(tmp("a"), "d.tar.gz");
      packModelDir(modelDir("derivado"), archive);
      await retainDerivative({ archivePath: archive, digest: derivativeDigest, executionId: exec, statePath: derivativesPath,
        upload: async () => "Qm", context: { identityId: identity.id, quotaReservationId: rid } });
      const { out } = writeOut(verdictDoc({ parent: parentDigest, derivative: derivativeDigest, identity: identity.id, ...over }));
      const res = await apply(out, { executionId: exec });
      assert.strictEqual(res.outcome, "failure");
      assert.strictEqual(res.alert, "receipt_mismatch");
      assert.deepStrictEqual(res.problems, [problem]);
    }
    assert.strictEqual(await contract.nextAssetId(), parentId);
    assert.strictEqual(registry.summary(identity.id).counts.failure, cases.length);
    // só a reserva do beforeEach segue presa
    assert.strictEqual(balance(), 20 - RESERVE_COST);
  });

  it("falha do job do Juiz: sem recibo, reserva devolvida, alerta no registro do derivado", async function () {
    const out = tmp("fail");
    fs.writeFileSync(path.join(out, "job_result.json"), JSON.stringify({ status: "failure", outcome: "inconclusive_failure", error: "StageNotReady: S1" }));
    const res = await apply(out);
    assert.deepStrictEqual([res.outcome, res.alert], ["failure", "judge_failure"]);
    assert.strictEqual(balance(), 20);
    const rec = getDerivative(derivativesPath, executionId);
    assert.deepStrictEqual([rec.verdict, rec.status], ["failure", "retained"]);
    assert.match(rec.judgeError, /StageNotReady/);
  });
});

describe("judge_flow.js: judgeDerivative de ponta a ponta com um Juiz falso (T-809)", function () {
  // "python" falso: responde ao hash do pacote e roda um job que escreve verdict.json pelo manifesto.
  const FAKE = `
const fs = require("node:fs"), path = require("node:path"), crypto = require("node:crypto");
const a = process.argv.slice(2);
if (a[1] === "model_gate.judge_package") { console.log(process.env.FAKE_JUDGE_HASH); process.exit(0); }
const m = JSON.parse(fs.readFileSync(a[a.indexOf("--manifest") + 1], "utf8"));
const out = a[a.indexOf("--out") + 1];
fs.mkdirSync(out, { recursive: true });
for (const [k, v] of Object.entries(m.inputs)) if (!fs.existsSync(path.resolve(path.dirname(a[a.indexOf("--manifest") + 1]), v.path))) process.exit(3);
if (process.env.FAKE_REQUIRE && (!m.inputs.battery || !/^[0-9a-f]{64}$/.test(m.sampling_key || "") || m.evaluator?.kind !== "detector"
  || !fs.existsSync(path.join(path.dirname(a[a.indexOf("--manifest") + 1]), "battery", "battery.json")))) process.exit(4);
if (process.env.FAKE_JUDGE_STATE === "falha") {
  fs.writeFileSync(path.join(out, "job_result.json"), JSON.stringify({ status: "failure", outcome: "inconclusive_failure", error: "StageNotReady" }));
  process.exit(2);
}
const i = m.inputs;
const doc = { schema: "dnat.verdict.v1", state: process.env.FAKE_JUDGE_STATE, rule: "-", reasons: [],
  instruments: { s1: [], integrity: [], guards: [], second_line: [] }, measures: { n_tests: 0, s1: [], signals: [], utility: null },
  thresholds: null, hashes: { parent: i.base.digest, parent_reference: i.parent_reference.digest, derivative: i.derivative.digest,
  judge: m.judge_hash, battery_commitment: m.battery_commitment, prereg: i.prereg.digest, dataset: i.dataset.digest,
  responses: "0".repeat(64) }, identity_id: m.identity_id, decided_at: m.decided_at };
const b = Buffer.from(JSON.stringify(doc));
fs.writeFileSync(path.join(out, "verdict.json"), b);
fs.writeFileSync(path.join(out, "job_result.json"), JSON.stringify({ status: "verdict", state: doc.state,
  verdict_sha256: crypto.createHash("sha256").update(b).digest("hex") }));
`;
  let contract;
  let operator;
  let user;
  let store;
  let state;
  let cmd;
  let prereg;
  let allow;

  const upload = async (buf) => {
    const cid = `Qm${sha(buf).slice(0, 16)}`;
    store.set(cid, buf);
    return cid;
  };
  const fetchEnvelope = async (uri) => {
    const b = store.get(String(uri).replace("ipfs://", ""));
    if (!b) throw new Error(`not found ${uri}`);
    return b;
  };

  async function setup({ withReference = true } = {}) {
    [, operator, user] = await ethers.getSigners();
    contract = await ethers.deployContract("DnatMarketplace", [operator.address]);
    store = new Map();
    state = tmp("state");
    const base = modelDir("base");
    const archive = path.join(tmp("a"), "b.tar.gz");
    packModelDir(base, archive);
    const baseCid = await upload(encryptBuffer(fs.readFileSync(archive), {}, MODEL_FORMAT));
    const r = await (await contract.connect(user).registerAsset(AssetType.Model, "base", "", `ipfs://${baseCid}`, "", `0x${modelDirDigest(base).digest}`, 0n, "0x")).wait();
    const parentId = parsed(contract, r, "AssetRegistered").args.id;
    if (withReference) {
      const ref = tmp("ref");
      fs.writeFileSync(path.join(ref, "reference.json"), '{"anchors": []}');
      await flow.depositReference({ statePath: path.join(state, "references.json"), parentId, dir: ref, upload, source: "teste" });
    }
    const der = modelDir("derivado");
    const darch = path.join(tmp("a"), "d.tar.gz");
    packModelDir(der, darch);
    const registry = new IdentityRegistry({ statePath: path.join(state, "identities.json"), difficulty: 0 });
    const { publicKey } = crypto.generateKeyPairSync("ed25519");
    const id = registry.register({ publicKey: Buffer.from(publicKey.export({ format: "jwk" }).x, "base64url").toString("hex"), nonce: "0" });
    const rid = crypto.randomUUID();
    registry.reserve(id.id, rid);
    const derivativesPath = path.join(state, "derivatives.json");
    await retainDerivative({ archivePath: darch, digest: modelDirDigest(der).digest, executionId: "e1", statePath: derivativesPath,
      upload, context: { identityId: id.id, quotaReservationId: rid } });
    const fake = path.join(tmp("fake"), "fake_python.js");
    fs.writeFileSync(fake, FAKE);
    cmd = [process.execPath, fake];
    prereg = path.join(tmp("p"), "prereg.yaml");
    fs.writeFileSync(prereg, "versao: teste\n");
    allow = [{ judgeHash: JUDGE, preregSha256: sha(fs.readFileSync(prereg)), batteryCommitment: BATTERY }];
    const dataset = path.join(tmp("ds"), "dataset.csv");
    fs.writeFileSync(dataset, "prompt,response\nhi,ok\n");
    return { parentId, registry, id, derivativesPath, dataset };
  }

  const judge = (s, extra = {}) => flow.judgeDerivative({
    contract: contract.connect(operator), ledger: s.registry, derivativesPath: s.derivativesPath,
    referencesPath: path.join(state, "references.json"), executionId: "e1", parentId: s.parentId, datasetPath: s.dataset,
    fetchEnvelope, allowlist: allow, preregPath: prereg, cmd, modelGateDir: state, owner: user.address, title: "derivado", ...extra,
  });

  afterEach(function () {
    delete process.env.FAKE_JUDGE_HASH;
    delete process.env.FAKE_JUDGE_STATE;
  });

  it("aprovado: decifra base, derivado e referência, roda o job e grava o recibo", async function () {
    const s = await setup();
    process.env.FAKE_JUDGE_HASH = JUDGE;
    process.env.FAKE_JUDGE_STATE = "aprovado";
    const res = await judge(s);
    assert.strictEqual(res.outcome, "approved", JSON.stringify(res));
    assert.strictEqual(await contract.isDerivativeUsable(BigInt(res.assetId)), true);
    assert.strictEqual(s.registry.summary(s.id.id).balance, 19);
  });

  it("Juiz em execução fora da lista: nem roda o job; reserva volta", async function () {
    const s = await setup();
    process.env.FAKE_JUDGE_HASH = sha("juiz não auditado");
    process.env.FAKE_JUDGE_STATE = "aprovado";
    const res = await judge(s);
    assert.deepStrictEqual([res.outcome, res.alert], ["failure", "judge_not_allowed"]);
    assert.strictEqual(s.registry.summary(s.id.id).balance, 20);
  });

  it("sem referência custodiada do pai (T-312): falha antes do job", async function () {
    const s = await setup({ withReference: false });
    process.env.FAKE_JUDGE_HASH = JUDGE;
    const res = await judge(s);
    assert.deepStrictEqual([res.outcome, res.alert], ["failure", "reference_missing"]);
  });

  it("job que falha (estágio que ainda não existe): reserva volta, sem recibo", async function () {
    const s = await setup();
    process.env.FAKE_JUDGE_HASH = JUDGE;
    process.env.FAKE_JUDGE_STATE = "falha";
    const res = await judge(s);
    assert.deepStrictEqual([res.outcome, res.alert], ["failure", "judge_failure"]);
    assert.strictEqual(await contract.nextAssetId(), s.parentId);
  });

  it("liberação com avaliador e pacote da bateria: o job recebe a bateria, o tipo do avaliador e a chave do sorteio", async function () {
    const s = await setup();
    const pack = tmp("pack");
    fs.writeFileSync(path.join(pack, "battery.json"), JSON.stringify({ schema: "dnat.battery-pack.v1" }));
    const packState = path.join(state, "battery_pack.json");
    const dep = await flow.depositBattery({ statePath: packState, dir: pack, upload });
    allow = [{ ...allow[0], evaluatorKind: "detector", batteryPackDigest: dep.digest }];
    process.env.FAKE_JUDGE_HASH = JUDGE;
    process.env.FAKE_JUDGE_STATE = "aprovado";
    process.env.FAKE_REQUIRE = "1";
    try {
      const keyPath = path.join(state, "sampling_key");
      const res = await judge(s, { batteryPath: packState, samplingKeyPath: keyPath });
      assert.strictEqual(res.outcome, "approved", JSON.stringify(res));
      const key = fs.readFileSync(keyPath, "utf8");
      assert.match(key, /^[0-9a-f]{64}$/);
      assert.strictEqual(fs.statSync(keyPath).mode & 0o777, 0o600);
      assert.strictEqual(flow.samplingKey(keyPath), key); // fixa por implantação
    } finally {
      delete process.env.FAKE_REQUIRE;
    }
  });

  it("pacote da bateria ausente ou diferente do liberado: falha antes do job", async function () {
    const s = await setup();
    allow = [{ ...allow[0], batteryPackDigest: sha("outro pacote") }];
    process.env.FAKE_JUDGE_HASH = JUDGE;
    const res = await judge(s, { batteryPath: path.join(state, "nao_existe.json") });
    assert.deepStrictEqual([res.outcome, res.alert], ["failure", "battery_missing"]);
  });

  it("lista permitida: avaliador com modelo exige digest; tipo desconhecido é recusado", function () {
    const p = path.join(tmp("al"), "a.json");
    const base = { judgeHash: JUDGE, preregSha256: PREREG, batteryCommitment: BATTERY };
    fs.writeFileSync(p, JSON.stringify({ schema: "dnat.judge-allowlist.v1", judges: [{ ...base, evaluatorKind: "guard" }] }));
    assert.throws(() => flow.loadAllowlist(p), /evaluatorDigest/);
    fs.writeFileSync(p, JSON.stringify({ schema: "dnat.judge-allowlist.v1", judges: [{ ...base, evaluatorKind: "gpt" }] }));
    assert.throws(() => flow.loadAllowlist(p), /evaluatorKind/);
    fs.writeFileSync(p, JSON.stringify({ schema: "dnat.judge-allowlist.v1", judges: [{ ...base, evaluatorKind: "guard", evaluatorDigest: sha("g") }] }));
    assert.strictEqual(flow.loadAllowlist(p)[0].evaluatorDigest, sha("g"));
  });

  it("pai revogado antes do Juiz: falha sem rodar", async function () {
    const s = await setup();
    await (await contract.connect(user).revokeAsset(s.parentId)).wait();
    process.env.FAKE_JUDGE_HASH = JUDGE;
    const res = await judge(s);
    assert.deepStrictEqual([res.outcome, res.alert], ["failure", "parent_inactive"]);
  });
});
