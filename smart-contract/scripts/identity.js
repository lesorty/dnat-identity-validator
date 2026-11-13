/**
 * Registro de identidades com prova de trabalho na CVM1 (T-1702; D7, E14 §18.2–§18.3).
 *
 * - Identidade: par de chaves Ed25519 do próprio usuário; o id é o SHA-256 da chave pública
 *   (os 32 bytes crus da chave, em hex).
 * - Prova de trabalho, no molde do Hashcash:
 *       válida  ⇔  SHA-256(desafio ‖ chave_pública ‖ nonce) começa com d bits zero
 *   desafio: 32 bytes fixos da implantação; chave: 32 bytes crus; nonce: inteiro sem sinal de
 *   64 bits em 8 bytes big-endian. Quem registra testa em média 2^d nonces; a CVM1 confere com
 *   um hash. A prova amarra a chave: não vale para outra chave nem para outra implantação.
 * - Estado: identities.json na pasta de estado da CVM1 (ao lado de executions/), com o desafio
 *   e, por id, a chave, o nonce, d, a data e o saldo inicial Q.
 *
 * - Pedidos assinados (T-1703, E14 §18.2): as rotas que criam trabalho exigem os cabeçalhos
 *       X-Identity   id da identidade (64 hex)
 *       X-Timestamp  carimbo em milissegundos desde 1970 (inteiro decimal, UTC)
 *       X-Signature  assinatura Ed25519 (64 bytes em hex) sobre a mensagem
 *           "DNAT-REQUEST-v1\n" + MÉTODO + "\n" + caminho + "\n" + carimbo + "\n" + SHA-256(corpo) em hex
 *   O caminho é o da requisição com a query (req.originalUrl); o corpo são os bytes crus enviados
 *   (vazio se não há corpo). Carimbo fora de ±5 min, identidade desconhecida, assinatura errada ou
 *   pedido já visto dentro da janela recebem 401. A repetição é barrada por um registro em memória
 *   dos pedidos aceitos na janela; um carimbo velho já é recusado pelo relógio.
 *
 * - Livro de cotas (T-1704, E14 §18.4, D7): o saldo da identidade é o que limita o número de
 *   derivados que ela leva ao Juiz. No aceite do job, reserve() tira RESERVE_COST = 5 do saldo e
 *   recusa o pedido sem saldo (402). No veredito, settle() cobra 1 (aprovado), 2 (inconclusivo
 *   de mérito) ou 5 (reprovado) e devolve a diferença; falha do job devolve tudo e não conta.
 *   O acerto vale uma vez por reserva (um segundo settle devolve o primeiro, sem cobrar de novo).
 *   O registro guarda, por identidade, o saldo livre, o total reservado, o gasto e a contagem por
 *   desfecho; summary() é o que a rota GET /api/identity/:id mostra. Sem recarga no MVP (D7).
 *
 * Só o módulo crypto do Node.
 */
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

// Provisórios até a T-1705 (d) e a T-1708 (Q), E14 §18.3 e §18.4.
const DEFAULT_DIFFICULTY = 20;
const INITIAL_BALANCE = 20;
const MAX_DIFFICULTY = 64;
const MAX_NONCE = (1n << 64n) - 1n;

// Custos por desfecho (D7, E14 §18.4); provisórios até a T-1708 fixar Q com o modelo de custo.
const RESERVE_COST = 5;
const SETTLE_COSTS = { approved: 1, inconclusive: 2, rejected: 5, failure: 0 };
const OUTCOME_ALIASES = {
  approved: "approved",
  aprovado: "approved",
  inconclusive: "inconclusive",
  inconclusivo: "inconclusive",
  rejected: "rejected",
  reprovado: "rejected",
  failure: "failure",
  failed: "failure",
  inconclusive_failure: "failure",
};

class IdentityError extends Error {
  constructor(message, status = 400) {
    super(message);
    this.status = status;
  }
}

function sha256(...parts) {
  const h = crypto.createHash("sha256");
  for (const p of parts) h.update(p);
  return h.digest();
}

