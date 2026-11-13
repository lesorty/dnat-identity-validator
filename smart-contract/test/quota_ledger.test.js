/* T-1704: livro de cotas na CVM1: reserva no aceite, acerto no veredito (E14 §18.4, D7). */
const assert = require("node:assert");
const crypto = require("node:crypto");
const fs = require("node:fs");
const net = require("node:net");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");
const {
  INITIAL_BALANCE,
  RESERVE_COST,
  SETTLE_COSTS,
  IdentityRegistry,
  identityId,
  normalizeOutcome,
} = require("../scripts/identity");

function newPublicKeyHex() {
  const { publicKey } = crypto.generateKeyPairSync("ed25519");
  return Buffer.from(publicKey.export({ format: "jwk" }).x, "base64url").toString("hex");
}

function tempStatePath() {
  return path.join(fs.mkdtempSync(path.join(os.tmpdir(), "dnat-quota-")), "identities.json");
}

const rejectsWith = (call, status, re) =>
  assert.throws(call, (e) => {
    assert.strictEqual(e.status, status);
    assert.match(e.message, re);
    return true;
  });

describe("identity.js: livro de cotas (T-1704)", function () {
  let statePath;
  let registry;
  let alice;

  // d = 0: qualquer nonce vale; aqui só interessa o saldo.
  beforeEach(function () {
    statePath = tempStatePath();
    registry = new IdentityRegistry({ statePath, difficulty: 0 });
    alice = registry.register({ publicKey: newPublicKeyHex(), nonce: "0" });
  });

  const balance = () => registry.summary(alice.id).balance;

  it("valores do protótipo: Q = 20, reserva 5 e custos 1, 2 e 5; falha não cobra", function () {
    assert.strictEqual(INITIAL_BALANCE, 20);
    assert.strictEqual(RESERVE_COST, 5);
    assert.deepStrictEqual(SETTLE_COSTS, { approved: 1, inconclusive: 2, rejected: 5, failure: 0 });
  });

  it("a identidade nova abre com Q livre, nada reservado, nada gasto e contagens zeradas", function () {
    assert.deepStrictEqual(registry.summary(alice.id), {
      id: alice.id,
      publicKey: alice.publicKey,
      difficulty: 0,
      registeredAtUtc: alice.registeredAtUtc,
      initialBalance: 20,
      balance: 20,
      reserved: 0,
      spent: 0,
      counts: { approved: 0, inconclusive: 0, rejected: 0, failure: 0 },
    });
    assert.strictEqual(registry.summary("00".repeat(32)), null);
  });

  it("reserve tira 5 do saldo livre e soma em reservado", function () {
    const r = registry.reserve(alice.id, "job-1");
    assert.strictEqual(r.reserved, 5);
    assert.strictEqual(r.status, "reserved");
    const s = registry.summary(alice.id);
    assert.deepStrictEqual([s.balance, s.reserved, s.spent], [15, 5, 0]);
  });

  it("acerto: aprovado cobra 1 e devolve 4; inconclusivo cobra 2 e devolve 3; reprovado cobra 5", function () {
    for (const [outcome, charged, refunded] of [["approved", 1, 4], ["inconclusive", 2, 3], ["rejected", 5, 0]]) {
      registry.reserve(alice.id, `job-${outcome}`);
      const before = balance();
      const r = registry.settle(`job-${outcome}`, outcome);
      assert.deepStrictEqual([r.outcome, r.charged, r.refunded, r.repeated], [outcome, charged, refunded, false]);
      assert.strictEqual(balance(), before + refunded);
    }
    const s = registry.summary(alice.id);
    assert.deepStrictEqual(s.counts, { approved: 1, inconclusive: 1, rejected: 1, failure: 0 });
    assert.deepStrictEqual([s.balance, s.reserved, s.spent], [20 - 1 - 2 - 5, 0, 8]);
  });

  it("falha do job devolve a reserva inteira e não conta como veredito", function () {
    registry.reserve(alice.id, "job-f");
    const r = registry.settle("job-f", "failure");
    assert.deepStrictEqual([r.charged, r.refunded], [0, 5]);
    const s = registry.summary(alice.id);
    assert.deepStrictEqual([s.balance, s.reserved, s.spent], [20, 0, 0]);
    assert.deepStrictEqual(s.counts, { approved: 0, inconclusive: 0, rejected: 0, failure: 1 });
  });

  it("4 reprovados esgotam Q = 20 e o 5º job é recusado com 402, sem mudar nada", function () {
    for (let i = 1; i <= 4; i += 1) {
      registry.reserve(alice.id, `job-${i}`);
      registry.settle(`job-${i}`, "rejected");
    }
    assert.strictEqual(balance(), 0);
    const before = JSON.stringify(registry.summary(alice.id));
    rejectsWith(() => registry.reserve(alice.id, "job-5"), 402, /insufficient quota/);
    assert.strictEqual(JSON.stringify(registry.summary(alice.id)), before);
    assert.strictEqual(registry.summary(alice.id).counts.rejected, 4);
  });

  it("a reserva em aberto já conta contra o saldo: não se emitem mais jobs do que o saldo cobre", function () {
    for (let i = 1; i <= 4; i += 1) registry.reserve(alice.id, `job-${i}`); // 4 × 5 = 20, nenhum acertado
    rejectsWith(() => registry.reserve(alice.id, "job-5"), 402, /insufficient quota/);
    registry.settle("job-1", "failure"); // a falha devolve e abre espaço
    registry.reserve(alice.id, "job-5");
  });

  it("o acerto conta uma vez por reserva: o segundo devolve o primeiro, sem cobrar nem contar de novo", function () {
    registry.reserve(alice.id, "job-1");
    const first = registry.settle("job-1", "approved");
    const again = registry.settle("job-1", "rejected"); // outro desfecho, mesma reserva
    assert.strictEqual(again.repeated, true);
    assert.strictEqual(again.outcome, "approved");
    assert.strictEqual(again.charged, first.charged);
    const s = registry.summary(alice.id);
    assert.deepStrictEqual([s.balance, s.spent], [19, 1]);
    assert.deepStrictEqual(s.counts, { approved: 1, inconclusive: 0, rejected: 0, failure: 0 });
  });

  it("recusas: identidade e reserva desconhecidas, reserva repetida e desfecho inválido", function () {
    rejectsWith(() => registry.reserve("00".repeat(32), "j"), 404, /unknown identity/);
    rejectsWith(() => registry.reserve(alice.id, ""), 400, /reservationId required/);
    rejectsWith(() => registry.settle("nao-existe", "approved"), 404, /unknown reservation/);
    registry.reserve(alice.id, "job-1");
    rejectsWith(() => registry.reserve(alice.id, "job-1"), 409, /already exists/);
    rejectsWith(() => registry.settle("job-1", "talvez"), 400, /unknown outcome/);
    assert.strictEqual(registry.summary(alice.id).reserved, 5); // o desfecho inválido não acertou nada
    assert.strictEqual(registry.settle("job-1", "approved").charged, 1);
  });

  it("aceita os estados do Juiz em português e o rótulo de falha da CVM1", function () {
    for (const [given, expected] of [["aprovado", "approved"], ["Reprovado", "rejected"], ["inconclusivo", "inconclusive"],
      ["inconclusive_failure", "failure"], ["failed", "failure"]]) {
      assert.strictEqual(normalizeOutcome(given), expected);
    }
    assert.throws(() => normalizeOutcome(undefined), /unknown outcome/);
  });

  it("cada identidade tem o próprio saldo", function () {
    const bob = registry.register({ publicKey: newPublicKeyHex(), nonce: "0" });
    registry.reserve(alice.id, "job-a");
    registry.settle("job-a", "rejected");
    assert.strictEqual(registry.summary(bob.id).balance, 20);
    assert.strictEqual(registry.summary(alice.id).balance, 15);
    // a reserva de uma não é acertada pela outra: o dono vem da reserva
    registry.reserve(bob.id, "job-b");
    assert.strictEqual(registry.settle("job-b", "approved").identityId, bob.id);
    assert.strictEqual(registry.summary(alice.id).balance, 15);
  });

  it("o livro persiste: reserva aberta, saldo e acerto repetido sobrevivem a um reinício", function () {
    registry.reserve(alice.id, "job-1");
    registry.reserve(alice.id, "job-2");
    registry.settle("job-1", "rejected");
    const reloaded = new IdentityRegistry({ statePath, difficulty: 0 });
    const s = reloaded.summary(alice.id);
    assert.deepStrictEqual([s.balance, s.reserved, s.spent, s.counts.rejected], [10, 5, 5, 1]);
    assert.strictEqual(reloaded.settle("job-1", "approved").repeated, true);
    assert.strictEqual(reloaded.settle("job-2", "approved").charged, 1);
    assert.strictEqual(reloaded.summary(alice.id).balance, 14);
  });

  it("registro anterior à T-1704 (só saldo) é completado na leitura, sem perder o saldo", function () {
    const legacyId = identityId(newPublicKeyHex());
    const state = JSON.parse(fs.readFileSync(statePath, "utf8"));
    state.identities[legacyId] = {
      id: legacyId, publicKey: "ab".repeat(32), nonce: "0", difficulty: 0, registeredAtUtc: "2026-11-01T00:00:00.000Z", balance: 12,
    };
    delete state.ledger;
    fs.writeFileSync(statePath, JSON.stringify(state));
    const reloaded = new IdentityRegistry({ statePath, difficulty: 0 });
    const s = reloaded.summary(legacyId);
    assert.deepStrictEqual([s.balance, s.reserved, s.spent, s.initialBalance], [12, 0, 0, 20]);
    assert.deepStrictEqual(s.counts, { approved: 0, inconclusive: 0, rejected: 0, failure: 0 });
    reloaded.reserve(legacyId, "j");
    assert.strictEqual(reloaded.settle("j", "approved").balance, 11);
  });
});

