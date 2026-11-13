/* T-1703: pedidos assinados pela identidade nas rotas que criam trabalho (E14 §18.2). */
const assert = require("node:assert");
const crypto = require("node:crypto");
const fs = require("node:fs");
const net = require("node:net");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");
const {
  MAX_CLOCK_SKEW_MS,
  IdentityRegistry,
  RequestVerifier,
  identityId,
  recordExecutionIdentity,
  requestMessage,
  signRequest,
  solveProof,
} = require("../scripts/identity");

function newIdentity() {
  const { publicKey, privateKey } = crypto.generateKeyPairSync("ed25519");
  const pub = Buffer.from(publicKey.export({ format: "jwk" }).x, "base64url").toString("hex");
  const seed = Buffer.from(privateKey.export({ format: "jwk" }).d, "base64url").toString("hex");
  return { publicKey: pub, privateKey, seed, id: identityId(pub) };
}

function tempDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "dnat-signed-"));
}

/** Cabeçalhos do Node vêm em minúsculas; o verificador lê assim. */
function lower(headers) {
  return Object.fromEntries(Object.entries(headers).map(([k, v]) => [k.toLowerCase(), v]));
}

describe("identity.js: pedidos assinados (T-1703)", function () {
  const NOW = 1_800_000_000_000;
  let registry;
  let verifier;
  let alice;
  const body = Buffer.from(JSON.stringify({ datasetId: "1", applicationId: "2" }));
  const req = { method: "POST", path: "/api/run-from-cids" };

  // d = 0: qualquer nonce vale; aqui só interessa ter identidades registradas.
  beforeEach(function () {
    registry = new IdentityRegistry({ statePath: path.join(tempDir(), "identities.json"), difficulty: 0 });
    alice = newIdentity();
    registry.register({ publicKey: alice.publicKey, nonce: "0" });
    verifier = new RequestVerifier({ registry, now: () => NOW });
  });

  const signed = (who, over = {}) => {
    const r = { ...req, body, timestamp: NOW, ...over };
    return lower(signRequest({ privateKey: who.privateKey, publicKey: who.publicKey, ...r }));
  };
  const rejects = (call, re) =>
    assert.throws(call, (e) => {
      assert.strictEqual(e.status, 401);
      assert.match(e.message, re);
      return true;
    });

  it("mensagem assinada: rótulo, método, caminho, carimbo e SHA-256 do corpo, separados por \\n", function () {
    const msg = requestMessage({ method: "post", path: "/api/x?y=1", timestamp: 42, body: Buffer.from("abc") });
    const sha = crypto.createHash("sha256").update("abc").digest("hex");
    assert.strictEqual(msg.toString("utf8"), `DNAT-REQUEST-v1\nPOST\n/api/x?y=1\n42\n${sha}`);
    const empty = crypto.createHash("sha256").update(Buffer.alloc(0)).digest("hex");
    assert.ok(requestMessage({ method: "GET", path: "/", timestamp: 1 }).toString().endsWith(empty));
  });

  it("pedido assinado certo passa e devolve a identidade; a semente em hex assina igual ao KeyObject", function () {
    const rec = verifier.verify({ ...req, body, headers: signed(alice) });
    assert.strictEqual(rec.id, alice.id);
    const bySeed = lower(signRequest({ privateKey: alice.seed, publicKey: alice.publicKey, ...req, body, timestamp: NOW + 1 }));
    assert.strictEqual(verifier.verify({ ...req, body, headers: bySeed }).id, alice.id);
  });

  it("sem assinatura, ou com cabeçalho faltando ou malformado: 401", function () {
    rejects(() => verifier.verify({ ...req, body, headers: {} }), /signed request required/);
    for (const h of ["x-identity", "x-timestamp", "x-signature"]) {
      const headers = signed(alice);
      delete headers[h];
      rejects(() => verifier.verify({ ...req, body, headers }), /signed request required/);
    }
    rejects(() => verifier.verify({ ...req, body, headers: { ...signed(alice), "x-signature": "zz" } }), /X-Signature/);
    rejects(() => verifier.verify({ ...req, body, headers: { ...signed(alice), "x-timestamp": "-5" } }), /X-Timestamp/);
    rejects(() => verifier.verify({ ...req, body, headers: { ...signed(alice), "x-identity": "abc" } }), /X-Identity/);
  });

  it("assinatura inválida: outra chave, corpo, caminho, método ou carimbo trocados: 401", function () {
    const mallory = newIdentity();
    // Mallory assina com a própria chave e se apresenta como Alice.
    const forged = { ...signed(mallory), "x-identity": alice.id };
    rejects(() => verifier.verify({ ...req, body, headers: forged }), /invalid request signature/);

    const headers = signed(alice);
    rejects(() => verifier.verify({ ...req, body: Buffer.from("{}"), headers }), /invalid request signature/);
    rejects(() => verifier.verify({ ...req, path: "/api/register-dataset", body, headers }), /invalid request signature/);
    rejects(() => verifier.verify({ ...req, method: "PUT", body, headers }), /invalid request signature/);
    rejects(
      () => verifier.verify({ ...req, body, headers: { ...headers, "x-timestamp": String(NOW + 1) } }),
      /invalid request signature/,
    );
    const flipped = Buffer.from(headers["x-signature"], "hex");
    flipped[0] ^= 1;
    rejects(
      () => verifier.verify({ ...req, body, headers: { ...headers, "x-signature": flipped.toString("hex") } }),
      /invalid request signature/,
    );
  });

  it("identidade desconhecida, mesmo com assinatura certa da própria chave: 401", function () {
    const stranger = newIdentity();
    rejects(() => verifier.verify({ ...req, body, headers: signed(stranger) }), /unknown identity/);
  });

  it("carimbo fora de ±5 min: 401; na borda da janela passa", function () {
    rejects(
      () => verifier.verify({ ...req, body, headers: signed(alice, { timestamp: NOW - MAX_CLOCK_SKEW_MS - 1 }) }),
      /outside the allowed window/,
    );
    rejects(
      () => verifier.verify({ ...req, body, headers: signed(alice, { timestamp: NOW + MAX_CLOCK_SKEW_MS + 1 }) }),
      /outside the allowed window/,
    );
    verifier.verify({ ...req, body, headers: signed(alice, { timestamp: NOW - MAX_CLOCK_SKEW_MS }) });
    verifier.verify({ ...req, body, headers: signed(alice, { timestamp: NOW + MAX_CLOCK_SKEW_MS }) });
  });

  it("repetição: o mesmo pedido assinado não passa duas vezes; outro carimbo ou outra identidade passa", function () {
    const headers = signed(alice);
    verifier.verify({ ...req, body, headers });
    rejects(() => verifier.verify({ ...req, body, headers }), /replayed request/);
    verifier.verify({ ...req, body, headers: signed(alice, { timestamp: NOW + 1 }) });

    const bob = newIdentity();
    registry.register({ publicKey: bob.publicKey, nonce: "0" });
    verifier.verify({ ...req, body, headers: signed(bob) });
  });

  it("repetição depois da janela: o registro em memória esvazia e o relógio recusa o carimbo velho", function () {
    let now = NOW;
    const v = new RequestVerifier({ registry, now: () => now });
    const headers = signed(alice);
    v.verify({ ...req, body, headers });
    now = NOW + MAX_CLOCK_SKEW_MS + 1;
    v.verify({ ...req, body, headers: signed(alice, { timestamp: now }) }); // dispara a limpeza
    assert.strictEqual(v.seen.size, 1);
    rejects(() => v.verify({ ...req, body, headers }), /outside the allowed window/);
  });

  it("recordExecutionIdentity grava o id no metadata.json sem apagar o resto", function () {
    const metadataPath = path.join(tempDir(), "metadata.json");
    assert.strictEqual(recordExecutionIdentity(metadataPath, alice.id), false);
    fs.writeFileSync(metadataPath, JSON.stringify({ status: "completed", returnCode: 0 }));
    assert.strictEqual(recordExecutionIdentity(metadataPath, alice.id), true);
    assert.deepStrictEqual(JSON.parse(fs.readFileSync(metadataPath, "utf8")), {
      status: "completed",
      returnCode: 0,
      identityId: alice.id,
    });
  });
});

