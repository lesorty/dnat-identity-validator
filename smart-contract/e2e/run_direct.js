#!/usr/bin/env node
/**
 * Fluxo inteiro numa máquina comum, no modo direto (T-811). Verificação de funcionamento: os tempos
 * e desfechos daqui NÃO são dado do artigo (todo dado do artigo sai da nuvem).
 *
 * Sobe, sem Docker e sem root:
 *   - cadeia: `hardhat node` e o DnatMarketplace implantado, com a CVM1 como operador;
 *   - IPFS: um servidor mínimo em memória com /api/v0/add e /api/v0/cat (só para este roteiro);
 *   - CVM2: build_vm_runtime/builder.py com DNAT_NO_MICROVM=1 (build-direct.sh, ext4 por mkfs -d);
 *   - CVM de job: vm_runtime/executor.py com DNAT_NO_MICROVM=1 (run-direct.sh, ext4 lido por debugfs);
 *   - CVM1: scripts/api-server.js, com estado num diretório temporário.
 *
 * E roda, pelo cliente assinado (identity_client.js), o caminho do derivado:
 *   identidade com prova de trabalho → depósito do base (tar.gz de um modelo minúsculo) → dataset →
 *   aplicação de fine-tuning simulado → compra de acesso → referência do pai depositada pelo
 *   operador → run-from-cids com parentModelId → derivado retido → Juiz como segundo job → recibo
 *   e cota.
 *
 * Cenários:
 *   A. Juiz real (model_gate): os estágios que dependem da nuvem ainda levantam StageNotReady, então
 *      o job termina em falha, nada vai ao contrato e a reserva da cota volta.
 *   B. Juiz SIMULADO aprovando (e2e/simulated_judge.js, numa lista permitida só de teste): recibo no
 *      contrato, derivado usável, cota 1.
 *   C. Juiz SIMULADO reprovando: recibo gravado, derivado inativo, cota 5.
 *
 *   node e2e/run_direct.js [--keep] [--serve] [--base-dir DIR]
 *       resultados em results/e2e_direct.{json,md}; com --base-dir, results/e2e_direct_<nome>.{json,md}
 *   --base-dir: um modelo real como base (T-805), por exemplo o Qwen2.5-0.5B de $MODEL_GATE_DATA;
 *   sem ele, o modelo minúsculo dos testes do model_gate.
 */
const crypto = require("node:crypto");
const fs = require("node:fs");
const http = require("node:http");
const net = require("node:net");
const os = require("node:os");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");
const { ethers } = require("ethers");
const client = require("../scripts/identity_client");
const { modelDirDigest, packModelDir } = require("../scripts/model_store");

const SC = path.resolve(__dirname, "..");
const REPO = path.resolve(SC, "..");
const MODEL_GATE = path.join(REPO, "model_gate");
const OPERATOR_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"; // conta 0 do hardhat
const KEEP = process.argv.includes("--keep");
// --serve: depois dos cenários, deixa a pilha no ar (para usar a web UI) até Ctrl+C.
const SERVE = process.argv.includes("--serve");
const BASE_DIR = (() => {
  const i = process.argv.indexOf("--base-dir");
  return i >= 0 ? path.resolve(process.argv[i + 1]) : null;
})();
const LABEL = BASE_DIR ? `_${path.basename(path.dirname(BASE_DIR)).replace(/[^A-Za-z0-9.-]+/g, "_")}` : "";
const sha = (b) => crypto.createHash("sha256").update(b).digest("hex");

const state = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-e2e-"));
const logs = path.join(state, "logs");
fs.mkdirSync(logs);
const procs = [];
const timings = [];
const servers = [];

function log(msg) {
  console.log(`[e2e] ${msg}`);
}

async function step(name, fn) {
  const t0 = process.hrtime.bigint();
  const out = await fn();
  const seconds = Number(process.hrtime.bigint() - t0) / 1e9;
  timings.push({ step: name, seconds: Math.round(seconds * 1000) / 1000 });
  log(`${name}: ${seconds.toFixed(2)} s`);
  return out;
}

