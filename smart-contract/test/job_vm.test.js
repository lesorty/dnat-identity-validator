/* CVM de job de uso único (T-801): pool, agente que recusa o segundo job e, com Docker, dois jobs
 * seguidos em containers diferentes, destruídos depois.
 */
const assert = require("node:assert");
const fs = require("node:fs");
const http = require("node:http");
const net = require("node:net");
const path = require("node:path");
const { spawn } = require("node:child_process");
const { DockerProvider, JobVmPool, dockerRequest, parseBytes, providerFromEnv } = require("../scripts/job_vm");

const REPO = path.resolve(__dirname, "..", "..");

function fakeAgent() {
  return new Promise((resolve) => {
    const s = http.createServer((req, res) => {
      res.setHeader("Content-Type", "application/json");
      if (req.url === "/stats") res.end(JSON.stringify({ peakRssBytes: 1234, jobsAccepted: 1 }));
      else res.end(JSON.stringify({ ok: true, used: false }));
    });
    s.listen(0, "127.0.0.1", () => resolve(s));
  });
}

class FakeProvider {
  constructor({ duplicate = false } = {}) {
    this.name = "fake";
    this.singleUse = true;
    this.n = 0;
    this.live = new Map();
    this.destroyed = [];
    this.duplicate = duplicate;
  }

  async create() {
    const s = await fakeAgent();
    const id = this.duplicate ? "vm-1" : `vm-${++this.n}`;
    this.live.set(id, s);
    return { id, url: `http://127.0.0.1:${s.address().port}` };
  }

  async destroy(vm) {
    this.live.get(vm.id)?.close();
    this.live.delete(vm.id);
    this.destroyed.push(vm.id);
  }
}

async function freePort() {
  return new Promise((resolve) => {
    const s = net.createServer().listen(0, "127.0.0.1", () => {
      const p = s.address().port;
      s.close(() => resolve(p));
    });
  });
}

async function post(url, body) {
  const res = await fetch(url, { method: "POST", body, headers: { "Content-Type": "application/gzip" } });
  return { status: res.status, json: await res.json() };
}

