/* T-803: o derivado volta só à CVM1, cifrado no IPFS, e nunca entra na saída do job.
 *
 * Sem CVM real: o agente é o vm_runtime/derivative.py de verdade, o executor é um servidor HTTP
 * falso que devolve a resposta no formato de run-direct.sh, o run_from_cids.py é o de verdade e o
 * IPFS é uma função de upload falsa.
 */
const assert = require("node:assert");
const crypto = require("node:crypto");
const fs = require("node:fs");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");
const { DERIVATIVE_FORMAT, decryptBufferEnvelope } = require("../scripts/asset_envelope");
const { readLedger, retainDerivative, userSummary } = require("../scripts/retention");

const ROOT = path.join(__dirname, "..", "..");
const AGENT = path.join(ROOT, "vm_runtime", "derivative.py");
const RUNNER = path.join(__dirname, "..", "scripts", "run_from_cids.py");
const PYTHON = process.env.PYTHON || "python3";
const MARKER = "PESOS-DO-DERIVADO-NAO-PODEM-SAIR";

function run(cmd, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" } });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (c) => (stdout += c));
    child.stderr.on("data", (c) => (stderr += c));
    child.on("error", reject);
    child.on("close", (code) => resolve({ code, stdout, stderr }));
  });
}

/** Derivado de mentira gravado pelo "job" e coletado pelo agente real. */
async function agentCollect(tmp) {
  const dir = path.join(tmp, "workspace", "derivative");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "adapter_model.safetensors"), Buffer.concat([Buffer.from(MARKER), crypto.randomBytes(4096)]));
  fs.writeFileSync(path.join(dir, "adapter_config.json"), '{"r": 8}');
  const { code, stdout, stderr } = await run(PYTHON, [AGENT, path.join(tmp, "workspace")]);
  assert.strictEqual(code, 0, stderr);
  assert.ok(!fs.existsSync(dir), "o agente apaga o derivado do disco do job");
  return JSON.parse(stdout);
}

/** Executor falso: responde como executor.py + run-direct.sh. */
function fakeExecutor(response) {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      req.resume();
      req.on("end", () => {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify(response));
      });
    });
    server.listen(0, "127.0.0.1", () => resolve(server));
  });
}

async function runJob(tmp, response, { derivativeOut = true } = {}) {
  const server = await fakeExecutor(response);
  try {
    const datasetPath = path.join(tmp, "dataset.csv");
    const artifactPath = path.join(tmp, "application.ext4");
    fs.writeFileSync(datasetPath, "a,b\n1,2\n");
    fs.writeFileSync(artifactPath, "ext4-falso");
    const archivePath = path.join(tmp, "prep", "derivative.tar.gz");
    const args = [
      RUNNER,
      "--local-dataset-path", datasetPath,
      "--application-artifact-path", artifactPath,
      "--executor-url", `http://127.0.0.1:${server.address().port}`,
      "--executions-dir", path.join(tmp, "executions"),
    ];
    if (derivativeOut) args.push("--derivative-out", archivePath);
    const { code, stdout, stderr } = await run(PYTHON, args);
    const metadata = JSON.parse(stdout);
    const executionDir = path.join(tmp, "executions", metadata.executionId);
    return { code, stderr, metadata, executionDir, archivePath };
  } finally {
    server.close();
  }
}

function assertNoWeights(executionDir, derivative) {
  const archiveB64 = derivative.archive;
  for (const name of fs.readdirSync(executionDir)) {
    const p = path.join(executionDir, name);
    if (!fs.statSync(p).isFile() || name === "bundle.tar.gz" || name.endsWith(".ext4") || name.endsWith(".csv")) continue;
    const text = fs.readFileSync(p, "latin1");
    assert.ok(!text.includes(MARKER), `${name} contém os pesos`);
    assert.ok(!text.includes(archiveB64.slice(0, 64)), `${name} contém o pacote do derivado`);
    assert.ok(!text.includes('"archive"'), `${name} contém o campo archive`);
  }
}

