/* T-1705: cliente de identidade no CLI (gera, minera, registra, assina) e custo da prova por d. */
const assert = require("node:assert");
const crypto = require("node:crypto");
const fs = require("node:fs");
const net = require("node:net");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");
const { identityId, requestMessage, verifyProof } = require("../scripts/identity");
const client = require("../scripts/identity_client");
const { main, parseArgs } = require("../scripts/identity_cli");

const tempDir = () => fs.mkdtempSync(path.join(os.tmpdir(), "dnat-client-"));

/** Roda um subcomando do CLI em processo e devolve { code, out, err }. */
async function cli(...argv) {
  const out = [];
  const err = [];
  const code = await main(argv, { stdout: (s) => out.push(s), stderr: (s) => err.push(s) });
  return { code, out: out.join("\n"), err: err.join("\n"), json: () => JSON.parse(out.join("\n")) };
}

describe("identity_client.js: chave, multipart e parâmetros (T-1705)", function () {
  it("generateIdentity: id é o SHA-256 da chave pública; a semente assina e a chave confere", function () {
    const k = client.generateIdentity();
    assert.strictEqual(k.id, identityId(k.publicKey));
    assert.match(k.seed, /^[0-9a-f]{64}$/);
  });

  it("o arquivo da chave tem modo 0600, não é sobrescrito sem --force e confere o id ao ler", function () {
    const file = path.join(tempDir(), "sub", "identity.json");
    const k = client.generateIdentity();
    client.saveKeyFile(file, k);
    assert.strictEqual(fs.statSync(file).mode & 0o777, 0o600);
    assert.deepStrictEqual(
      { id: client.loadKeyFile(file).id, seed: client.loadKeyFile(file).seed },
      { id: k.id, seed: k.seed },
    );
    assert.throws(() => client.saveKeyFile(file, client.generateIdentity()), /already exists/);
    client.saveKeyFile(file, client.generateIdentity(), { overwrite: true });

    const bad = JSON.parse(fs.readFileSync(file, "utf8"));
    fs.writeFileSync(file, JSON.stringify({ ...bad, id: "00".repeat(32) }));
    assert.throws(() => client.loadKeyFile(file), /id does not match/);
    assert.throws(() => client.loadKeyFile(path.join(tempDir(), "nada.json")), /key file not found/);
  });

  it("buildMultipart: campos, arquivo e fecho com o limite informado", function () {
    const { body, contentType } = client.buildMultipart(
      { name: "ds", description: "d" },
      { file: { filename: "a.csv", data: Buffer.from("x,y\n1,2\n"), type: "text/csv" } },
      "B0",
    );
    assert.strictEqual(contentType, "multipart/form-data; boundary=B0");
    const text = body.toString();
    assert.match(text, /--B0\r\nContent-Disposition: form-data; name="name"\r\n\r\nds\r\n/);
    assert.match(text, /name="file"; filename="a.csv"\r\nContent-Type: text\/csv\r\n\r\nx,y\n1,2\n\r\n/);
    assert.ok(text.endsWith("--B0--\r\n"));
  });

  it("signedRequest assina os bytes exatos do corpo enviado e o caminho com a query", async function () {
    const k = client.generateIdentity();
    let seen;
    const fetchImpl = async (url, init) => {
      seen = { url, init };
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    };
    await client.signedRequest({ apiUrl: "http://h:1/", identity: k, method: "POST", path: "/api/run-from-cids?x=1", json: { a: 1 }, fetchImpl });
    assert.strictEqual(seen.url, "http://h:1/api/run-from-cids?x=1");
    assert.strictEqual(seen.init.headers["Content-Type"], "application/json");
    assert.strictEqual(seen.init.headers["X-Identity"], k.id);
    const message = requestMessage({
      method: "POST", path: "/api/run-from-cids?x=1", timestamp: seen.init.headers["X-Timestamp"], body: seen.init.body,
    });
    const pub = crypto.createPublicKey({ key: { kty: "OKP", crv: "Ed25519", x: Buffer.from(k.publicKey, "hex").toString("base64url") }, format: "jwk" });
    assert.ok(crypto.verify(null, message, pub, Buffer.from(seen.init.headers["X-Signature"], "hex")));
  });

  it("resposta com erro vira ClientError com status e corpo", async function () {
    const k = client.generateIdentity();
    const fetchImpl = async () => new Response(JSON.stringify({ error: "nope" }), { status: 402 });
    await assert.rejects(
      client.signedRequest({ identity: k, path: "/x", json: {}, fetchImpl }),
      (e) => e.status === 402 && /402 nope/.test(e.message) && e.body.error === "nope",
    );
  });

  it("parseArgs: valores, repetidos, booleanos e posicionais; valor faltando é erro", function () {
    const r = parseArgs(["POST", "/p", "--field", "a=1", "--field", "b=2", "--force", "--api", "http://x"], {
      multi: ["field"], flags: ["force"],
    });
    assert.deepStrictEqual(r.positional, ["POST", "/p"]);
    assert.deepStrictEqual(r.opts, { field: ["a=1", "b=2"], force: true, api: "http://x" });
    assert.throws(() => parseArgs(["--api"]), /needs a value/);
    assert.throws(() => parseArgs(["--api", "--key"]), /needs a value/);
  });
});