describe("CVM de job de uso único (T-801)", function () {
  this.timeout(120000);

  describe("pool", function () {
    it("dois jobs seguidos recebem CVMs diferentes, cada uma destruída depois, com a memória de pico", async function () {
      const provider = new FakeProvider();
      const pool = new JobVmPool({ provider });
      const a = await pool.take();
      const ra = await pool.finish(a);
      const b = await pool.take();
      const rb = await pool.finish(b);
      assert.notStrictEqual(a.id, b.id);
      assert.deepStrictEqual(provider.destroyed, [a.id, b.id]);
      assert.strictEqual(provider.live.size, 0);
      for (const r of [ra, rb]) {
        assert.strictEqual(r.singleUse, true);
        assert.strictEqual(r.peakRssBytes, 1234);
        assert.ok(r.destroyedAt);
      }
      await pool.close();
    });

    it("o warm pool entrega CVMs já prontas e se repõe; ao fechar, destrói as não usadas", async function () {
      const provider = new FakeProvider();
      const pool = new JobVmPool({ provider, size: 2 });
      await pool.refill();
      assert.strictEqual(pool.ready.length, 2);
      const a = await pool.take();
      assert.strictEqual(a.fromPool, true);
      await pool.refill();
      assert.strictEqual(pool.ready.length, 2);
      await pool.finish(a);
      await pool.close();
      assert.strictEqual(provider.live.size, 0);
      assert.strictEqual(provider.destroyed.length, 3);
    });

    it("recusa entregar a mesma CVM a dois jobs", async function () {
      const pool = new JobVmPool({ provider: new FakeProvider({ duplicate: true }) });
      const a = await pool.take();
      await assert.rejects(() => pool.take(), /already handed/);
      await pool.finish(a);
      await pool.close();
    });

    it("static é reaproveitado e diz isso; provedor desconhecido falha", function () {
      const p = providerFromEnv({ DNAT_JOB_VM_PROVIDER: "static", EXECUTOR_URL: "http://x:5000/execute" });
      assert.strictEqual(p.singleUse, false);
      assert.strictEqual(p.url, "http://x:5000");
      assert.throws(() => providerFromEnv({ DNAT_JOB_VM_PROVIDER: "nope" }), /unknown/);
      assert.throws(() => providerFromEnv({ DNAT_JOB_VM_PROVIDER: "command" }), /CREATE_CMD/);
      assert.strictEqual(parseBytes("4g"), 4 * 1024 ** 3);
      assert.strictEqual(parseBytes("512mb"), 512 * 1024 ** 2);
    });
  });

  describe("agente com DNAT_SINGLE_USE=1", function () {
    let agent;
    let url;
    before(async function () {
      const port = await freePort();
      agent = spawn("python3", [path.join(REPO, "vm_runtime", "executor.py"), String(port)], {
        cwd: path.join(REPO, "vm_runtime"),
        env: { ...process.env, DNAT_NO_MICROVM: "1", DNAT_SINGLE_USE: "1", DNAT_DERIVATIVE_OUTBOX: fs.mkdtempSync("/tmp/dnat-outbox-") },
        stdio: "ignore",
      });
      url = `http://127.0.0.1:${port}`;
      for (let i = 0; i < 100; i++) {
        try {
          await fetch(`${url}/health`);
          return;
        } catch {
          await new Promise((r) => setTimeout(r, 100));
        }
      }
      throw new Error("agent did not start");
    });
    after(() => agent?.kill());

    it("aceita um job e recusa o segundo com \"used\"; /stats e /health mostram o estado", async function () {
      const h0 = await (await fetch(`${url}/health`)).json();
      assert.strictEqual(h0.singleUse, true);
      assert.strictEqual(h0.used, false);
      const first = await post(`${url}/execute`, Buffer.from("not a bundle"));
      assert.strictEqual(first.status, 200);
      assert.strictEqual(first.json.status, "agent_error"); // bundle inválido, mas o job foi aceito
      const second = await post(`${url}/execute`, Buffer.from("not a bundle"));
      assert.strictEqual(second.status, 503);
      assert.strictEqual(second.json.error, "used");
      const h1 = await (await fetch(`${url}/health`)).json();
      assert.strictEqual(h1.used, true);
      const stats = await (await fetch(`${url}/stats`)).json();
      assert.strictEqual(stats.jobsAccepted, 1);
      assert.ok(stats.peakRssBytes > 0);
    });
  });

  describe("Docker (pilha local, T-815)", function () {
    const socketPath = "/var/run/docker.sock";
    let provider;
    before(async function () {
      if (!fs.existsSync(socketPath)) return this.skip();
      provider = new DockerProvider({ socketPath, image: "dnat-executor-direct:latest", network: "dnat-runtime", memory: "2g" });
      try {
        await dockerRequest(socketPath, "GET", "/images/dnat-executor-direct:latest/json");
        await dockerRequest(socketPath, "GET", "/networks/dnat-runtime");
      } catch {
        return this.skip(); // sem a imagem ou a rede da pilha direta
      }
    });

    it("dois jobs seguidos caem em containers diferentes, que somem depois", async function () {
      const created = [];
      const create = provider.create.bind(provider);
      provider.create = async () => {
        const vm = await create();
        created.push(vm.id);
        return vm;
      };
      const pool = new JobVmPool({ provider, size: 1 });
      await pool.refill();
      const a = await pool.take();
      const b = await pool.take(); // a segunda já vem do pool reposto ou é criada na hora
      assert.notStrictEqual(a.id, b.id);
      assert.notStrictEqual(a.url, b.url);
      const first = await post(`${a.url}/execute`, Buffer.from("x"));
      assert.strictEqual(first.json.status, "agent_error");
      const again = await post(`${a.url}/execute`, Buffer.from("x"));
      assert.strictEqual(again.json.error, "used");
      const ra = await pool.finish(a);
      await pool.finish(b);
      await pool.close();
      assert.strictEqual(await provider.exists(a.id), false);
      assert.strictEqual(await provider.exists(b.id), false);
      assert.ok(ra.cgroupPeakBytes > 0 || ra.peakRssBytes > 0, JSON.stringify(ra));
      // nenhum container criado por este pool (os dois do job e o de reposição) sobrou
      assert.ok(created.length >= 2);
      for (const id of created) assert.strictEqual(await provider.exists(id), false, id);
    });
  });
});