describe("api-server: consulta de saldo e contagens (T-1704)", function () {
  this.timeout(60_000);

  const challenge = crypto.randomBytes(32).toString("hex");
  const key = newPublicKeyHex();
  let server;
  let base;

  before(async function () {
    const port = await new Promise((resolve) => {
      const s = net.createServer().listen(0, "127.0.0.1", () => {
        const p = s.address().port;
        s.close(() => resolve(p));
      });
    });
    const env = {
      ...process.env,
      WEB_PORT: String(port),
      DNAT_IDENTITIES_PATH: tempStatePath(),
      DNAT_IDENTITY_CHALLENGE: challenge,
      DNAT_IDENTITY_DIFFICULTY: "0",
    };
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

  it("GET /api/identity/:id de identidade desconhecida recebe 404", async function () {
    const res = await fetch(`${base}/api/identity/${"00".repeat(32)}`);
    assert.strictEqual(res.status, 404);
  });

  it("GET /api/identity/:id mostra saldo, reservado, gasto e contagens, sem assinatura (leitura aberta)", async function () {
    const reg = await fetch(`${base}/api/identity/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ publicKey: key, nonce: "0" }),
    });
    assert.strictEqual(reg.status, 201);
    const id = identityId(key);
    const res = await fetch(`${base}/api/identity/${id}`);
    assert.strictEqual(res.status, 200);
    const body = await res.json();
    assert.deepStrictEqual(
      [body.id, body.balance, body.reserved, body.spent, body.initialBalance],
      [id, 20, 0, 0, 20],
    );
    assert.deepStrictEqual(body.counts, { approved: 0, inconclusive: 0, rejected: 0, failure: 0 });
    assert.strictEqual("nonce" in body, false);
  });

  it("/api/identity/challenge e /register continuam nas rotas fixas, antes de /:id", async function () {
    const res = await fetch(`${base}/api/identity/challenge`);
    assert.strictEqual(res.status, 200);
    assert.strictEqual((await res.json()).challenge, challenge);
  });
});