describe("Retenção do derivado (T-803)", function () {
  this.timeout(60_000);
  let tmp;

  beforeEach(function () {
    tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-retention-"));
  });

  afterEach(function () {
    fs.rmSync(tmp, { recursive: true, force: true });
  });

  it("job com derivado: result.json, stdout, stderr e metadata ficam sem pesos; a CVM1 recebe o pacote conferido", async function () {
    const derivative = await agentCollect(tmp);
    const { code, metadata, executionDir, archivePath, stderr } = await runJob(tmp, {
      returncode: 0,
      stdout: "loss=0.12 passos=10\n",
      stderr: "",
      derivative,
    });
    assert.strictEqual(code, 0, stderr);
    assert.deepStrictEqual(metadata.derivative, { digest: derivative.digest, status: "received" });
    assertNoWeights(executionDir, derivative);
    const result = JSON.parse(fs.readFileSync(path.join(executionDir, "result.json"), "utf8"));
    assert.deepStrictEqual(Object.keys(result).sort(), ["returncode", "stderr", "stdout"]);
    assert.ok(fs.readFileSync(archivePath).equals(Buffer.from(derivative.archive, "base64")));
  });

  it("a CVM1 cifra o pacote, guarda no IPFS, apaga o claro e registra o derivado retido e pendente", async function () {
    const derivative = await agentCollect(tmp);
    const { archivePath, metadata } = await runJob(tmp, { returncode: 0, stdout: "", stderr: "", derivative });
    const uploaded = [];
    const statePath = path.join(tmp, "derivatives.json");

    const record = await retainDerivative({
      archivePath,
      digest: metadata.derivative.digest,
      executionId: metadata.executionId,
      statePath,
      upload: async (buf) => {
        uploaded.push(buf);
        return "bafyfalso";
      },
      context: { datasetId: "1", applicationId: "2" },
    });

    assert.ok(!fs.existsSync(archivePath), "o pacote em claro sai do disco da CVM1");
    assert.strictEqual(uploaded.length, 1);
    assert.ok(!uploaded[0].includes(Buffer.from(MARKER)), "o IPFS só recebe o envelope cifrado");
    const { plaintext, metadata: envMeta } = decryptBufferEnvelope(uploaded[0], [DERIVATIVE_FORMAT]);
    assert.ok(plaintext.equals(Buffer.from(derivative.archive, "base64")));
    assert.strictEqual(envMeta.digest, derivative.digest);

    assert.strictEqual(record.encryptedUri, "ipfs://bafyfalso");
    assert.deepStrictEqual(userSummary(record), { digest: derivative.digest, status: "retained", verdict: "pending" });
    const saved = readLedger(statePath).derivatives[metadata.executionId];
    assert.strictEqual(saved.digest, derivative.digest);
    assert.strictEqual(saved.status, "retained");
    assert.strictEqual(saved.verdict, "pending");
    assert.strictEqual(saved.datasetId, "1");
  });

  it("falha no upload ainda apaga o pacote em claro", async function () {
    const archivePath = path.join(tmp, "derivative.tar.gz");
    fs.writeFileSync(archivePath, "pacote");
    await assert.rejects(
      retainDerivative({
        archivePath,
        digest: "a".repeat(64),
        executionId: "x",
        statePath: path.join(tmp, "derivatives.json"),
        upload: async () => {
          throw new Error("IPFS fora do ar");
        },
      }),
      /IPFS fora do ar/,
    );
    assert.ok(!fs.existsSync(archivePath));
    assert.ok(!fs.existsSync(path.join(tmp, "derivatives.json")));
  });

  it("digest adulterado: o derivado é recusado e nada é gravado", async function () {
    const derivative = await agentCollect(tmp);
    const forged = { ...derivative, digest: "0".repeat(64) };
    const { metadata, archivePath, executionDir } = await runJob(tmp, { returncode: 0, stdout: "", stderr: "", derivative: forged });
    assert.strictEqual(metadata.derivative.status, "invalid");
    assert.match(metadata.derivative.error, /digest mismatch/);
    assert.ok(!fs.existsSync(archivePath));
    assertNoWeights(executionDir, derivative);
  });

  it("arquivo a mais no pacote, fora da lista declarada: recusado", async function () {
    const derivative = await agentCollect(tmp);
    const forged = { ...derivative, files: derivative.files.slice(1) };
    const { metadata, archivePath } = await runJob(tmp, { returncode: 0, stdout: "", stderr: "", derivative: forged });
    assert.strictEqual(metadata.derivative.status, "invalid");
    assert.ok(!fs.existsSync(archivePath));
  });

  it("job que falhou ou sem destino de retenção: o derivado é descartado, sem sair na saída", async function () {
    const derivative = await agentCollect(tmp);
    const failed = await runJob(tmp, { returncode: 1, stdout: "", stderr: "erro", derivative });
    assert.deepStrictEqual(failed.metadata.derivative, { digest: derivative.digest, status: "discarded", reason: "job failed" });
    assert.ok(!fs.existsSync(failed.archivePath));
    assertNoWeights(failed.executionDir, derivative);

    const noTarget = await runJob(tmp, { returncode: 0, stdout: "", stderr: "", derivative }, { derivativeOut: false });
    assert.strictEqual(noTarget.metadata.derivative.status, "discarded");
    assertNoWeights(noTarget.executionDir, derivative);
  });

  it("job sem derivado segue como antes", async function () {
    const { code, metadata, executionDir } = await runJob(tmp, { returncode: 0, stdout: "ok\n", stderr: "", derivative: null });
    assert.strictEqual(code, 0);
    assert.strictEqual(metadata.derivative, undefined);
    assert.strictEqual(fs.readFileSync(path.join(executionDir, "stdout.txt"), "utf8"), "ok\n");
  });
});
