/* Teste 9 (T-1707): cada regra da identidade e da cota (D7) verificada por HTTP num Express só com
 * as rotas de identidade e o job de demonstração (e2e/demo_cota.js), sem cadeia nem executor.
 */
const assert = require("node:assert");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { identityOnlyApp, listen } = require("../e2e/demo_cota");
const { signRequest, solveProof, verifyProof } = require("../scripts/identity");
const client = require("../scripts/identity_client");

describe("Teste 9: identidade e cota pela API, sem cadeia nem executor (T-1707)", function () {
  this.timeout(60000);
  let server;
  let url;
  let registry;
  let statePath;

  before(async function () {
    statePath = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "dnat-t9-")), "identities.json");
    const made = identityOnlyApp({ statePath, difficulty: 12 });
    registry = made.registry;
    ({ server, url } = await listen(made.app));
  });
  after(() => server?.close());

  const job = (identity, verdict, extra = {}) =>
    client.signedRequest({ apiUrl: url, identity, path: "/api/demo/job", json: { verdict }, ...extra })
      .then((r) => ({ status: 200, ...r }), (e) => ({ status: e.status, error: e.body?.error }));
  const register = (body) => fetch(`${url}/api/identity/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  it("prova válida registra; inválida e chave repetida não", async function () {
    const identity = client.generateIdentity();
    const { challenge } = await (await fetch(`${url}/api/identity/challenge`)).json();
    const nonce = solveProof(Buffer.from(challenge, "hex"), Buffer.from(identity.publicKey, "hex"), 12);
    let bad = nonce + 1n;
    while (verifyProof(Buffer.from(challenge, "hex"), Buffer.from(identity.publicKey, "hex"), bad, 12)) bad += 1n;
    assert.strictEqual((await register({ publicKey: identity.publicKey, nonce: bad.toString() })).status, 400);
    const ok = await register({ publicKey: identity.publicKey, nonce: nonce.toString() });
    assert.strictEqual(ok.status, 201);
    assert.strictEqual((await ok.json()).balance, 20);
    assert.strictEqual((await register({ publicKey: identity.publicKey, nonce: nonce.toString() })).status, 409);
  });

  it("assinatura certa passa; errada, de outra chave, carimbo velho e repetição recebem 401", async function () {
    const identity = client.generateIdentity();
    await client.registerIdentity({ apiUrl: url, identity });
    assert.strictEqual((await job(identity, "approved")).status, 200);

    const body = JSON.stringify({ verdict: "approved" });
    const send = (headers) => fetch(`${url}/api/demo/job`, { method: "POST", headers: { "Content-Type": "application/json", ...headers }, body });
    const sign = (o = {}) => signRequest({ privateKey: identity.seed, publicKey: identity.publicKey, method: "POST", path: "/api/demo/job", body: Buffer.from(body), ...o });

    const other = client.generateIdentity();
    const foreign = { ...sign(), "X-Signature": signRequest({ privateKey: other.seed, publicKey: other.publicKey, method: "POST", path: "/api/demo/job", body: Buffer.from(body) })["X-Signature"] };
    assert.strictEqual((await send(foreign)).status, 401);
    const tampered = sign();
    tampered["X-Signature"] = (tampered["X-Signature"][0] === "0" ? "1" : "0") + tampered["X-Signature"].slice(1);
    assert.strictEqual((await send(tampered)).status, 401);
    assert.strictEqual((await send(sign({ timestamp: Date.now() - 6 * 60 * 1000 }))).status, 401);
    const once = sign();
    assert.strictEqual((await send(once)).status, 200);
    assert.strictEqual((await send(once)).status, 401); // o mesmo pedido de novo
  });

  it("reserva, acerto por desfecho (1, 2, 5) e falha que devolve tudo", async function () {
    const identity = client.generateIdentity();
    await client.registerIdentity({ apiUrl: url, identity });
    const seq = [["approved", 1, 19], ["inconclusive", 2, 17], ["rejected", 5, 12], ["failure", 0, 12]];
    for (const [verdict, charged, balance] of seq) {
      const r = await job(identity, verdict);
      assert.deepStrictEqual([r.status, r.charged, r.balance], [200, charged, balance], verdict);
    }
    const s = await (await fetch(`${url}/api/identity/${identity.id}`)).json();
    assert.deepStrictEqual(s.counts, { approved: 1, inconclusive: 1, rejected: 1, failure: 1 });
    assert.strictEqual(s.reserved, 0);
    assert.strictEqual(s.spent, 8);
  });

  it("4 reprovados esgotam Q = 20 e o 5º job é recusado com 402, sem mudar o saldo", async function () {
    const identity = client.generateIdentity();
    await client.registerIdentity({ apiUrl: url, identity });
    for (let i = 0; i < 4; i++) assert.strictEqual((await job(identity, "rejected")).status, 200);
    const fifth = await job(identity, "rejected");
    assert.strictEqual(fifth.status, 402);
    assert.match(fifth.error, /insufficient quota/);
    const s = await (await fetch(`${url}/api/identity/${identity.id}`)).json();
    assert.deepStrictEqual([s.balance, s.reserved, s.counts.rejected], [0, 0, 4]);
    // o estado persiste no arquivo da CVM1
    const disk = JSON.parse(fs.readFileSync(statePath, "utf8"));
    assert.ok(Object.values(disk.ledger).some((e) => e.identityId === identity.id && e.outcome === "rejected"));
  });

  it("identidade desconhecida: 404 na consulta e 401 no job", async function () {
    assert.strictEqual((await fetch(`${url}/api/identity/${crypto.randomBytes(32).toString("hex")}`)).status, 404);
    assert.strictEqual((await job(client.generateIdentity(), "approved")).status, 401);
  });
});
