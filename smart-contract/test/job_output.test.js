/* T-804 e T-802, lado da CVM1: run_from_cids.py recusa o que não for o esquema fixo e espera o
 * agente sempre por mais tempo que ele, sem travar.
 *
 * Sem CVM real: o executor é um servidor HTTP falso; o run_from_cids.py é o de verdade. O lado do
 * agente (executor.py, run-direct.sh) é testado em vm_runtime/tests/test_job_output.py.
 */
const assert = require("node:assert");
const crypto = require("node:crypto");
const fs = require("node:fs");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");

const RUNNER = path.join(__dirname, "..", "scripts", "run_from_cids.py");
const PYTHON = process.env.PYTHON || "python3";

function agentOutput(fields = {}) {
  return {
    schema: "dnat.job-output.v1",
    status: "ok",
    returncode: 0,
    elapsed_seconds: 1.5,
    job_timeout_seconds: 600,
    metrics: { loss: 0.25, steps: 10 },
    metrics_error: null,
    error: null,
    derivative: null,
    ...fields,
  };
}

function run(cmd, args, env = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1", ...env } });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (c) => (stdout += c));
    child.stderr.on("data", (c) => (stderr += c));
    child.on("error", reject);
    child.on("close", (code) => resolve({ code, stdout, stderr }));
  });
}

/** Executor falso. `execute(req, res)` responde ao POST; `health` é o corpo de GET /health. */
function fakeExecutor({ execute, health = { ok: true } }) {
  const seen = [];
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      seen.push({ method: req.method, url: req.url, headers: req.headers });
      req.resume();
      req.on("end", () => {
        if (req.method === "GET") {
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify(health));
          return;
        }
        execute(req, res);
      });
    });
    server.listen(0, "127.0.0.1", () => resolve({ server, seen }));
  });
}

function reply(body, status = 200) {
  return (_req, res) => {
    res.writeHead(status, { "Content-Type": "application/json" });
    res.end(typeof body === "string" ? body : JSON.stringify(body));
  };
}

async function runJob(tmp, executorOpts, { args = [], env = {} } = {}) {
  const { server, seen } = await fakeExecutor(executorOpts);
  try {
    const datasetPath = path.join(tmp, "dataset.csv");
    const artifactPath = path.join(tmp, "application.ext4");
    fs.writeFileSync(datasetPath, "a,b\n1,2\n");
    fs.writeFileSync(artifactPath, "ext4-falso");
    const archivePath = path.join(tmp, "prep", "derivative.tar.gz");
    const started = Date.now();
    const { code, stdout, stderr } = await run(
      PYTHON,
      [
        RUNNER,
        "--local-dataset-path", datasetPath,
        "--application-artifact-path", artifactPath,
        "--executor-url", `http://127.0.0.1:${server.address().port}`,
        "--executions-dir", path.join(tmp, "executions"),
        "--derivative-out", archivePath,
        ...args,
      ],
      env,
    );
    const tookMs = Date.now() - started;
    const metadata = JSON.parse(stdout);
    const executionDir = path.join(tmp, "executions", metadata.executionId);
    const result = JSON.parse(fs.readFileSync(path.join(executionDir, "result.json"), "utf8"));
    return { code, stderr, metadata, result, executionDir, archivePath, seen, tookMs };
  } finally {
    server.closeAllConnections?.();
    server.close();
  }
}

/** Nenhum arquivo da execução (fora o bundle e as entradas) contém `needle`. */
function assertNothingLeaked(executionDir, needle) {
  for (const name of fs.readdirSync(executionDir)) {
    const p = path.join(executionDir, name);
    if (!fs.statSync(p).isFile() || name === "bundle.tar.gz" || name.endsWith(".ext4") || name.endsWith(".csv")) continue;
    assert.ok(!fs.readFileSync(p, "latin1").includes(needle), `${name} vazou a saída do job`);
  }
  assert.ok(!fs.existsSync(path.join(executionDir, "stdout.txt")));
  assert.ok(!fs.existsSync(path.join(executionDir, "stderr.txt")));
}

const FIXED_KEYS = ["elapsed_seconds", "error", "job_timeout_seconds", "metrics", "metrics_error", "returncode", "schema", "status"];

