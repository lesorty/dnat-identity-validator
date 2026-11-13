/**
 * Cliente de identidade do usuário (T-1705; D7, E14 §18): gera a chave Ed25519, minera a prova de
 * trabalho para o desafio da CVM1, registra, guarda a chave em um arquivo local e assina os
 * pedidos às rotas que criam trabalho (T-1703). Mede também o custo da prova por dificuldade
 * (C_id, para o modelo de custo da T-1708).
 *
 * Sem hardhat nem ethers: só o crypto do Node e o fetch. O formato da assinatura é o de
 * identity.js (signRequest); o servidor confere com o mesmo módulo.
 *
 * Arquivo da chave (JSON, modo 0600): { version, id, publicKey, seed, apiUrl?, registeredAtUtc? }.
 * A semente de 32 bytes em hex é a chave privada; quem a tem assina como a identidade.
 */
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { identityId, signRequest, solveProof } = require("./identity");

const KEY_FILE_VERSION = 1;
const DEFAULT_API_URL = process.env.DNAT_API_URL || "http://127.0.0.1:3001";
const DEFAULT_KEY_FILE = process.env.DNAT_IDENTITY_KEY || path.join(os.homedir(), ".dnat", "identity.json");

class ClientError extends Error {
  constructor(message, status = null, body = null) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

function generateIdentity() {
  const { publicKey, privateKey } = crypto.generateKeyPairSync("ed25519");
  const pub = Buffer.from(publicKey.export({ format: "jwk" }).x, "base64url").toString("hex");
  const seed = Buffer.from(privateKey.export({ format: "jwk" }).d, "base64url").toString("hex");
  return { id: identityId(pub), publicKey: pub, seed };
}

/** Grava a chave sem sobrescrever outra (a chave perdida é uma identidade perdida, com o saldo). */
function saveKeyFile(file, identity, { overwrite = false } = {}) {
  if (fs.existsSync(file) && !overwrite) throw new ClientError(`key file already exists: ${file}`);
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify({ version: KEY_FILE_VERSION, ...identity }, null, 2), { mode: 0o600 });
  fs.renameSync(tmp, file);
}

function loadKeyFile(file) {
  if (!fs.existsSync(file)) throw new ClientError(`key file not found: ${file} (run: identity new)`);
  const data = JSON.parse(fs.readFileSync(file, "utf8"));
  if (data.version !== KEY_FILE_VERSION) throw new ClientError(`unsupported key file version: ${data.version}`);
  if (identityId(data.publicKey) !== data.id) throw new ClientError("key file: id does not match the public key");
  return data;
}

function apiBase(apiUrl) {
  return String(apiUrl || DEFAULT_API_URL).replace(/\/+$/, "");
}

async function readResponse(res) {
  const text = await res.text();
  let body = text;
  try {
    body = JSON.parse(text);
  } catch {
    // corpo que não é JSON segue como texto
  }
  if (!res.ok) throw new ClientError(`${res.status} ${body?.error || text}`.trim(), res.status, body);
  return body;
}

/** Busca o desafio, minera o nonce e registra. Devolve o registro e o tempo da prova. */
async function registerIdentity({ apiUrl, identity, fetchImpl = fetch, solve = solveProof }) {
  const base = apiBase(apiUrl);
  const { challenge, difficulty } = await readResponse(await fetchImpl(`${base}/api/identity/challenge`));
  const started = process.hrtime.bigint();
  const nonce = solve(Buffer.from(challenge, "hex"), Buffer.from(identity.publicKey, "hex"), difficulty);
  const proofSeconds = Number(process.hrtime.bigint() - started) / 1e9;
  const record = await readResponse(
    await fetchImpl(`${base}/api/identity/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ publicKey: identity.publicKey, nonce: nonce.toString() }),
    }),
  );
  return { record, difficulty, nonce: nonce.toString(), proofSeconds };
}

/**
 * Corpo multipart/form-data montado à mão, para assinar os bytes exatos que seguem (o curl -F não
 * deixa assinar antes). fields: {nome: texto}; files: {nome: {filename, data: Buffer, type}}.
 */
function buildMultipart(fields = {}, files = {}, boundary = `----dnat${crypto.randomBytes(12).toString("hex")}`) {
  const parts = [];
  for (const [name, value] of Object.entries(fields)) {
    parts.push(Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="${name}"\r\n\r\n${value}\r\n`));
  }
  for (const [name, f] of Object.entries(files)) {
    const type = f.type || "application/octet-stream";
    parts.push(Buffer.from(
      `--${boundary}\r\nContent-Disposition: form-data; name="${name}"; filename="${f.filename}"\r\nContent-Type: ${type}\r\n\r\n`,
    ));
    parts.push(f.data, Buffer.from("\r\n"));
  }
  parts.push(Buffer.from(`--${boundary}--\r\n`));
  return { body: Buffer.concat(parts), contentType: `multipart/form-data; boundary=${boundary}` };
}

/**
 * Pedido assinado pela identidade. json: objeto enviado como JSON; ou body (Buffer) com contentType.
 * O caminho assinado é o da requisição com a query, o mesmo que o servidor lê (req.originalUrl).
 */