describe("api-server: rotas que criam trabalho exigem pedido assinado (T-1703)", function () {
  this.timeout(120_000);

  const challenge = crypto.randomBytes(32).toString("hex");
  const DIFFICULTY = 8;
  const alice = newIdentity();
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
      DNAT_IDENTITIES_PATH: path.join(tempDir(), "identities.json"),
      DNAT_IDENTITY_CHALLENGE: challenge,
      DNAT_IDENTITY_DIFFICULTY: String(DIFFICULTY),
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

    const nonce = solveProof(Buffer.from(challenge, "hex"), Buffer.from(alice.publicKey, "hex"), DIFFICULTY);
    const res = await fetch(`${base}/api/identity/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ publicKey: alice.publicKey, nonce: nonce.toString() }),
    });
    assert.strictEqual(res.status, 201);
  });

  after(function () {
    server?.kill();
  });

  const ROUTES = ["/api/register-dataset", "/api/register-application", "/api/run-from-cids"];
  const jsonBody = JSON.stringify({});

  function send(route, { who = alice, body = jsonBody, signedBody = body, timestamp, headers = {}, sign = true } = {}) {
    const auth = sign
      ? signRequest({ privateKey: who.privateKey, publicKey: who.publicKey, method: "POST", path: route, body: signedBody, timestamp })
      : {};
    return fetch(`${base}${route}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...auth, ...headers },
      body,
    });
  }

  it("sem assinatura: 401 nas três rotas", async function () {
    for (const route of ROUTES) {
      const res = await send(route, { sign: false });
      assert.strictEqual(res.status, 401, route);
      assert.match((await res.json()).error, /signed request required/);
    }
  });

  it("assinatura inválida (outra chave, corpo trocado): 401 nas três rotas", async function () {
    const mallory = newIdentity();
    for (const route of ROUTES) {
      const forged = await send(route, { who: mallory, headers: { "X-Identity": alice.id } });
      assert.strictEqual(forged.status, 401, route);
      const tampered = await send(route, { signedBody: JSON.stringify({ other: 1 }) });
      assert.strictEqual(tampered.status, 401, route);
      assert.match((await tampered.json()).error, /invalid request signature/);
    }
  });

  it("identidade desconhecida e carimbo velho: 401", async function () {
    const res = await send("/api/run-from-cids", { who: newIdentity() });
    assert.strictEqual(res.status, 401);
    assert.match((await res.json()).error, /unknown identity/);
    const old = await send("/api/run-from-cids", { timestamp: Date.now() - MAX_CLOCK_SKEW_MS - 60_000 });
    assert.strictEqual(old.status, 401);
    assert.match((await old.json()).error, /outside the allowed window/);
  });

  it("pedido assinado certo passa da autenticação (JSON e multipart); repetido recebe 401", async function () {
    // Corpo vazio: a rota falha depois, por falta de campos (400), sem tocar a cadeia nem o IPFS.
    const ts = Date.now();
    const first = await send("/api/run-from-cids", { timestamp: ts });
    assert.strictEqual(first.status, 400);
    assert.match((await first.json()).error, /datasetId and applicationId are required/);

    const replay = await send("/api/run-from-cids", { timestamp: ts });
    assert.strictEqual(replay.status, 401);
    assert.match((await replay.json()).error, /replayed request/);

    // Multipart: a assinatura cobre os bytes crus do corpo.
    const boundary = "dnat-test-boundary";
    const multipart = Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="title"\r\n\r\nx\r\n--${boundary}--\r\n`);
    for (const route of ["/api/register-dataset", "/api/register-application"]) {
      const auth = signRequest({ privateKey: alice.privateKey, publicKey: alice.publicKey, method: "POST", path: route, body: multipart });
      const res = await fetch(`${base}${route}`, {
        method: "POST",
        headers: { "Content-Type": `multipart/form-data; boundary=${boundary}`, ...auth },
        body: multipart,
      });
      assert.strictEqual(res.status, 400, route);
      assert.match((await res.json()).error, /filePath or uploaded file is required/);
    }
  });

  it("leitura e rotas do operador seguem sem assinatura", async function () {
    const res = await fetch(`${base}/api/identity/challenge`);
    assert.strictEqual(res.status, 200);
    const execs = await fetch(`${base}/api/executions`);
    assert.strictEqual(execs.status, 200);
  });
});