describe("Saída de esquema fixo na CVM1 (T-804)", function () {
  this.timeout(120_000);
  let tmp;

  beforeEach(function () {
    tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-job-output-"));
  });

  afterEach(function () {
    fs.rmSync(tmp, { recursive: true, force: true });
  });

  it("resposta conforme: result.json só com as chaves fixas e as métricas; sem stdout.txt nem stderr.txt", async function () {
    const { code, metadata, result, executionDir } = await runJob(tmp, { execute: reply(agentOutput()) });
    assert.strictEqual(code, 0);
    assert.strictEqual(metadata.status, "success");
    assert.strictEqual(metadata.outcome, "completed");
    assert.deepStrictEqual(Object.keys(result).sort(), FIXED_KEYS);
    assert.deepStrictEqual(result.metrics, { loss: 0.25, steps: 10 });
    assert.ok(!("stdoutPath" in metadata) && !("stderrPath" in metadata));
    assertNothingLeaked(executionDir, "PESOS");
  });

  it("agente antigo que devolve 50 MiB aleatórios no stdout: recusado, nada gravado, derivado descartado", async function () {
    const blob = crypto.randomBytes(50 << 20).toString("base64");
    const { code, metadata, result, executionDir, archivePath } = await runJob(tmp, {
      execute: reply({ returncode: 0, stdout: blob, stderr: "", derivative: { digest: "a".repeat(64), files: [], archive: "" } }),
    });
    assert.notStrictEqual(code, 0);
    assert.strictEqual(metadata.status, "output_rejected");
    assert.strictEqual(metadata.outcome, "inconclusive_failure");
    assert.strictEqual(metadata.error, "agent output rejected: too_large");
    assert.deepStrictEqual(metadata.derivative, { digest: "a".repeat(64), status: "discarded", reason: "output rejected" });
    assert.ok(!fs.existsSync(archivePath));
    assert.deepStrictEqual(Object.keys(result).sort(), FIXED_KEYS);
    assert.strictEqual(result.metrics, null);
    assertNothingLeaked(executionDir, blob.slice(1000, 1064));
  });

  it("campo extra na resposta ou nas métricas: recusado", async function () {
    const extraTop = await runJob(tmp, { execute: reply(agentOutput({ weights: "PESOS" })) });
    assert.strictEqual(extraTop.metadata.status, "output_rejected");
    assert.strictEqual(extraTop.metadata.error, "agent output rejected: unexpected_field");
    assertNothingLeaked(extraTop.executionDir, "PESOS");

    const extraMetric = await runJob(tmp, { execute: reply(agentOutput({ metrics: { loss: 1, pesos: 123456 } })) });
    assert.strictEqual(extraMetric.metadata.status, "output_rejected");
    assert.strictEqual(extraMetric.metadata.error, "agent output rejected: metrics_unknown_field");
    assertNothingLeaked(extraMetric.executionDir, "123456");
  });

  it("texto livre num campo de código, ou acima do teto configurado: recusado", async function () {
    const freeText = await runJob(tmp, { execute: reply(agentOutput({ status: "agent_error", returncode: null, error: "PESOS" })) });
    assert.strictEqual(freeText.metadata.error, "agent output rejected: error");
    assertNothingLeaked(freeText.executionDir, "PESOS");

    const capped = await runJob(tmp, { execute: reply(agentOutput()) }, { env: { DNAT_JOB_OUTPUT_MAX_BYTES: "64" } });
    assert.strictEqual(capped.metadata.error, "agent output rejected: too_large");
  });

  it("esquema de métricas configurável na CVM1", async function () {
    const env = { DNAT_METRICS_SCHEMA: '{"acc": "number"}' };
    const ok = await runJob(tmp, { execute: reply(agentOutput({ metrics: { acc: 0.91 } })) }, { env });
    assert.deepStrictEqual(ok.result.metrics, { acc: 0.91 });
    const refused = await runJob(tmp, { execute: reply(agentOutput()) }, { env });
    assert.strictEqual(refused.metadata.status, "output_rejected");
  });
});

describe("Tempos limite na CVM1 (T-802)", function () {
  this.timeout(120_000);
  let tmp;

  beforeEach(function () {
    tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-timeouts-"));
  });

  afterEach(function () {
    fs.rmSync(tmp, { recursive: true, force: true });
  });

  it("pede o limite ao agente, até o teto dele, e espera job + margem do agente + a própria folga", async function () {
    const health = { ok: true, timeouts: { job_default_seconds: 600, job_max_seconds: 7200, agent_margin_seconds: 120 } };
    const { metadata, seen } = await runJob(tmp, { execute: reply(agentOutput()), health }, { args: ["--job-timeout", "9000"] });
    const post = seen.find((r) => r.method === "POST");
    assert.strictEqual(post.headers["x-dnat-job-timeout"], "7200");
    assert.deepStrictEqual(metadata.timeouts, { jobSeconds: 7200, agentSeconds: 7320, cvm1Seconds: 7350 });
  });

  it("tempo estourado no agente: status timeout, erro registrado, inconclusivo por falha, derivado descartado", async function () {
    const { code, metadata, result, archivePath } = await runJob(tmp, {
      execute: reply(agentOutput({ status: "timeout", returncode: 124, job_timeout_seconds: 2, metrics: null, metrics_error: "missing", derivative: { digest: "b".repeat(64) } })),
    });
    assert.strictEqual(code, 124);
    assert.strictEqual(metadata.status, "timeout");
    assert.strictEqual(metadata.outcome, "inconclusive_failure");
    assert.match(metadata.error, /time limit \(2 s\)/);
    assert.strictEqual(metadata.derivative.status, "discarded");
    assert.ok(!fs.existsSync(archivePath));
    assert.strictEqual(result.status, "timeout");
  });

  it("agente que não responde: a CVM1 desiste no limite dela, registra e não trava", async function () {
    const health = { ok: true, timeouts: { job_default_seconds: 1, job_max_seconds: 1, agent_margin_seconds: 1 } };
    const { code, metadata, result, tookMs, seen } = await runJob(
      tmp,
      { execute: () => {}, health },
      { args: ["--job-timeout", "60", "--cvm1-margin", "1"] },
    );
    assert.strictEqual(seen.find((r) => r.method === "POST").headers["x-dnat-job-timeout"], "1");
    assert.deepStrictEqual(metadata.timeouts, { jobSeconds: 1, agentSeconds: 2, cvm1Seconds: 3 });
    assert.strictEqual(code, 124);
    assert.strictEqual(metadata.status, "timeout");
    assert.strictEqual(metadata.outcome, "inconclusive_failure");
    assert.match(metadata.error, /CVM1 waited 3 s/);
    assert.strictEqual(result.status, "timeout");
    assert.ok(tookMs < 15_000, `levou ${tookMs} ms`);
  });

  it("agente ocupado (503 no esquema fixo): falha registrada, sem travar", async function () {
    const { metadata } = await runJob(tmp, {
      execute: reply(agentOutput({ status: "agent_error", returncode: null, metrics: null, error: "busy" }), 503),
    });
    assert.strictEqual(metadata.status, "agent_error");
    assert.strictEqual(metadata.error, "agent error: busy");
    assert.strictEqual(metadata.outcome, "inconclusive_failure");
  });
});