async function signedRequest({ apiUrl, identity, method = "POST", path: requestPath, json, body, contentType, fetchImpl = fetch }) {
  let payload = body;
  let type = contentType;
  if (json !== undefined) {
    payload = Buffer.from(JSON.stringify(json), "utf8");
    type = "application/json";
  }
  const headers = signRequest({ privateKey: identity.seed, publicKey: identity.publicKey, method, path: requestPath, body: payload });
  if (type) headers["Content-Type"] = type;
  const res = await fetchImpl(`${apiBase(apiUrl)}${requestPath}`, { method, headers, body: payload });
  return readResponse(res);
}

// ---------------------------------------------------------------------------------------------
// Custo da prova por dificuldade (C_id)
// ---------------------------------------------------------------------------------------------

function median(values) {
  const s = [...values].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

/**
 * Mede a taxa de hash do mesmo laço que o cliente usa (SHA-256 de desafio ‖ chave ‖ nonce) e o
 * tempo real da prova para cada d, com chave e desafio novos a cada repetição. O tempo de uma
 * prova é geométrico (média 2^d hashes, desvio quase igual à média), então 5 repetições dão só
 * a ordem de grandeza; a coluna esperada (2^d ÷ taxa) é a que serve ao modelo de custo.
 */
function benchProof({ minBits = 12, maxBits = 24, reps = 5, solve = solveProof, now = () => process.hrtime.bigint(), onRow = () => {} } = {}) {
  if (!(Number.isInteger(minBits) && Number.isInteger(maxBits) && minBits >= 0 && minBits <= maxBits)) {
    throw new ClientError("bench: need integers 0 <= min <= max");
  }
  if (!(Number.isInteger(reps) && reps >= 1)) throw new ClientError("bench: reps must be an integer >= 1");
  const rows = [];
  let totalHashes = 0;
  let totalSeconds = 0;
  const timed = (d) => {
    const key = crypto.randomBytes(32);
    const challenge = crypto.randomBytes(32);
    const t0 = now();
    const nonce = solve(challenge, key, d);
    const seconds = Number(now() - t0) / 1e9;
    const hashes = Number(nonce) + 1; // nonces testados: 0 … nonce
    totalHashes += hashes;
    totalSeconds += seconds;
    return { seconds, hashes };
  };
  const runs = new Map();
  for (let d = minBits; d <= maxBits; d += 1) {
    runs.set(d, Array.from({ length: reps }, () => timed(d)));
  }
  const rate = totalHashes / totalSeconds; // hashes por segundo, de todas as provas medidas
  for (const [d, list] of runs) {
    const seconds = list.map((r) => r.seconds);
    const row = {
      difficulty: d,
      reps,
      seconds,
      meanSeconds: seconds.reduce((a, b) => a + b, 0) / reps,
      medianSeconds: median(seconds),
      minSeconds: Math.min(...seconds),
      maxSeconds: Math.max(...seconds),
      expectedHashes: 2 ** d,
      expectedSeconds: 2 ** d / rate,
    };
    rows.push(row);
    onRow(row);
  }
  return { hashesPerSecond: rate, rows };
}

function machineInfo() {
  const cpus = os.cpus();
  return {
    cpuModel: cpus[0]?.model || "unknown",
    logicalCpus: cpus.length,
    node: process.version,
    platform: `${os.platform()} ${os.release()}`,
    note: "medido numa máquina local; a medida em VM de 4 vCPU fica para a T-210",
  };
}

const fmt = (x) => (x >= 100 ? x.toFixed(0) : x >= 1 ? x.toFixed(2) : x.toFixed(4));

function benchMarkdown(result, machine = machineInfo()) {
  const lines = [
    "# Custo da prova de trabalho por dificuldade (T-1705)",
    "",
    `Máquina: ${machine.cpuModel}, ${machine.logicalCpus} CPUs lógicas, Node ${machine.node}, ${machine.platform}.`,
    `Taxa medida: ${(result.hashesPerSecond / 1e6).toFixed(3)} milhões de hashes por segundo, um núcleo.`,
    "",
    "| d (bits) | repetições | média (s) | mediana (s) | mín (s) | máx (s) | esperado 2^d ÷ taxa (s) |",
    "|---:|---:|---:|---:|---:|---:|---:|",
    ...result.rows.map((r) =>
      `| ${r.difficulty} | ${r.reps} | ${fmt(r.meanSeconds)} | ${fmt(r.medianSeconds)} | ${fmt(r.minSeconds)} | ${fmt(r.maxSeconds)} | ${fmt(r.expectedSeconds)} |`),
    "",
    "O tempo de uma prova é geométrico: média 2^d hashes e desvio quase igual à média. Com poucas",
    "repetições a média medida oscila bastante; a coluna esperada é a estimativa para o modelo de custo.",
    machine.note ? `\n${machine.note}.` : "",
  ];
  return lines.join("\n") + "\n";
}

module.exports = {
  DEFAULT_API_URL,
  DEFAULT_KEY_FILE,
  ClientError,
  benchMarkdown,
  benchProof,
  buildMultipart,
  generateIdentity,
  loadKeyFile,
  machineInfo,
  registerIdentity,
  saveKeyFile,
  signedRequest,
};