function parseHex32(value, what) {
  const s = String(value || "").trim().toLowerCase().replace(/^0x/, "");
  if (!/^[0-9a-f]{64}$/.test(s)) throw new IdentityError(`${what} must be 32 bytes in hex`);
  return Buffer.from(s, "hex");
}

/** Chave pública Ed25519 crua (32 bytes); recusa o que o Node não aceita como Ed25519. */
function parsePublicKey(value) {
  const raw = parseHex32(value, "publicKey");
  try {
    crypto.createPublicKey({ key: { kty: "OKP", crv: "Ed25519", x: raw.toString("base64url") }, format: "jwk" });
  } catch {
    throw new IdentityError("publicKey is not a valid Ed25519 key");
  }
  return raw;
}

function parseNonce(value) {
  const s = String(value ?? "").trim();
  if (!/^[0-9]{1,20}$/.test(s)) throw new IdentityError("nonce must be a non-negative integer (64 bits)");
  const n = BigInt(s);
  if (n > MAX_NONCE) throw new IdentityError("nonce must fit in 64 bits");
  return n;
}

function encodeNonce(nonce) {
  const buf = Buffer.alloc(8);
  buf.writeBigUInt64BE(BigInt(nonce));
  return buf;
}

function identityId(publicKey) {
  const raw = Buffer.isBuffer(publicKey) ? publicKey : parsePublicKey(publicKey);
  return sha256(raw).toString("hex");
}

function powHash(challenge, publicKey, nonce) {
  return sha256(challenge, publicKey, encodeNonce(nonce));
}

function leadingZeroBits(buf) {
  let bits = 0;
  for (const byte of buf) {
    if (byte === 0) {
      bits += 8;
      continue;
    }
    return bits + Math.clz32(byte) - 24;
  }
  return bits;
}

function verifyProof(challenge, publicKey, nonce, difficulty) {
  return leadingZeroBits(powHash(challenge, publicKey, nonce)) >= difficulty;
}

/** Procura um nonce válido a partir de start: o trabalho de quem registra (testes e cliente). */
function solveProof(challenge, publicKey, difficulty, start = 0n) {
  for (let nonce = BigInt(start); nonce <= MAX_NONCE; nonce += 1n) {
    if (verifyProof(challenge, publicKey, nonce, difficulty)) return nonce;
  }
  throw new IdentityError("no nonce found");
}

function parseDifficulty(value) {
  const d = Number(value);
  if (!Number.isInteger(d) || d < 0 || d > MAX_DIFFICULTY) {
    throw new Error(`identity difficulty must be an integer in [0, ${MAX_DIFFICULTY}]`);
  }
  return d;
}

// ---------------------------------------------------------------------------------------------
// Pedidos assinados (T-1703)
// ---------------------------------------------------------------------------------------------

const REQUEST_SIGNATURE_TAG = "DNAT-REQUEST-v1";
const MAX_CLOCK_SKEW_MS = 5 * 60 * 1000;
const SIGNATURE_HEADERS = { identity: "x-identity", timestamp: "x-timestamp", signature: "x-signature" };

// Prefixo PKCS#8 de uma chave privada Ed25519 (RFC 8410): basta acrescentar a semente de 32 bytes.
const ED25519_PKCS8_PREFIX = Buffer.from("302e020100300506032b657004220420", "hex");

function bodyHash(body) {
  if (body === undefined || body === null) return sha256(Buffer.alloc(0)).toString("hex");
  return sha256(Buffer.isBuffer(body) ? body : Buffer.from(String(body), "utf8")).toString("hex");
}

/** Bytes que a identidade assina: método, caminho, carimbo e SHA-256 do corpo, com rótulo de versão. */
function requestMessage({ method, path: requestPath, timestamp, body }) {
  return Buffer.from(
    [REQUEST_SIGNATURE_TAG, String(method).toUpperCase(), String(requestPath), String(timestamp), bodyHash(body)].join("\n"),
    "utf8",
  );
}