describe("identity_client.js: custo da prova por dificuldade (T-1705)", function () {
  it("benchProof: tabela de média, mediana e esperado com solver e relógio sintéticos", function () {
    // Cada prova de dificuldade d "acha" o nonce 2^d − 1 (2^d hashes) e leva 2^d milissegundos.
    let clock = 0n;
    const solve = (_c, _k, d) => {
      clock += BigInt(2 ** d) * 1_000_000n;
      return BigInt(2 ** d - 1);
    };
    const now = () => clock;
    // O relógio só anda dentro de solve; antes e depois dele a leitura é a mesma, então a duração é a do solve.
    const rows = [];
    const res = client.benchProof({ minBits: 3, maxBits: 5, reps: 3, solve, now, onRow: (r) => rows.push(r.difficulty) });
    assert.deepStrictEqual(rows, [3, 4, 5]);
    assert.ok(Math.abs(res.hashesPerSecond - 1000) < 1e-9); // 2^d hashes em 2^d ms, em qualquer d
    for (const r of res.rows) {
      const s = 2 ** r.difficulty / 1000;
      assert.deepStrictEqual([r.meanSeconds, r.medianSeconds, r.minSeconds, r.maxSeconds], [s, s, s, s]);
      assert.strictEqual(r.expectedHashes, 2 ** r.difficulty);
      assert.ok(Math.abs(r.expectedSeconds - s) < 1e-12);
      assert.strictEqual(r.seconds.length, 3);
    }
  });

  it("benchProof com o solver real: provas válidas, 2^d hashes esperados e o tempo esperado dobra por bit", function () {
    const res = client.benchProof({ minBits: 6, maxBits: 9, reps: 2 });
    assert.deepStrictEqual(res.rows.map((r) => r.difficulty), [6, 7, 8, 9]);
    assert.ok(res.hashesPerSecond > 1000);
    for (let i = 1; i < res.rows.length; i += 1) {
      assert.ok(Math.abs(res.rows[i].expectedSeconds / res.rows[i - 1].expectedSeconds - 2) < 1e-9);
    }
    // o laço que o bench mede é o mesmo que o servidor confere
    const key = crypto.randomBytes(32);
    const ch = crypto.randomBytes(32);
    assert.ok(verifyProof(ch, key, require("../scripts/identity").solveProof(ch, key, 9), 9));
  });

  it("benchProof recusa faixa e repetições inválidas", function () {
    assert.throws(() => client.benchProof({ minBits: 10, maxBits: 9 }), /need integers/);
    assert.throws(() => client.benchProof({ minBits: 1, maxBits: 2, reps: 0 }), /reps/);
  });

  it("identity bench grava a tabela em results/: JSON e Markdown, com a máquina e a faixa pedida", async function () {
    const base = path.join(tempDir(), "pow_cost");
    const r = await cli("identity", "bench", "--min", "4", "--max", "7", "--reps", "2", "--out", base);
    assert.strictEqual(r.code, 0, r.err);
    assert.match(r.err, /d=4: média/); // progresso no stderr
    const saved = JSON.parse(fs.readFileSync(`${base}.json`, "utf8"));
    assert.deepStrictEqual(saved.rows.map((x) => x.difficulty), [4, 5, 6, 7]);
    assert.ok(saved.machine.logicalCpus >= 1 && saved.hashesPerSecond > 0);
    const md = fs.readFileSync(`${base}.md`, "utf8");
    assert.match(md, /\| 4 \| 2 \|/);
    assert.match(md, /esperado 2\^d/);
    assert.deepStrictEqual(r.json(), { json: `${base}.json`, markdown: `${base}.md`, hashesPerSecond: saved.hashesPerSecond, rows: 4 });
  });

  it("o bench padrão cobre d de 12 a 24 com 5 repetições", function () {
    const src = fs.readFileSync(path.join(__dirname, "..", "scripts", "identity_cli.js"), "utf8");
    assert.match(src, /int\(opts\.min, "min", 12\)/);
    assert.match(src, /int\(opts\.max, "max", 24\)/);
    assert.match(src, /int\(opts\.reps, "reps", 5\)/);
  });
});

