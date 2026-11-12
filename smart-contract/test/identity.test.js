/* T-1702: registro de identidade com prova de trabalho (identity.js e as rotas do api-server). */
const assert = require("node:assert");
const crypto = require("node:crypto");
const fs = require("node:fs");
const net = require("node:net");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");
const {
  DEFAULT_DIFFICULTY,
  INITIAL_BALANCE,
  IdentityRegistry,
  identityId,
  leadingZeroBits,
  powHash,
  solveProof,
  verifyProof,
} = require("../scripts/identity");

function newPublicKeyHex() {
  const { publicKey } = crypto.generateKeyPairSync("ed25519");
  return Buffer.from(publicKey.export({ format: "jwk" }).x, "base64url").toString("hex");
}

function tempStatePath() {
  return path.join(fs.mkdtempSync(path.join(os.tmpdir(), "dnat-identity-")), "identities.json");
}

/** Primeiro nonce cujo hash tem exatamente `bits` zeros no início (nem mais, nem menos). */
function nonceWithExactZeros(challenge, key, bits) {
  for (let n = 0n; ; n += 1n) {
    if (leadingZeroBits(powHash(challenge, key, n)) === bits) return n;
  }
}

describe("identity.js: prova de trabalho (T-1702)", function () {
  const challenge = crypto.randomBytes(32);

  it("id é o SHA-256 da chave pública crua", function () {
    const key = newPublicKeyHex();
    const expected = crypto.createHash("sha256").update(Buffer.from(key, "hex")).digest("hex");
    assert.strictEqual(identityId(key), expected);
  });

  it("conta os bits zero do início do hash", function () {
    assert.strictEqual(leadingZeroBits(Buffer.from([0x80])), 0);
    assert.strictEqual(leadingZeroBits(Buffer.from([0x01])), 7);
    assert.strictEqual(leadingZeroBits(Buffer.from([0x00, 0x00, 0x10])), 19);
    assert.strictEqual(leadingZeroBits(Buffer.alloc(32)), 256);
  });

  it("dificuldade: prova com d−1 zeros falha em d e vale em d−1", function () {
    const key = Buffer.from(newPublicKeyHex(), "hex");
    const n = nonceWithExactZeros(challenge, key, 9);
    assert.strictEqual(verifyProof(challenge, key, n, 9), true);
    assert.strictEqual(verifyProof(challenge, key, n, 10), false);
  });

  it("a prova amarra a chave e o desafio da implantação", function () {
    const key = Buffer.from(newPublicKeyHex(), "hex");
    const n = solveProof(challenge, key, 12);
    assert.strictEqual(verifyProof(challenge, key, n, 12), true);
    // O mesmo nonce com outra chave ou outro desafio só vale por sorte (2^-12 cada); entre 5
    // tentativas, ao menos uma é recusada (falha espúria com chance 2^-60).
    const otherKeys = Array.from({ length: 5 }, () => Buffer.from(newPublicKeyHex(), "hex"));
    const otherChallenges = Array.from({ length: 5 }, () => crypto.randomBytes(32));
    assert.ok(otherKeys.some((k) => !verifyProof(challenge, k, n, 12)));
    assert.ok(otherChallenges.some((c) => !verifyProof(c, key, n, 12)));
  });

  it("registro: prova válida abre saldo Q; inválida, chave repetida e chave malformada são recusadas", function () {
    const statePath = tempStatePath();
    const reg = new IdentityRegistry({ statePath, difficulty: 10 });
    const ch = Buffer.from(reg.challenge().challenge, "hex");
    const key = newPublicKeyHex();
    const nonce = solveProof(ch, Buffer.from(key, "hex"), 10);

    const bad = nonceWithExactZeros(ch, Buffer.from(key, "hex"), 3);
    assert.throws(() => reg.register({ publicKey: key, nonce: bad.toString() }), (e) => e.status === 400);

    const rec = reg.register({ publicKey: key, nonce: nonce.toString() });
    assert.strictEqual(rec.id, identityId(key));
    assert.strictEqual(rec.balance, INITIAL_BALANCE);
    assert.strictEqual(rec.difficulty, 10);
    assert.strictEqual(rec.nonce, nonce.toString());

    assert.throws(() => reg.register({ publicKey: key, nonce: nonce.toString() }), (e) => e.status === 409);
    assert.throws(() => reg.register({ publicKey: "zz", nonce: "1" }), (e) => e.status === 400);
    assert.throws(() => reg.register({ publicKey: key, nonce: "-1" }), (e) => e.status === 400);
    assert.throws(() => reg.register({ publicKey: key, nonce: (1n << 64n).toString() }), (e) => e.status === 400);

    // Persistido: um registro novo sobre o mesmo arquivo mantém desafio e identidade.
    const again = new IdentityRegistry({ statePath, difficulty: 10 });
    assert.strictEqual(again.challenge().challenge, reg.challenge().challenge);
    assert.deepStrictEqual(again.get(rec.id), rec);
  });

  it("valores do protótipo: d = 20 e Q = 20", function () {
    assert.strictEqual(DEFAULT_DIFFICULTY, 20);
    assert.strictEqual(INITIAL_BALANCE, 20);
  });
});