function privateKeyObject(privateKey) {
  if (privateKey instanceof crypto.KeyObject) return privateKey;
  const seed = parseHex32(privateKey, "privateKey");
  return crypto.createPrivateKey({ key: Buffer.concat([ED25519_PKCS8_PREFIX, seed]), format: "der", type: "pkcs8" });
}

function publicKeyObject(publicKeyHex) {
  const raw = parseHex32(publicKeyHex, "publicKey");
  return crypto.createPublicKey({ key: { kty: "OKP", crv: "Ed25519", x: raw.toString("base64url") }, format: "jwk" });
}

/**
 * Cabeçalhos de um pedido assinado (para os testes e para o cliente da T-1705). privateKey: KeyObject
 * Ed25519 ou a semente de 32 bytes em hex; publicKey: chave crua em hex (dá o id).
 */
function signRequest({ privateKey, publicKey, method, path: requestPath, body, timestamp = Date.now() }) {
  const signature = crypto.sign(null, requestMessage({ method, path: requestPath, timestamp, body }), privateKeyObject(privateKey));
  return {
    "X-Identity": identityId(publicKey),
    "X-Timestamp": String(timestamp),
    "X-Signature": signature.toString("hex"),
  };
}

/**
 * Confere pedidos assinados contra o registro de identidades. Guarda em memória os pedidos aceitos
 * até o carimbo sair da janela: o mesmo pedido (mesma identidade e mesma mensagem) não passa duas
 * vezes. A chave do registro é o hash da mensagem, não a assinatura, para não depender de a
 * assinatura ser única.
 */
class RequestVerifier {
  constructor({ registry, maxSkewMs = MAX_CLOCK_SKEW_MS, now = () => Date.now() }) {
    this.registry = registry;
    this.maxSkewMs = maxSkewMs;
    this.now = now;
    this.seen = new Map(); // id:hash da mensagem -> instante a partir do qual o carimbo já é velho
  }

  _prune(now) {
    for (const [key, expiresAt] of this.seen) {
      if (expiresAt < now) this.seen.delete(key);
    }
  }

  /** Devolve o registro da identidade ou lança IdentityError com status 401. */
  verify({ method, path: requestPath, headers, body }) {
    const get = (name) => {
      const v = headers?.[name];
      return Array.isArray(v) ? v[0] : v;
    };
    const id = String(get(SIGNATURE_HEADERS.identity) || "").trim().toLowerCase();
    const ts = String(get(SIGNATURE_HEADERS.timestamp) || "").trim();
    const sig = String(get(SIGNATURE_HEADERS.signature) || "").trim().toLowerCase();
    if (!id || !ts || !sig) throw new IdentityError("signed request required (X-Identity, X-Timestamp, X-Signature)", 401);
    if (!/^[0-9a-f]{64}$/.test(id)) throw new IdentityError("X-Identity must be 32 bytes in hex", 401);
    if (!/^[0-9]{1,16}$/.test(ts)) throw new IdentityError("X-Timestamp must be milliseconds since epoch", 401);
    if (!/^[0-9a-f]{128}$/.test(sig)) throw new IdentityError("X-Signature must be 64 bytes in hex", 401);

    const now = this.now();
    const timestamp = Number(ts);
    if (Math.abs(now - timestamp) > this.maxSkewMs) throw new IdentityError("request timestamp outside the allowed window", 401);

    const record = this.registry.get(id);
    if (!record) throw new IdentityError("unknown identity", 401);

    const message = requestMessage({ method, path: requestPath, timestamp: ts, body });
    let valid = false;
    try {
      valid = crypto.verify(null, message, publicKeyObject(record.publicKey), Buffer.from(sig, "hex"));
    } catch {
      valid = false;
    }
    if (!valid) throw new IdentityError("invalid request signature", 401);

    this._prune(now);
    const key = `${id}:${sha256(message).toString("hex")}`;
    if (this.seen.has(key)) throw new IdentityError("replayed request", 401);
    this.seen.set(key, timestamp + this.maxSkewMs);
    return record;
  }