describe("cli.js: usuário novo registra e fala com a API assinando (T-1705)", function () {
  this.timeout(60_000);

  const challenge = crypto.randomBytes(32).toString("hex");
  let server;
  let api;
  let keyFile;

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
      DNAT_IDENTITY_DIFFICULTY: "10",
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
    api = `http://127.0.0.1:${port}`;
    keyFile = path.join(tempDir(), "identity.json");
  });

  after(function () {
    server?.kill();
  });

  it("identity new: gera a chave, minera para d = 10, registra e grava o arquivo com saldo Q = 20", async function () {
    const r = await cli("identity", "new", "--api", api, "--key", keyFile);
    assert.strictEqual(r.code, 0, r.err);
    const out = r.json();
    assert.deepStrictEqual([out.difficulty, out.balance, out.keyFile], [10, 20, keyFile]);
    assert.ok(out.proofSeconds >= 0);
    const saved = client.loadKeyFile(keyFile);
    assert.strictEqual(saved.id, out.id);
    assert.strictEqual(saved.apiUrl, api);
    assert.strictEqual(fs.statSync(keyFile).mode & 0o777, 0o600);
    // a prova gravada vale para o desafio da implantação
    assert.ok(verifyProof(Buffer.from(challenge, "hex"), Buffer.from(saved.publicKey, "hex"), BigInt(out.nonce), 10));
  });

  it("identity new não sobrescreve a chave existente sem --force e não registra outra identidade", async function () {
    const before = client.loadKeyFile(keyFile).id;
    const r = await cli("identity", "new", "--api", api, "--key", keyFile);
    assert.strictEqual(r.code, 1);
    assert.match(r.err, /already exists/);
    assert.strictEqual(client.loadKeyFile(keyFile).id, before);
  });

  it("identity new com a API fora do ar: erro e nenhuma chave gravada", async function () {
    const file = path.join(tempDir(), "k.json");
    const r = await cli("identity", "new", "--api", "http://127.0.0.1:9", "--key", file);
    assert.strictEqual(r.code, 1);
    assert.strictEqual(fs.existsSync(file), false);
  });

  it("identity show: saldo, reservado, gasto e contagens da identidade do arquivo", async function () {
    const r = await cli("identity", "show", "--key", keyFile);
    assert.strictEqual(r.code, 0, r.err);
    const s = r.json();
    assert.deepStrictEqual([s.id, s.balance, s.reserved, s.spent], [client.loadKeyFile(keyFile).id, 20, 0, 0]);
    assert.deepStrictEqual(s.counts, { approved: 0, inconclusive: 0, rejected: 0, failure: 0 });
  });

  it("run-from-cids assinado pelo CLI passa da autenticação (falha depois, na cadeia, não com 401)", async function () {
    const r = await cli("run-from-cids", "--dataset", "1", "--application", "2", "--key", keyFile);
    assert.strictEqual(r.code, 1);
    assert.doesNotMatch(r.err, /401|signed request required|invalid request signature|unknown identity/);
  });

  it("api: JSON assinado chega à rota e a validação do corpo responde (sem 401)", async function () {
    const r = await cli("api", "POST", "/api/run-from-cids", "--json", "{}", "--key", keyFile);
    assert.strictEqual(r.code, 1);
    assert.match(r.err, /400 datasetId and applicationId are required/);
  });

  it("api: multipart assinado nas rotas register-* chega à rota (400 por falta de arquivo, não 401)", async function () {
    for (const route of ["/api/register-dataset", "/api/register-application"]) {
      const r = await cli("api", "POST", route, "--field", "name=x", "--key", keyFile);
      assert.strictEqual(r.code, 1, route);
      assert.match(r.err, /400 filePath or uploaded file is required/, route);
    }
  });

  it("api com arquivo: o multipart montado pelo CLI é lido pelo servidor com a assinatura conferindo", async function () {
    const csv = path.join(tempDir(), "d.csv");
    fs.writeFileSync(csv, "a,b\n1,2\n");
    const r = await cli("api", "POST", "/api/register-dataset", "--field", "name=x", "--file", `file=${csv}`, "--key", keyFile);
    // Passou da assinatura e do parser; falha depois, na cadeia ou no IPFS, que não existem aqui.
    assert.strictEqual(r.code, 1);
    assert.doesNotMatch(r.err, /401|invalid request signature|signed request required/);
    assert.doesNotMatch(r.err, /filePath or uploaded file is required/);
  });

  it("identidade não registrada, ou chave de outra identidade: 401", async function () {
    const stranger = path.join(tempDir(), "stranger.json");
    client.saveKeyFile(stranger, client.generateIdentity());
    const r = await cli("api", "POST", "/api/run-from-cids", "--json", "{}", "--key", stranger, "--api", api);
    assert.strictEqual(r.code, 1);
    assert.match(r.err, /401 unknown identity/);
  });

  it("sem arquivo de chave e comando desconhecido: erro claro, código 1", async function () {
    let r = await cli("run-from-cids", "--dataset", "1", "--application", "2", "--key", path.join(tempDir(), "nao.json"));
    assert.strictEqual(r.code, 1);
    assert.match(r.err, /key file not found/);
    r = await cli("run-from-cids", "--dataset", "1");
    assert.match(r.err, /usage: run-from-cids/);
    r = await cli("identity", "x");
    assert.match(r.err, /usage: identity/);
  });
});