describe("api-server: rotas de identidade (T-1702)", function () {
  this.timeout(120_000);

  const challenge = crypto.randomBytes(32).toString("hex");
  const key = newPublicKeyHex();
  const otherKey = newPublicKeyHex();
  let nonce;
  let foreignNonce;
  let server;
  let base;
  let statePath;

  before(async function () {
    // d = 20, o padrão do protótipo: em média 2^20 hashes, segundos de CPU.
    // A mineração é síncrona: fica toda aqui, antes de abrir conexões com o servidor.
    nonce = solveProof(Buffer.from(challenge, "hex"), Buffer.from(key, "hex"), DEFAULT_DIFFICULTY);
    foreignNonce = solveProof(crypto.randomBytes(32), Buffer.from(otherKey, "hex"), DEFAULT_DIFFICULTY);

    const port = await new Promise((resolve) => {
      const s = net.createServer().listen(0, "127.0.0.1", () => {
        const p = s.address().port;
        s.close(() => resolve(p));
      });
    });
    statePath = tempStatePath();
    const env = { ...process.env, WEB_PORT: String(port), DNAT_IDENTITIES_PATH: statePath, DNAT_IDENTITY_CHALLENGE: challenge };
    delete env.DNAT_IDENTITY_DIFFICULTY;
    delete env.CONTRACT_ADDRESS;
    server = spawn(process.execPath, [path.join(__dirname, "..", "scripts", "api-server.js")], {
      cwd: path.join(__dirname, ".."),
      env,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stderr = "";
    server.stderr.on("data", (c) => (stderr += c));
    await new Promise((resolve, reject) => {
      server.stdout.on("data", (c) => String(c).includes("running on") && resolve());
      server.on("exit", (code) => reject(new Error(`api-server saiu (${code}): ${stderr}`)));
    });
    base = `http://127.0.0.1:${port}`;
  });

  after(function () {
    server?.kill();
  });

  const post = (body) =>
    fetch(`${base}/api/identity/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

  it("GET /api/identity/challenge devolve o desafio da implantação e d = 20", async function () {
    const res = await fetch(`${base}/api/identity/challenge`);
    assert.strictEqual(res.status, 200);
    assert.deepStrictEqual(await res.json(), { challenge, difficulty: 20 });
  });

  it("POST /api/identity/register: prova inválida recebe 400", async function () {
    const res = await post({ publicKey: key, nonce: (nonce + 1n).toString() });
    // nonce + 1 só seria válido com chance 2^-20; nesse caso o teste seguinte acusaria 409.
    assert.strictEqual(res.status, 400);
    assert.match((await res.json()).error, /invalid proof of work/);
  });

  it("POST /api/identity/register: prova válida registra com saldo Q = 20 e grava identities.json", async function () {
    const res = await post({ publicKey: key, nonce: nonce.toString() });
    assert.strictEqual(res.status, 201);
    const body = await res.json();
    assert.strictEqual(body.id, identityId(key));
    assert.strictEqual(body.balance, 20);
    assert.strictEqual(body.difficulty, 20);

    const saved = JSON.parse(fs.readFileSync(statePath, "utf8"));
    assert.strictEqual(saved.challenge, challenge);
    assert.strictEqual(saved.identities[body.id].publicKey, key);
    assert.strictEqual(saved.identities[body.id].nonce, nonce.toString());
    assert.ok(saved.identities[body.id].registeredAtUtc);
  });

  it("POST /api/identity/register: chave repetida recebe 409", async function () {
    const res = await post({ publicKey: key, nonce: nonce.toString() });
    assert.strictEqual(res.status, 409);
  });

  it("POST /api/identity/register: prova feita para outro desafio recebe 400", async function () {
    // Só valeria aqui por sorte (2^-20); nesse caso raro o teste aponta 201 em vez de 400.
    const res = await post({ publicKey: otherKey, nonce: foreignNonce.toString() });
    assert.strictEqual(res.status, 400);
  });
});