function freePort() {
  return new Promise((resolve) => {
    const s = net.createServer().listen(0, "127.0.0.1", () => {
      const p = s.address().port;
      s.close(() => resolve(p));
    });
  });
}

function start(name, cmd, args, { env = {}, cwd = SC } = {}) {
  const out = fs.openSync(path.join(logs, `${name}.log`), "a");
  const p = spawn(cmd, args, { cwd, env: { ...process.env, ...env }, stdio: ["ignore", out, out], detached: true });
  procs.push({ name, p });
  return p;
}

function stop(p) {
  try {
    process.kill(-p.pid, "SIGTERM");
  } catch {
    // já saiu
  }
}

async function waitFor(name, check, timeoutMs = 120000) {
  const t0 = Date.now();
  for (;;) {
    try {
      if (await check()) return;
    } catch {
      // ainda subindo
    }
    if (Date.now() - t0 > timeoutMs) {
      const tail = fs.existsSync(path.join(logs, `${name}.log`)) ? fs.readFileSync(path.join(logs, `${name}.log`), "utf8").slice(-1500) : "";
      throw new Error(`${name} não subiu em ${timeoutMs / 1000} s\n${tail}`);
    }
    await new Promise((r) => setTimeout(r, 300));
  }
}

const httpOk = (url) => async () => (await fetch(url, { signal: AbortSignal.timeout(2000) })).ok;

// ------------------------------------------------------------------ IPFS mínimo, em memória

function startFakeIpfs(port) {
  // Blocos em disco (T-805: envelopes de GB); o add ainda monta o multipart na memória, o cat é em fluxo.
  const blobs = path.join(state, "ipfs");
  fs.mkdirSync(blobs, { recursive: true });
  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, "http://x");
    if (url.pathname === "/api/v0/add") {
      const chunks = [];
      for await (const c of req) chunks.push(c);
      const form = await new Request("http://x", { method: "POST", headers: req.headers, body: Buffer.concat(chunks) }).formData();
      const file = form.get("file");
      const data = Buffer.from(await file.arrayBuffer());
      const cid = `bafk${sha(data).slice(0, 52)}`;
      fs.writeFileSync(path.join(blobs, cid), data);
      res.setHeader("Content-Type", "application/json");
      return res.end(JSON.stringify({ Name: file.name, Hash: cid, Size: String(data.length) }));
    }
    req.resume();
    if (url.pathname === "/api/v0/cat") {
      const cid = String(url.searchParams.get("arg") || "");
      const file = path.join(blobs, cid);
      if (!/^bafk[0-9a-f]{52}$/.test(cid) || !fs.existsSync(file)) {
        res.statusCode = 404;
        return res.end("not found");
      }
      res.setHeader("Content-Length", fs.statSync(file).size);
      return fs.createReadStream(file).pipe(res);
    }
    res.statusCode = 404;
    res.end();
  });
  servers.push(server);
  return new Promise((resolve) => server.listen(port, "127.0.0.1", () => resolve(blobs)));
}

// ------------------------------------------------------------------ peças

