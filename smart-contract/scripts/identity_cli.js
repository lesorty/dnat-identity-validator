/**
 * Subcomandos do cli.js que falam com a API da CVM1 como uma identidade (T-1705). Rodam sem
 * hardhat e sem carteira: só a chave Ed25519 do usuário.
 *
 *   identity new   [--api URL] [--key ARQUIVO] [--force]   gera a chave, minera a prova e registra
 *   identity show  [--api URL] [--key ARQUIVO]             saldo e contagens (GET /api/identity/:id)
 *   identity bench [--min 12] [--max 24] [--reps 5] [--out results/identity_pow_cost]
 *   run-from-cids  --dataset ID --application ID [--user ENDEREÇO] [--api URL] [--key ARQUIVO]
 *   api MÉTODO CAMINHO [--json TEXTO | --json-file ARQ] [--field nome=valor]... [--file nome=ARQ]...
 *                                                          pedido assinado genérico (scripts de teste)
 *
 * Padrões: --api = DNAT_API_URL ou http://127.0.0.1:3001; --key = DNAT_IDENTITY_KEY ou
 * ~/.dnat/identity.json. Saída em JSON no stdout; erros no stderr com código de saída 1.
 */
const fs = require("node:fs");
const path = require("node:path");
const client = require("./identity_client");

const COMMANDS = ["identity", "run-from-cids", "api"];

/** --nome valor (ou --nome sozinho como booleano); repetidos viram lista. O resto são posicionais. */
function parseArgs(argv, { multi = [], flags = [] } = {}) {
  const opts = {};
  const positional = [];
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (!a.startsWith("--")) {
      positional.push(a);
      continue;
    }
    const name = a.slice(2);
    if (flags.includes(name)) {
      opts[name] = true;
      continue;
    }
    const value = argv[i + 1];
    if (value === undefined || value.startsWith("--")) throw new client.ClientError(`--${name} needs a value`);
    i += 1;
    if (multi.includes(name)) (opts[name] ||= []).push(value);
    else opts[name] = value;
  }
  return { opts, positional };
}

const int = (value, name, fallback) => {
  if (value === undefined) return fallback;
  if (!/^\d+$/.test(String(value))) throw new client.ClientError(`--${name} must be a non-negative integer`);
  return Number(value);
};

async function identityNew(opts, out) {
  const keyFile = opts.key || client.DEFAULT_KEY_FILE;
  const identity = client.generateIdentity();
  // A chave só é gravada depois de a CVM1 aceitar o registro; antes, um 400 deixaria uma chave sem identidade.
  if (fs.existsSync(keyFile) && !opts.force) throw new client.ClientError(`key file already exists: ${keyFile} (use --force)`);
  const { record, difficulty, nonce, proofSeconds } = await client.registerIdentity({ apiUrl: opts.api, identity });
  client.saveKeyFile(keyFile, { ...identity, apiUrl: opts.api || client.DEFAULT_API_URL, registeredAtUtc: record.registeredAtUtc }, { overwrite: Boolean(opts.force) });
  out({ id: identity.id, keyFile, difficulty, nonce, proofSeconds, balance: record.balance });
}

async function identityShow(opts, out) {
  const key = client.loadKeyFile(opts.key || client.DEFAULT_KEY_FILE);
  const res = await fetch(`${String(opts.api || key.apiUrl || client.DEFAULT_API_URL).replace(/\/+$/, "")}/api/identity/${key.id}`);
  const body = await res.json();
  if (!res.ok) throw new client.ClientError(`${res.status} ${body.error}`, res.status, body);
  out(body);
}

function identityBench(opts, out, log) {
  const outBase = opts.out || path.join(__dirname, "..", "results", "identity_pow_cost");
  const result = client.benchProof({
    minBits: int(opts.min, "min", 12),
    maxBits: int(opts.max, "max", 24),
    reps: int(opts.reps, "reps", 5),
    onRow: (r) => log(`d=${r.difficulty}: média ${r.meanSeconds.toFixed(3)} s (esperado ${r.expectedSeconds.toFixed(3)} s)`),
  });
  const machine = client.machineInfo();
  fs.mkdirSync(path.dirname(outBase), { recursive: true });
  fs.writeFileSync(`${outBase}.json`, JSON.stringify({ measuredAtUtc: new Date().toISOString(), machine, ...result }, null, 2));
  fs.writeFileSync(`${outBase}.md`, client.benchMarkdown(result, machine));
  out({ json: `${outBase}.json`, markdown: `${outBase}.md`, hashesPerSecond: result.hashesPerSecond, rows: result.rows.length });
}

async function signedCall(opts, positional, out) {
  const key = client.loadKeyFile(opts.key || client.DEFAULT_KEY_FILE);
  const apiUrl = opts.api || key.apiUrl;
  const [method, requestPath] = positional;
  if (!method || !requestPath || !requestPath.startsWith("/")) throw new client.ClientError("usage: api METHOD /path [--json ...]");
  const request = { apiUrl, identity: key, method: method.toUpperCase(), path: requestPath };
  if (opts["json-file"]) request.json = JSON.parse(fs.readFileSync(opts["json-file"], "utf8"));
  else if (opts.json) request.json = JSON.parse(opts.json);
  else if (opts.field || opts.file) {
    const fields = Object.fromEntries((opts.field || []).map((f) => [f.slice(0, f.indexOf("=")), f.slice(f.indexOf("=") + 1)]));
    const files = Object.fromEntries(
      (opts.file || []).map((f) => {
        const name = f.slice(0, f.indexOf("="));
        const file = f.slice(f.indexOf("=") + 1);
        return [name, { filename: path.basename(file), data: fs.readFileSync(file) }];
      }),
    );
    const { body, contentType } = client.buildMultipart(fields, files);
    Object.assign(request, { body, contentType });
  }
  out(await client.signedRequest(request));
}

/** Executa o subcomando e devolve o código de saída. argv: o que vem depois de "node cli.js". */
async function main(argv, { stdout = console.log, stderr = console.error } = {}) {
  const [command, ...rest] = argv;
  const out = (value) => stdout(JSON.stringify(value, null, 2));
  try {
    if (command === "identity") {
      const [sub, ...args] = rest;
      const { opts } = parseArgs(args, { flags: ["force"] });
      if (sub === "new") await identityNew(opts, out);
      else if (sub === "show") await identityShow(opts, out);
      else if (sub === "bench") identityBench(opts, out, stderr);
      else throw new client.ClientError("usage: identity new|show|bench");
    } else if (command === "run-from-cids") {
      const { opts } = parseArgs(rest);
      if (!opts.dataset || !opts.application) throw new client.ClientError("usage: run-from-cids --dataset ID --application ID");
      const json = { datasetId: String(opts.dataset), applicationId: String(opts.application) };
      if (opts.user) json.user = opts.user;
      await signedCall({ ...opts, json: JSON.stringify(json) }, ["POST", "/api/run-from-cids"], out);
    } else if (command === "api") {
      const { opts, positional } = parseArgs(rest, { multi: ["field", "file"] });
      await signedCall(opts, positional, out);
    } else {
      throw new client.ClientError(`unknown command: ${command}`);
    }
    return 0;
  } catch (e) {
    stderr(`error: ${e.message}`);
    if (e.body && typeof e.body === "object") stderr(JSON.stringify(e.body));
    return 1;
  }
}

module.exports = { COMMANDS, main, parseArgs };
