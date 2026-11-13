/**
 * Pilha do modo direto para os roteiros de ponta a ponta (T-811, T-814), sem Docker nem root.
 *
 *   cadeia     `hardhat node` e o DnatMarketplace implantado, com a CVM1 como operador
 *   IPFS       servidor mínimo com /api/v0/add e /api/v0/cat, blocos em disco (só para os roteiros)
 *   CVM2       build_vm_runtime/builder.py com DNAT_NO_MICROVM=1 (ext4 por mkfs -d)
 *   CVM de job vm_runtime/executor.py com DNAT_NO_MICROVM=1 (ext4 lido por debugfs)
 *   CVM1       scripts/api-server.js, com estado num diretório temporário
 *
 * Os processos sobem num grupo próprio e são encerrados em close(). Estado e logs ficam em
 * stack.state; close() apaga o estado só quando o roteiro passou e não pediu --keep.
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

const SC = path.resolve(__dirname, "..");
const REPO = path.resolve(SC, "..");
const MODEL_GATE = path.join(REPO, "model_gate");
const MODEL_GATE_DATA = process.env.MODEL_GATE_DATA || path.join(os.homedir(), "model_gate_data");
const OPERATOR_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"; // conta 0 do hardhat
const sha = (b) => crypto.createHash("sha256").update(b).digest("hex");

function freePort() {
  return new Promise((resolve) => {
    const s = net.createServer().listen(0, "127.0.0.1", () => {
      const p = s.address().port;
      s.close(() => resolve(p));
    });
  });
}

const httpOk = (url) => async () => (await fetch(url, { signal: AbortSignal.timeout(2000) })).ok;

class Stack {
  constructor(tag = "e2e") {
    this.tag = tag;
    this.state = fs.mkdtempSync(path.join(os.tmpdir(), `dnat-${tag}-`));
    this.logs = path.join(this.state, "logs");
    fs.mkdirSync(this.logs);
    this.procs = [];
    this.servers = [];
    this.timings = [];
    this.machine = { ...client.machineInfo(), node: process.version, startedAtUtc: new Date().toISOString() };
  }

  log(msg) {
    console.log(`[${this.tag}] ${msg}`);
  }

  async step(name, fn) {
    const t0 = process.hrtime.bigint();
    const out = await fn();
    const seconds = Number(process.hrtime.bigint() - t0) / 1e9;
    this.timings.push({ step: name, seconds: Math.round(seconds * 1000) / 1000 });
    this.log(`${name}: ${seconds.toFixed(2)} s`);
    return out;
  }

  start(name, cmd, args, { env = {}, cwd = SC } = {}) {
    const out = fs.openSync(path.join(this.logs, `${name}.log`), "a");
    const p = spawn(cmd, args, { cwd, env: { ...process.env, ...env }, stdio: ["ignore", out, out], detached: true });
    this.procs.push({ name, p });
    return p;
  }

  stop(p) {
    try {
      process.kill(-p.pid, "SIGTERM");
    } catch {
      // já saiu
    }
  }

  async waitFor(name, check, timeoutMs = 120000) {
    const t0 = Date.now();
    for (;;) {
      try {
        if (await check()) return;
      } catch {
        // ainda subindo
      }
      if (Date.now() - t0 > timeoutMs) {
        const f = path.join(this.logs, `${name}.log`);
        throw new Error(`${name} não subiu em ${timeoutMs / 1000} s\n${fs.existsSync(f) ? fs.readFileSync(f, "utf8").slice(-1500) : ""}`);
      }
      await new Promise((r) => setTimeout(r, 300));
    }
  }

  // ---------------------------------------------------------------- peças

  async startIpfs() {
    // Blocos em disco (T-805: envelopes de GB); o add monta o multipart na memória, o cat é em fluxo.
    const blobs = path.join(this.state, "ipfs");
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
    this.servers.push(server);
    const port = await freePort();
    await new Promise((resolve) => server.listen(port, "127.0.0.1", resolve));
    this.ipfsUrl = `http://127.0.0.1:${port}`;
    return this.ipfsUrl;
  }

  async startChain() {
    const port = await freePort();
    const rpc = `http://127.0.0.1:${port}`;
    this.start("hardhat", "npx", ["hardhat", "node", "--hostname", "127.0.0.1", "--port", String(port)]);
    await this.waitFor("hardhat", async () => {
      const r = await fetch(rpc, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_chainId", params: [] }) });
      return r.ok;
    });
    const provider = new ethers.JsonRpcProvider(rpc);
    const operator = new ethers.Wallet(OPERATOR_KEY, provider);
    const art = JSON.parse(fs.readFileSync(path.join(SC, "artifacts", "contracts", "DnatMarketplace.sol", "DnatMarketplace.json"), "utf8"));
    const contract = await new ethers.ContractFactory(art.abi, art.bytecode, operator).deploy(operator.address);
    await contract.waitForDeployment();
    this.chain = { rpc, provider, contract, address: await contract.getAddress(), abi: art.abi };
    return this.chain;
  }

  async startBuilder() {
    const port = await freePort();
    this.builderUrl = `http://127.0.0.1:${port}`;
    this.start("builder", "python3", [path.join(REPO, "build_vm_runtime", "builder.py"), String(port)], {
      cwd: path.join(REPO, "build_vm_runtime"),
      env: { DNAT_NO_MICROVM: "1", DNAT_ARTIFACT_BUILDER: path.join(SC, "scripts", "build_application_artifact.py"),
        WHEEL_CACHE_SOURCE_DIR: path.join(this.state, "wheels") },
    });
    await this.waitFor("builder", httpOk(`${this.builderUrl}/health`));
    return this.builderUrl;
  }

  async startExecutor(env = {}) {
    const port = await freePort();
    this.executorUrl = `http://127.0.0.1:${port}`;
    this.start("executor", "python3", [path.join(REPO, "vm_runtime", "executor.py"), String(port)], {
      cwd: path.join(REPO, "vm_runtime"), env: { DNAT_NO_MICROVM: "1", ...env },
    });
    await this.waitFor("executor", httpOk(`${this.executorUrl}/health`));
    return this.executorUrl;
  }

  /** Variáveis da CVM1 com o estado neste diretório; `extra` acrescenta ou troca. */
  cvmEnv(extra = {}) {
    return {
      RPC_URL: this.chain.rpc,
      CONTRACT_ADDRESS: this.chain.address,
      PRIVATE_KEY: OPERATOR_KEY,
      IPFS_API_URL: this.ipfsUrl,
      EXECUTOR_URL: this.executorUrl,
      BUILDER_URL: this.builderUrl,
      DNAT_IDENTITIES_PATH: path.join(this.state, "identities.json"),
      DNAT_DERIVATIVES_PATH: path.join(this.state, "derivatives.json"),
      DNAT_REFERENCES_PATH: path.join(this.state, "references.json"),
      DNAT_JUDGE_ALLOWLIST: path.join(this.state, "judge_allowlist.json"),
      DNAT_BATTERY_PACK_PATH: path.join(this.state, "battery_pack.json"),
      DNAT_SAMPLING_KEY_PATH: path.join(this.state, "sampling_key"),
      DNAT_IDENTITY_DIFFICULTY: "12",
      DNAT_UPLOAD_LIMIT: "4gb",
      ...extra,
    };
  }

  async startCvm1(name, env) {
    const port = await freePort();
    const p = this.start(name, process.execPath, [path.join(SC, "scripts", "api-server.js")], { env: { ...env, WEB_PORT: String(port) } });
    const api = `http://127.0.0.1:${port}`;
    await this.waitFor(name, httpOk(`${api}/api/identity/challenge`));
    return { api, p };
  }

  /** judge_cli.js assíncrono: o IPFS roda neste processo e precisa atender. */
  judgeCli(args, env = {}) {
    return new Promise((resolve, reject) => {
      const p = spawn(process.execPath, [path.join(SC, "scripts", "judge_cli.js"), ...args], {
        cwd: SC, env: { ...process.env, ...this.cvmEnv(), ...env },
      });
      let out = "";
      let err = "";
      p.stdout.on("data", (c) => (out += c));
      p.stderr.on("data", (c) => (err += c));
      p.on("close", (code) => (code === 0 ? resolve(JSON.parse(out)) : reject(new Error(`judge_cli ${args[0]}: ${err}`))));
    });
  }

  /** Modelo minúsculo dos testes do model_gate (síncrono: chamar antes de abrir conexões). */
  makeTinyBase(dir) {
    const code = "import sys; from pathlib import Path; from tests.tiny import save_tiny; save_tiny(Path(sys.argv[1]), seed=0)";
    const r = spawnSync("uv", ["run", "--project", MODEL_GATE, "--frozen", "--quiet", "python", "-c", code, dir], { cwd: MODEL_GATE, encoding: "utf8" });
    if (r.status !== 0) throw new Error(`modelo minúsculo: ${r.stderr}`);
    return dir;
  }

  close({ keep = false, ok = false } = {}) {
    for (const { p } of this.procs) this.stop(p);
    for (const s of this.servers) s.close();
    if (!keep && ok) fs.rmSync(this.state, { recursive: true, force: true });
    else this.log(`estado mantido em ${this.state}`);
  }
}