  /**
   * Middleware do Express. Vai depois do leitor do corpo: usa req.body se for Buffer (rotas
   * multipart) ou req.rawBody (gravado pelo express.json com verify); sem nenhum dos dois, corpo vazio.
   */
  middleware() {
    return (req, res, next) => {
      try {
        const body = Buffer.isBuffer(req.body) ? req.body : req.rawBody;
        req.identity = this.verify({ method: req.method, path: req.originalUrl, headers: req.headers, body });
        next();
      } catch (e) {
        res.status(e instanceof IdentityError ? e.status : 401).json({ error: e.message });
      }
    };
  }
}

/** Grava o id da identidade que pediu o job no metadata.json da execução (T-1703; a T-809 o leva ao recibo). */
function recordExecutionIdentity(metadataPath, id, extra = {}) {
  if (!id || !fs.existsSync(metadataPath)) return false;
  let metadata;
  try {
    metadata = JSON.parse(fs.readFileSync(metadataPath, "utf8"));
  } catch {
    return false; // metadata ilegível: não derruba a resposta do job
  }
  fs.writeFileSync(metadataPath, JSON.stringify({ ...metadata, identityId: id, ...extra }, null, 2), "utf8");
  return true;
}

function normalizeOutcome(value) {
  const outcome = OUTCOME_ALIASES[String(value ?? "").trim().toLowerCase()];
  if (!outcome) throw new IdentityError(`unknown outcome: ${JSON.stringify(value)}`);
  return outcome;
}

function emptyCounts() {
  return { approved: 0, inconclusive: 0, rejected: 0, failure: 0 };
}

/**
 * Registro persistido em um arquivo JSON. O desafio vem de DNAT_IDENTITY_CHALLENGE (32 bytes em
 * hex) ou é sorteado na primeira carga e fica gravado no arquivo, fixo para a implantação.
 */
class IdentityRegistry {
  constructor({ statePath, difficulty = DEFAULT_DIFFICULTY, challenge = null, initialBalance = INITIAL_BALANCE }) {
    this.statePath = statePath;
    this.difficulty = parseDifficulty(difficulty);
    this.initialBalance = initialBalance;
    this.state = this._load();
    if (challenge) {
      this.state.challenge = parseHex32(challenge, "challenge").toString("hex");
    } else if (!this.state.challenge) {
      this.state.challenge = crypto.randomBytes(32).toString("hex");
    }
    this._save();
  }

  _load() {
    if (!fs.existsSync(this.statePath)) return { challenge: null, identities: {}, ledger: {} };
    const parsed = JSON.parse(fs.readFileSync(this.statePath, "utf8"));
    return { challenge: parsed.challenge || null, identities: parsed.identities || {}, ledger: parsed.ledger || {} };
  }