async function startChain() {
  const port = await freePort();
  const rpc = `http://127.0.0.1:${port}`;
  start("hardhat", "npx", ["hardhat", "node", "--hostname", "127.0.0.1", "--port", String(port)]);
  await waitFor("hardhat", async () => {
    const r = await fetch(rpc, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_chainId", params: [] }) });
    return r.ok;
  });
  const provider = new ethers.JsonRpcProvider(rpc);
  const operator = new ethers.Wallet(OPERATOR_KEY, provider);
  const art = JSON.parse(fs.readFileSync(path.join(SC, "artifacts", "contracts", "DnatMarketplace.sol", "DnatMarketplace.json"), "utf8"));
  const contract = await new ethers.ContractFactory(art.abi, art.bytecode, operator).deploy(operator.address);
  await contract.waitForDeployment();
  return { rpc, provider, contract, address: await contract.getAddress() };
}

function makeTinyBase(dir) {
  const code = "import sys; from pathlib import Path; from tests.tiny import save_tiny; save_tiny(Path(sys.argv[1]), seed=0)";
  const r = spawnSync("uv", ["run", "--project", MODEL_GATE, "--frozen", "--quiet", "python", "-c", code, dir], { cwd: MODEL_GATE, encoding: "utf8" });
  if (r.status !== 0) throw new Error(`modelo minúsculo: ${r.stderr}`);
  return dir;
}

// Assíncrono: o IPFS em memória roda neste processo e precisa atender o judge_cli.
function judgeCli(args, env) {
  return new Promise((resolve, reject) => {
    const p = spawn(process.execPath, [path.join(SC, "scripts", "judge_cli.js"), ...args], { cwd: SC, env: { ...process.env, ...env } });
    let out = "";
    let err = "";
    p.stdout.on("data", (c) => (out += c));
    p.stderr.on("data", (c) => (err += c));
    p.on("close", (code) => (code === 0 ? resolve(JSON.parse(out)) : reject(new Error(`judge_cli ${args[0]}: ${err}`))));
  });
}

async function startCvm1(name, env) {
  const port = await freePort();
  const p = start(name, process.execPath, [path.join(SC, "scripts", "api-server.js")], { env: { ...env, WEB_PORT: String(port) } });
  const api = `http://127.0.0.1:${port}`;
  await waitFor(name, httpOk(`${api}/api/identity/challenge`));
  return { api, p };
}

// ------------------------------------------------------------------ roteiro

async function main() {
  const machine = { ...client.machineInfo(), node: process.version, startedAtUtc: new Date().toISOString() };
  // Antes de qualquer conexão: o spawnSync trava este processo, e uma conexão ociosa do cliente
  // seria fechada pelo servidor (keep-alive de 5 s) e reaproveitada depois ("other side closed").
  const baseDir = BASE_DIR || makeTinyBase(path.join(state, "base"));
  const baseArchive = packModelDir(baseDir, path.join(state, "base.tar.gz"));
  const ipfsPort = await freePort();
  const ipfsUrl = `http://127.0.0.1:${ipfsPort}`;
  await step("IPFS em memória", () => startFakeIpfs(ipfsPort));
  const chain = await step("hardhat node e implantação do contrato", startChain);

  const builderPort = await freePort();
  const builderUrl = `http://127.0.0.1:${builderPort}`;
  await step("CVM2 (builder, modo direto)", async () => {
    start("builder", "python3", [path.join(REPO, "build_vm_runtime", "builder.py"), String(builderPort)], {
      cwd: path.join(REPO, "build_vm_runtime"),
      env: { DNAT_NO_MICROVM: "1", DNAT_ARTIFACT_BUILDER: path.join(SC, "scripts", "build_application_artifact.py"), WHEEL_CACHE_SOURCE_DIR: path.join(state, "wheels") },
    });
    await waitFor("builder", httpOk(`${builderUrl}/health`));
  });
  const executorPort = await freePort();
  const executorUrl = `http://127.0.0.1:${executorPort}`;
  await step("CVM de job (executor, modo direto)", async () => {
    start("executor", "python3", [path.join(REPO, "vm_runtime", "executor.py"), String(executorPort)], {
      cwd: path.join(REPO, "vm_runtime"), env: { DNAT_NO_MICROVM: "1" },
    });
    await waitFor("executor", httpOk(`${executorUrl}/health`));
  });

  const allowlist = path.join(state, "judge_allowlist.json");
  const batteryPackPath = path.join(state, "battery_pack.json");
  const battery = sha("T-304 pendente: compromisso provisório da parte secreta");
  // Pacote da bateria (T-807), se já montado no notebook (experiments.battery_pack); fica fora do git.
  const localPack = path.join(process.env.MODEL_GATE_DATA || path.join(os.homedir(), "model_gate_data"), "battery", "local_t807");
  const hasPack = fs.existsSync(path.join(localPack, "battery.json"));
  if (hasPack) {
    await step("pacote da bateria depositado pelo operador (judge_cli battery)", () =>
      judgeCli(["battery", "--dir", localPack, "--source", "roteiro T-811"], { IPFS_API_URL: ipfsUrl, DNAT_BATTERY_PACK_PATH: batteryPackPath }));
  }
  const release = await step("liberar o Juiz atual na lista permitida (judge_cli allow)", () =>
    judgeCli(["allow", "--battery-commitment", battery, "--evaluator-kind", "detector", "--note", "roteiro T-811"],
      { DNAT_JUDGE_ALLOWLIST: allowlist, DNAT_BATTERY_PACK_PATH: batteryPackPath }));

  const cvmEnv = {
    RPC_URL: chain.rpc,
    CONTRACT_ADDRESS: chain.address,
    PRIVATE_KEY: OPERATOR_KEY,
    IPFS_API_URL: ipfsUrl,
    EXECUTOR_URL: executorUrl,
    BUILDER_URL: builderUrl,
    DNAT_IDENTITIES_PATH: path.join(state, "identities.json"),
    DNAT_DERIVATIVES_PATH: path.join(state, "derivatives.json"),
    DNAT_REFERENCES_PATH: path.join(state, "references.json"),
    DNAT_JUDGE_ALLOWLIST: allowlist,
    DNAT_BATTERY_PACK_PATH: batteryPackPath,
    DNAT_SAMPLING_KEY_PATH: path.join(state, "sampling_key"),
    DNAT_IDENTITY_DIFFICULTY: "12",
    DNAT_UPLOAD_LIMIT: "4gb",
  };
  let cvm1 = await step("CVM1 (api-server)", () => startCvm1("cvm1", cvmEnv));

  const identity = client.generateIdentity();
  const reg = await step("identidade com prova de trabalho (d = 12)", () => client.registerIdentity({ apiUrl: cvm1.api, identity }));
  const signed = (p, opts) => client.signedRequest({ apiUrl: cvm1.api, identity, path: p, ...opts });
  const multipart = (name, filename, data) => client.buildMultipart({ "manifest.name": name, "manifest.description": "roteiro T-811" }, { file: { filename, data } });

  const model = await step("depósito do modelo base (register-model)", () => {
    const m = multipart(BASE_DIR ? path.basename(path.dirname(BASE_DIR)) : "modelo minúsculo", "base.tar.gz", fs.readFileSync(baseArchive));
    return signed("/api/register-model", { body: m.body, contentType: m.contentType });
  });
  if (model.onChainAsset.contentHash !== `0x${modelDirDigest(baseDir).digest}`) throw new Error("contentHash do base não é o digest do diretório");

  const csv = "prompt,response\nWhat is the capital of France?,Paris\nName a primary color.,Blue\nHow many legs does a spider have?,Eight\n";
  const dataset = await step("dataset (register-dataset)", () => {
    const m = multipart("dataset benigno", "dataset.csv", Buffer.from(csv));
    return signed("/api/register-dataset", { body: m.body, contentType: m.contentType });
  });
  const app = await step("aplicação de fine-tuning simulado (register-application, build no CVM2)", () => {
    const m = multipart("fine-tuning simulado", "application.py", fs.readFileSync(path.join(__dirname, "fine_tune_app.py")));
    return signed("/api/register-application", { body: m.body, contentType: m.contentType });
  });
  await step("compra de acesso (purchase-access)", async () => {
    const r = await fetch(`${cvm1.api}/api/purchase-access`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ datasetId: dataset.assetId, applicationId: app.assetId }) });
    if (!r.ok) throw new Error(await r.text());
  });

  const refDir = path.join(state, "reference");
  fs.mkdirSync(refDir);
  fs.writeFileSync(path.join(refDir, "reference.json"), JSON.stringify({ placeholder: "T-312 roda na nuvem; esta referência é só do roteiro" }));
  await step("referência do pai depositada pelo operador (judge_cli reference)", () =>
    judgeCli(["reference", "--parent", model.assetId, "--dir", refDir, "--source", "roteiro T-811 (placeholder)"],
      { IPFS_API_URL: ipfsUrl, DNAT_REFERENCES_PATH: cvmEnv.DNAT_REFERENCES_PATH }));

  const job = { datasetId: dataset.assetId, applicationId: app.assetId, parentModelId: model.assetId };
  const balance = async () => (await (await fetch(`${cvm1.api}/api/identity/${reg.record.id}`)).json()).balance;
  const scenarios = {};

  scenarios.A = await step("A · fine-tuning + Juiz real (model_gate)", () => signed("/api/run-from-cids", { json: job }));
  scenarios.A.balanceAfter = await balance();

  // B e C: a CVM1 reinicia com o Juiz SIMULADO, numa lista permitida só de teste.
  stop(cvm1.p);
  const simHash = sha("juiz simulado do roteiro T-811");
  const simAllow = path.join(state, "judge_allowlist_simulado.json");
  fs.writeFileSync(simAllow, JSON.stringify({ schema: "dnat.judge-allowlist.v1", judges: [{ ...release, judgeHash: simHash, note: "SIMULADO" }] }));
  const simEnv = { ...cvmEnv, DNAT_JUDGE_ALLOWLIST: simAllow, DNAT_JUDGE_CMD: JSON.stringify([process.execPath, path.join(__dirname, "simulated_judge.js")]), SIMULATED_JUDGE_HASH: simHash };
  cvm1 = await startCvm1("cvm1-simulado", { ...simEnv, SIMULATED_JUDGE_STATE: "aprovado" });
  scenarios.B = await step("B · fine-tuning + Juiz SIMULADO aprovando", () => signed("/api/run-from-cids", { json: job }));
  scenarios.B.balanceAfter = await balance();
  stop(cvm1.p);
  cvm1 = await startCvm1("cvm1-simulado-reprova", { ...simEnv, SIMULATED_JUDGE_STATE: "reprovado" });
  scenarios.C = await step("C · fine-tuning + Juiz SIMULADO reprovando", () => signed("/api/run-from-cids", { json: job }));
  scenarios.C.balanceAfter = await balance();

  const onChain = {};
  for (const k of ["B", "C"]) {
    const id = scenarios[k].judge?.assetId;
    if (!id) continue;
    const a = await chain.contract.getAsset(BigInt(id));
    const d = await chain.contract.getDerivative(BigInt(id));
    onChain[k] = { assetId: id, active: a.active, usable: await chain.contract.isDerivativeUsable(BigInt(id)), verdict: Number(d.verdict), verdictHash: d.verdictHash, judgeHash: d.judgeHash };
  }

  const summary = (s) => ({
    exitCode: s.exitCode,
    metrics: s.result?.metrics ?? null,
    derivative: s.metadata?.derivative ?? null,
    judge: s.judge,
    quota: s.quota,
    balanceAfter: s.balanceAfter,
  });
  const result = {
    note: "Verificação de funcionamento (T-811), não é dado do artigo. B e C usam um Juiz SIMULADO.",
    machine,
    judgeRelease: release,
    base: { dir: BASE_DIR ? path.basename(path.dirname(BASE_DIR)) : "minúsculo (tests/tiny.py)", digest: modelDirDigest(baseDir).digest,
      archiveBytes: fs.statSync(baseArchive).size },
    assets: { model: model.assetId, dataset: dataset.assetId, application: app.assetId },
    identity: { id: reg.record.id, difficulty: reg.difficulty, proofSeconds: reg.proofSeconds },
    scenarios: { A: summary(scenarios.A), B: summary(scenarios.B), C: summary(scenarios.C) },
    onChain,
    timings,
  };

  const checks = [
    ["A: Juiz real termina em falha (prereg sem valores, T-606)", scenarios.A.judge?.outcome === "failure"],
    ["A: reserva devolvida (saldo 20)", scenarios.A.balanceAfter === 20],
    ["B: aprovado, derivado usável no contrato", scenarios.B.judge?.outcome === "approved" && onChain.B?.usable === true],
    ["B: cota 1 (saldo 19)", scenarios.B.balanceAfter === 19],
    ["C: reprovado, derivado inativo", scenarios.C.judge?.outcome === "rejected" && onChain.C?.active === false],
    ["C: cota 5 (saldo 14)", scenarios.C.balanceAfter === 14],
  ];
  result.checks = checks.map(([name, ok]) => ({ name, ok }));
  writeResults(result);
  for (const [name, ok] of checks) log(`${ok ? "ok  " : "FALHOU"} ${name}`);
  if (SERVE) {
    log(`pilha no ar: web UI em ${cvm1.api}/ (Juiz SIMULADO reprovando, modelo base ${model.assetId}); Ctrl+C encerra`);
    await new Promise((resolve) => {
      process.once("SIGINT", resolve);
      process.once("SIGTERM", resolve);
    });
  }
  return checks.every(([, ok]) => ok) ? 0 : 1;
}