// O run-from-cids com o Juiz real responde depois de minutos; o fetch do Node desiste se os
// cabeçalhos não chegam em 300 s. Para os roteiros, sem limite de espera.
const { Agent, fetch: undiciFetch } = require("undici");
const patient = new Agent({ headersTimeout: 0, bodyTimeout: 0 });
const longFetch = (url, opts = {}) => undiciFetch(url, { ...opts, dispatcher: patient });

/** Cliente assinado de uma identidade nova, registrada com prova de trabalho. */
async function newClient(apiUrl) {
  let api = apiUrl;
  const identity = client.generateIdentity();
  const reg = await client.registerIdentity({ apiUrl: api, identity });
  return {
    identity,
    reg,
    /** A CVM1 reiniciada (outra porta) continua com o mesmo estado e a mesma identidade. */
    useApi: (next) => {
      api = next;
    },
    signed: (p, opts) => client.signedRequest({ apiUrl: api, identity, path: p, fetchImpl: longFetch, ...opts }),
    multipart: (name, filename, data, description = "") =>
      client.buildMultipart({ "manifest.name": name, "manifest.description": description }, { file: { filename, data } }),
    balance: async () => (await (await fetch(`${api}/api/identity/${reg.record.id}`)).json()).balance,
  };
}

/** Termina o roteiro: código de saída, encerramento da pilha e saída do processo. */
function finish(stack, promise, { keep = false } = {}) {
  promise
    .then((code) => {
      process.exitCode = code;
    })
    .catch((e) => {
      console.error(`[${stack.tag}] erro: ${e.stack || e.message}${e.cause ? ` (causa: ${e.cause.message || e.cause})` : ""}`);
      console.error(`[${stack.tag}] logs em ${stack.logs}`);
      process.exitCode = 1;
    })
    .finally(() => {
      stack.close({ keep, ok: process.exitCode === 0 });
      setTimeout(() => process.exit(process.exitCode ?? 0), 500).unref();
    });
}

module.exports = { MODEL_GATE, MODEL_GATE_DATA, OPERATOR_KEY, REPO, SC, Stack, finish, newClient, sha };