  _save() {
    fs.mkdirSync(path.dirname(this.statePath), { recursive: true });
    const tmp = `${this.statePath}.${process.pid}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(this.state, null, 2), "utf8");
    fs.renameSync(tmp, this.statePath);
  }

  challenge() {
    return { challenge: this.state.challenge, difficulty: this.difficulty };
  }

  get(id) {
    return this.state.identities[String(id || "").toLowerCase()] || null;
  }

  /** Confere a prova com um hash e abre o saldo Q. Chave repetida: 409. */
  register({ publicKey, nonce }) {
    const key = parsePublicKey(publicKey);
    const n = parseNonce(nonce);
    const id = identityId(key);
    if (this.state.identities[id]) throw new IdentityError("identity already registered", 409);
    if (!verifyProof(Buffer.from(this.state.challenge, "hex"), key, n, this.difficulty)) {
      throw new IdentityError(`invalid proof of work for difficulty ${this.difficulty}`);
    }

    const record = {
      id,
      publicKey: key.toString("hex"),
      nonce: n.toString(),
      difficulty: this.difficulty,
      registeredAtUtc: new Date().toISOString(),
      initialBalance: this.initialBalance,
      balance: this.initialBalance,
      reserved: 0,
      spent: 0,
      counts: emptyCounts(),
    };
    this.state.identities[id] = record;
    this._save();
    return record;
  }

  /** Completa o que um registro anterior à T-1704 não tem (só saldo e data). */
  _ledgerRecord(id) {
    const record = this.get(id);
    if (!record) return null;
    record.initialBalance ??= this.initialBalance;
    record.reserved ??= 0;
    record.spent ??= 0;
    record.counts = { ...emptyCounts(), ...(record.counts || {}) };
    return record;
  }

  /**
   * Reserva RESERVE_COST no aceite do job (E14 §18.4). Sem saldo livre: 402 e nada muda. A reserva
   * tem um id próprio (reservationId) que o settle usa; o mesmo id não reserva duas vezes (409).
   */
  reserve(identityId, reservationId) {
    const record = this._ledgerRecord(identityId);
    if (!record) throw new IdentityError("unknown identity", 404);
    const key = String(reservationId ?? "").trim();
    if (!key) throw new IdentityError("reservationId required");
    if (this.state.ledger[key]) throw new IdentityError("reservation already exists", 409);
    if (record.balance < RESERVE_COST) {
      throw new IdentityError(`insufficient quota: balance ${record.balance}, a job reserves ${RESERVE_COST}`, 402);
    }
    record.balance -= RESERVE_COST;
    record.reserved += RESERVE_COST;
    this.state.ledger[key] = {
      reservationId: key,
      identityId: record.id,
      reserved: RESERVE_COST,
      status: "reserved",
      reservedAtUtc: new Date().toISOString(),
    };
    this._save();
    return { ...this.state.ledger[key], balance: record.balance };
  }

  /**
   * Acerta a reserva pelo desfecho (E14 §18.4): aprovado cobra 1, inconclusivo 2, reprovado 5 e
   * devolve a diferença; falha do job (T-107) devolve tudo e não entra na contagem. Conta uma vez
   * por reserva: o segundo acerto devolve o primeiro, com repeated = true, sem cobrar de novo.
   */
  settle(reservationId, outcome) {
    const key = String(reservationId ?? "").trim();
    const entry = this.state.ledger[key];
    if (!entry) throw new IdentityError("unknown reservation", 404);
    if (entry.status === "settled") {
      return { ...entry, balance: this.get(entry.identityId).balance, repeated: true };
    }
    const result = normalizeOutcome(outcome);
    const record = this._ledgerRecord(entry.identityId);
    const charged = SETTLE_COSTS[result];
    const refunded = entry.reserved - charged;
    record.reserved -= entry.reserved;
    record.balance += refunded;
    record.spent += charged;
    record.counts[result] += 1;
    Object.assign(entry, {
      status: "settled",
      outcome: result,
      charged,
      refunded,
      settledAtUtc: new Date().toISOString(),
    });
    this._save();
    return { ...entry, balance: record.balance, repeated: false };
  }

  /** Saldo e contagens de uma identidade, para a rota de consulta (auditor e modelo do atacante). */
  summary(id) {
    const record = this._ledgerRecord(id);
    if (!record) return null;
    return {
      id: record.id,
      publicKey: record.publicKey,
      difficulty: record.difficulty,
      registeredAtUtc: record.registeredAtUtc,
      initialBalance: record.initialBalance,
      balance: record.balance,
      reserved: record.reserved,
      spent: record.spent,
      counts: { ...record.counts },
    };
  }
}

module.exports = {
  DEFAULT_DIFFICULTY,
  INITIAL_BALANCE,
  RESERVE_COST,
  SETTLE_COSTS,
  MAX_CLOCK_SKEW_MS,
  REQUEST_SIGNATURE_TAG,
  IdentityError,
  IdentityRegistry,
  RequestVerifier,
  bodyHash,
  encodeNonce,
  identityId,
  leadingZeroBits,
  normalizeOutcome,
  powHash,
  recordExecutionIdentity,
  requestMessage,
  signRequest,
  solveProof,
  verifyProof,
};
