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
 * Só o módulo crypto do Node. Pedidos assinados (T-1703) e o livro de cotas (T-1704) ficam fora.
 */
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

// Provisórios até a T-1705 (d) e a T-1708 (Q), E14 §18.3 e §18.4.
const DEFAULT_DIFFICULTY = 20;
const INITIAL_BALANCE = 20;
const MAX_DIFFICULTY = 64;
const MAX_NONCE = (1n << 64n) - 1n;

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
    if (!fs.existsSync(this.statePath)) return { challenge: null, identities: {} };
    const parsed = JSON.parse(fs.readFileSync(this.statePath, "utf8"));
    return { challenge: parsed.challenge || null, identities: parsed.identities || {} };
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
      balance: this.initialBalance,
    };
    this.state.identities[id] = record;
    this._save();
    return record;
  }
}

module.exports = {
  DEFAULT_DIFFICULTY,
  INITIAL_BALANCE,
  IdentityError,
  IdentityRegistry,
  encodeNonce,
  identityId,
  leadingZeroBits,
  powHash,
  solveProof,
  verifyProof,
};
