/* web/dnat-identity.js (T-1703, T-1705 na web UI): identidade criada no "navegador" e pedidos assinados.
 *
 * O arquivo da web roda num contexto vm com o WebCrypto do Node (Ed25519 incluso) e shims de
 * window, localStorage, Blob e Worker (o worker roda no mesmo processo). O servidor é o api-server
 * de verdade: ele confere a prova de trabalho no registro e a assinatura nas rotas que criam trabalho.
 */
const assert = require("node:assert");
const fs = require("node:fs");
const net = require("node:net");
const os = require("node:os");
const path = require("node:path");
const vm = require("node:vm");
const { spawn } = require("node:child_process");
const { generateIdentity } = require("../scripts/identity_client");

const SOURCE = fs.readFileSync(path.join(__dirname, "..", "web", "dnat-identity.js"), "utf8");

function browser(base, fetchImpl = (p, o) => fetch(`${base}${p}`, o)) {
  const store = new Map();
  const blobs = new Map();
  class FakeBlob {
    constructor(parts) {
      this.text = parts.join("");
    }
  }
  class FakeWorker {
    constructor(url) {
      const src = blobs.get(url);
      const ctx = { postMessage: (data) => setImmediate(() => this.onmessage?.({ data })), BigInt, Math, Date, Uint32Array };
      vm.createContext(ctx);
      vm.runInContext(src, ctx);
      this.ctx = ctx;
    }
    postMessage(data) {
      setImmediate(() => this.ctx.onmessage({ data }));
    }
    terminate() {}
  }
  const win = {};
  const ctx = {
    window: win,
    crypto: globalThis.crypto,
    TextEncoder,
    Blob: FakeBlob,
    Worker: FakeWorker,
    URL: { createObjectURL: (b) => { const u = `blob:${blobs.size}`; blobs.set(u, b.text); return u; }, revokeObjectURL() {} },
    localStorage: { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, String(v)), removeItem: (k) => store.delete(k) },
    fetch: fetchImpl,
    JSON,
    Array,
    Object,
    Uint8Array,
    String,
    Error,
    Date,
    Promise,
    parseInt,
  };
  vm.createContext(ctx);
  vm.runInContext(SOURCE, ctx);
  return { lib: win.DnatIdentity, store };
}

describe("web/dnat-identity.js: identidade e pedidos assinados no navegador", function () {
  this.timeout(120000);
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
      DNAT_IDENTITIES_PATH: path.join(fs.mkdtempSync(path.join(os.tmpdir(), "dnat-web-")), "identities.json"),
      DNAT_IDENTITY_DIFFICULTY: "12",
    };
    delete env.CONTRACT_ADDRESS;
    server = spawn(process.execPath, [path.join(__dirname, "..", "scripts", "api-server.js")], { cwd: path.join(__dirname, ".."), env, stdio: ["ignore", "pipe", "pipe"] });
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

  it("cria a identidade com prova de trabalho aceita pelo servidor e a guarda no formato do CLI", async function () {
    const { lib, store } = browser(base);
    const progress = [];
    const out = await lib.create((p) => progress.push(p));
    assert.strictEqual(out.difficulty, 12);
    const saved = JSON.parse(store.get("dnat-identity"));
    assert.deepStrictEqual(Object.keys(saved).sort(), ["id", "publicKey", "registeredAtUtc", "seed", "version"]);
    const res = await fetch(`${base}/api/identity/${saved.id}`);
    assert.strictEqual(res.status, 200);
    assert.strictEqual((await res.json()).balance, 20);
  });

  it("pedido JSON e multipart assinados passam da autenticação; assinatura adulterada e sem identidade não", async function () {
    const { lib } = browser(base);
    await lib.create();
    const json = await lib.signedFetch("/api/run-from-cids", { body: JSON.stringify({}), contentType: "application/json" });
    assert.notStrictEqual(json.status, 401, await json.text()); // passa; falha depois por falta de campos
    const file = { name: "dataset.csv", type: "text/csv", arrayBuffer: async () => new TextEncoder().encode("prompt,response\nhi,ok\n").buffer };
    const mp = await lib.buildMultipart({ "manifest.name": "d" }, { file });
    const up = await lib.signedFetch("/api/register-dataset", { body: mp.body, contentType: mp.contentType });
    assert.notStrictEqual(up.status, 401, await up.text());

    // mesma assinatura com o corpo trocado no caminho: 401
    const saved = lib.load();
    const tampered = browser(base, async (p, o) => fetch(`${base}${p}`, { ...o, body: new TextEncoder().encode('{"datasetId":"1"}') }));
    tampered.store.set("dnat-identity", JSON.stringify(saved));
    const bad = await tampered.lib.signedFetch("/api/run-from-cids", { body: JSON.stringify({}), contentType: "application/json" });
    assert.strictEqual(bad.status, 401);

    const anon = browser(base);
    await assert.rejects(() => anon.lib.signedFetch("/api/run-from-cids", { body: "{}" }), /sem identidade/);
  });

  it("importa o arquivo de chave do CLI e recusa um arquivo adulterado", async function () {
    const { lib } = browser(base);
    const cli = generateIdentity();
    const ok = await lib.importJson(JSON.stringify({ version: 1, ...cli }));
    assert.strictEqual(ok.id, cli.id);
    const other = generateIdentity();
    await assert.rejects(() => lib.importJson(JSON.stringify({ version: 1, ...cli, seed: other.seed })), /semente não é desta chave/);
    await assert.rejects(() => lib.importJson(JSON.stringify({ version: 1, ...cli, id: other.id })), /id não bate/);
  });
});