function writeResults(r) {
  const dir = path.join(SC, "results");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, `e2e_direct${LABEL}.json`), JSON.stringify(r, null, 2) + "\n");
  const rows = r.timings.map((t) => `| ${t.step} | ${t.seconds.toFixed(2)} |`).join("\n");
  const sc = (k) => {
    const s = r.scenarios[k];
    return `| ${k} | ${s.exitCode} | ${s.derivative?.status ?? "-"} | ${s.judge?.outcome ?? "-"} | ${s.judge?.alert ?? "-"} | ${s.judge?.assetId ?? "-"} | ${s.balanceAfter} |`;
  };
  const md = `# Fluxo inteiro no modo direto (T-811)

${r.note}

Base: ${r.base.dir} · ${(r.base.archiveBytes / 1e6).toFixed(1)} MB empacotado · digest \`${r.base.digest.slice(0, 12)}\`

Máquina: ${r.machine.cpuModel} · ${r.machine.logicalCpus} CPUs lógicas · ${r.machine.platform} · Node ${r.machine.node} · ${r.machine.startedAtUtc}

Juiz liberado: \`${r.judgeRelease.judgeHash}\` · prereg \`${r.judgeRelease.preregSha256}\`

## Desfechos

| Cenário | Saída do job | Derivado | Veredito | Alerta | Asset | Saldo depois |
|---|---|---|---|---|---|---|
${sc("A")}
${sc("B")}
${sc("C")}

A: Juiz real. B e C: Juiz SIMULADO (e2e/simulated_judge.js), só para exercitar recibo e cota.

## Conferências

${r.checks.map((c) => `- ${c.ok ? "✅" : "❌"} ${c.name}`).join("\n")}

## Tempo por etapa (s)

| Etapa | s |
|---|---|
${rows}
`;
  fs.writeFileSync(path.join(dir, `e2e_direct${LABEL}.md`), md);
}

main()
  .then((code) => {
    process.exitCode = code;
  })
  .catch((e) => {
    console.error(`[e2e] erro: ${e.stack || e.message}${e.cause ? ` (causa: ${e.cause.message || e.cause})` : ""}`);
    console.error(`[e2e] logs em ${logs}`);
    process.exitCode = 1;
  })
  .finally(() => {
    for (const { p } of procs) stop(p);
    for (const s of servers) s.close();
    if (!KEEP && process.exitCode === 0) fs.rmSync(state, { recursive: true, force: true });
    else console.log(`[e2e] estado mantido em ${state}`);
    setTimeout(() => process.exit(process.exitCode ?? 0), 500).unref();
  });
