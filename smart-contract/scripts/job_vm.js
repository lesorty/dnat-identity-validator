/**
 * CVM de job de uso único (T-801): a CVM1 tira uma CVM nunca usada por job, entrega o job pelo
 * agente, lê a memória de pico e destrói a CVM. Nenhuma CVM recebe dois jobs.
 *
 * Provedores (DNAT_JOB_VM_PROVIDER):
 *   static   EXECUTOR_URL fixo, reaproveitado entre jobs. Só para desenvolvimento e para os roteiros
 *            antigos; o registro do job diz singleUse: false.
 *   docker   um container novo por job, da imagem do executor (vm_runtime/Dockerfile.direct), pela API
 *            do Docker no socket (DOCKER_HOST unix://… ou /var/run/docker.sock). É a pilha local
 *            (T-815): rede entra-só e agente sem privilégio, como a CVM na nuvem.
 *   command  comandos do operador para a nuvem. DNAT_JOB_VM_CREATE_CMD imprime na última linha
 *            {"id": "...", "url": "http://IP:5000"}; DNAT_JOB_VM_DESTROY_CMD recebe o id em
 *            DNAT_JOB_VM_ID. A CVM criada sobe o agente com DNAT_SINGLE_USE=1.
 *
 * Warm pool (DNAT_JOB_VM_POOL, padrão 0): quantas CVMs nunca usadas ficam prontas. Tirar uma dispara
 * a reposição em segundo plano; sem nenhuma pronta, cria na hora.
 *
 * Duas travas contra reuso: o pool nunca entrega o mesmo id duas vezes (e a CVM é destruída depois
 * do job, com ou sem sucesso), e o agente com DNAT_SINGLE_USE=1 recusa o segundo /execute ("used").
 */
const crypto = require("node:crypto");
const path = require("node:path");
const http = require("node:http");
const { spawn } = require("node:child_process");

const AGENT_PORT = 5000;

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function getJson(url, timeoutMs = 3000) {
  const res = await fetch(url, { signal: AbortSignal.timeout(timeoutMs) });
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return res.json();
}

/** Espera o agente responder /health, sem job aceito ainda. */
async function waitAgent(url, { timeoutMs = 60000, intervalMs = 250 } = {}) {
  const deadline = Date.now() + timeoutMs;
  let last;
  while (Date.now() < deadline) {
    try {
      const h = await getJson(`${url}/health`, 2000);
      if (h.used) throw new Error(`job VM at ${url} already ran a job`);
      return h;
    } catch (e) {
      if (/already ran a job/.test(e.message)) throw e;
      last = e;
    }
    await sleep(intervalMs);
  }
  throw new Error(`job VM agent at ${url} did not come up: ${last?.message || "timeout"}`);
}

// ---------------------------------------------------------------- provedores

class StaticProvider {
  constructor({ url }) {
    this.name = "static";
    this.singleUse = false;
    this.url = url.replace(/\/execute$/, "").replace(/\/$/, "");
  }

  async create() {
    await waitAgent(this.url, { timeoutMs: 3000 });
    return { id: `static:${this.url}`, url: this.url };
  }

  async destroy() {}
}

/** Pedido à API do Docker Engine pelo socket unix, sem o CLI do Docker. */
function dockerRequest(socketPath, method, p, body) {
  return new Promise((resolve, reject) => {
    const data = body === undefined ? null : Buffer.from(JSON.stringify(body));
    const req = http.request(
      { socketPath, method, path: p /* sem versão: o daemon usa a dele */, headers: data ? { "Content-Type": "application/json", "Content-Length": data.length } : {} },
      (res) => {
        const chunks = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () => {
          const text = Buffer.concat(chunks).toString("utf8");
          let json = null;
          try {
            json = text ? JSON.parse(text) : null;
          } catch {
            json = null;
          }
          if (res.statusCode >= 400) reject(new Error(`docker ${method} ${p}: ${res.statusCode} ${json?.message || text}`));
          else resolve(json);
        });
      },
    );
    req.on("error", reject);
    if (data) req.write(data);
    req.end();
  });
}

function parseBytes(v) {
  if (v === undefined || v === null || v === "") return 0;
  const m = String(v).trim().toLowerCase().match(/^(\d+(?:\.\d+)?)\s*([kmgt]?)b?$/);
  if (!m) throw new Error(`bad memory size: ${v}`);
  return Math.round(Number(m[1]) * 1024 ** " kmgt".indexOf(m[2] || " "));
}

class DockerProvider {
  constructor({ socketPath, image, network, memory, env = {}, owner = "cvm1" }) {
    this.name = "docker";
    this.owner = owner;
    this.singleUse = true;
    this.socketPath = socketPath;
    this.image = image;
    this.network = network;
    this.memoryBytes = parseBytes(memory);
    this.env = env;
  }

  async create() {
    const name = `dnat-job-${crypto.randomUUID().slice(0, 12)}`;
    const env = { DNAT_EGRESS_LOCK: "1", DNAT_SINGLE_USE: "1", ...this.env };
    const created = await dockerRequest(this.socketPath, "POST", `/containers/create?name=${name}`, {
      Image: this.image,
      Env: Object.entries(env).map(([k, v]) => `${k}=${v}`),
      // dnat.owner: a CVM1 dona; na partida ela apaga só as próprias CVMs órfãs (sweep), não as de outra pilha.
      Labels: { "dnat.role": "job-vm", "dnat.owner": this.owner },
      HostConfig: {
        // Só para a regra de saída do start-direct.sh; o agente e o job rodam sem capability.
        CapAdd: ["NET_ADMIN"],
        NetworkMode: this.network,
        ...(this.memoryBytes ? { Memory: this.memoryBytes, MemorySwap: this.memoryBytes } : {}),
      },
    });
    const id = created.Id;
    try {
      await dockerRequest(this.socketPath, "POST", `/containers/${id}/start`);
      const info = await dockerRequest(this.socketPath, "GET", `/containers/${id}/json`);
      const ip = info.NetworkSettings?.Networks?.[this.network]?.IPAddress;
      if (!ip) throw new Error(`job VM ${name} has no address on network ${this.network}`);
      const url = `http://${ip}:${AGENT_PORT}`;
      await waitAgent(url);
      return { id, name, url };
    } catch (e) {
      await this.destroy({ id }).catch(() => {});
      throw e;
    }
  }

  async destroy(vm) {
    await dockerRequest(this.socketPath, "DELETE", `/containers/${vm.id}?force=true&v=true`).catch((e) => {
      if (!/404/.test(e.message)) throw e;
    });
  }

  /** CVMs de job desta CVM1 que sobraram de uma queda (com os dados de um job dentro): destrói e conta. */
  async sweep() {
    const filters = encodeURIComponent(JSON.stringify({ label: ["dnat.role=job-vm", `dnat.owner=${this.owner}`] }));
    const list = await dockerRequest(this.socketPath, "GET", `/containers/json?all=1&filters=${filters}`);
    for (const c of list || []) await this.destroy({ id: c.Id });
    return (list || []).length;
  }

  /** O container ainda existe? (para os testes conferirem a destruição) */
  async exists(id) {
    try {
      await dockerRequest(this.socketPath, "GET", `/containers/${id}/json`);
      return true;
    } catch (e) {
      if (/404/.test(e.message)) return false;
      throw e;
    }
  }
}

function runCommand(cmd, env) {
  return new Promise((resolve, reject) => {
    const p = spawn("sh", ["-c", cmd], { env: { ...process.env, ...env }, stdio: ["ignore", "pipe", "pipe"] });
    let out = "";
    let err = "";
    p.stdout.on("data", (c) => (out += c));
    p.stderr.on("data", (c) => (err += c));
    p.on("error", reject);
    p.on("close", (code) => (code === 0 ? resolve(out) : reject(new Error(`job VM command failed (${code}): ${err.trim().slice(-500)}`))));
  });
}

class CommandProvider {
  constructor({ createCmd, destroyCmd }) {
    if (!createCmd || !destroyCmd) throw new Error("DNAT_JOB_VM_CREATE_CMD and DNAT_JOB_VM_DESTROY_CMD are required");
    this.name = "command";
    this.singleUse = true;
    this.createCmd = createCmd;
    this.destroyCmd = destroyCmd;
  }

  async create() {
    const out = await runCommand(this.createCmd, {});
    const last = out.trim().split("\n").pop();
    const vm = JSON.parse(last);
    if (!vm.id || !vm.url) throw new Error("DNAT_JOB_VM_CREATE_CMD must print {\"id\", \"url\"}");
    vm.url = vm.url.replace(/\/$/, "");
    try {
      await waitAgent(vm.url, { timeoutMs: 600000, intervalMs: 2000 });
    } catch (e) {
      await this.destroy(vm).catch(() => {});
      throw e;
    }
    return vm;
  }

  async destroy(vm) {
    await runCommand(this.destroyCmd, { DNAT_JOB_VM_ID: vm.id });
  }
}

function providerFromEnv(env = process.env) {
  const kind = env.DNAT_JOB_VM_PROVIDER || "static";
  if (kind === "static") return new StaticProvider({ url: env.EXECUTOR_URL || "http://localhost:5000" });
  if (kind === "docker") {
    const host = env.DOCKER_HOST || "";
    return new DockerProvider({
      socketPath: host.startsWith("unix://") ? host.slice("unix://".length) : "/var/run/docker.sock",
      image: env.DNAT_JOB_VM_IMAGE || "dnat-executor-direct:latest",
      network: env.DNAT_JOB_VM_NETWORK || "dnat-runtime",
      memory: env.DNAT_JOB_VM_MEMORY || "",
      // Variáveis a mais para o agente da CVM de job, em JSON (ex.: teto de tempo, threads do treino).
      env: env.DNAT_JOB_VM_ENV ? JSON.parse(env.DNAT_JOB_VM_ENV) : {},
      // Dono: o diretório de execuções identifica a CVM1 (duas pilhas no mesmo host têm diretórios diferentes).
      owner: env.DNAT_JOB_VM_OWNER || `cvm1-${crypto.createHash("sha256")
        .update(path.resolve(env.DNAT_EXECUTIONS_ROOT || path.join(__dirname, "..", "executions"))).digest("hex").slice(0, 16)}`,
    });
  }
  if (kind === "command") return new CommandProvider({ createCmd: env.DNAT_JOB_VM_CREATE_CMD, destroyCmd: env.DNAT_JOB_VM_DESTROY_CMD });
  throw new Error(`unknown DNAT_JOB_VM_PROVIDER: ${kind}`);
}

// ---------------------------------------------------------------- pool

class JobVmPool {
  constructor({ provider, size = 0, log = () => {} }) {
    this.provider = provider;
    this.size = provider.singleUse ? size : 0;
    this.log = log;
    this.ready = [];
    this.handed = new Set(); // ids já entregues a um job: nunca de novo
    this.active = new Map(); // entregues e ainda não destruídos: o close() os destrói (desligar no meio de um job)
    this.filling = null;
    this.closed = false;
  }

  async _create() {
    const t0 = Date.now();
    const vm = await this.provider.create();
    return { ...vm, provider: this.provider.name, singleUse: this.provider.singleUse, createdAt: new Date().toISOString(), bootMs: Date.now() - t0 };
  }

  /** Repõe o warm pool em segundo plano; erros só vão para o log (o take cria na hora). */
  refill() {
    if (this.closed || this.filling || this.ready.length >= this.size) return this.filling;
    this.filling = (async () => {
      try {
        while (!this.closed && this.ready.length < this.size) {
          const vm = await this._create();
          if (this.closed) await this.provider.destroy(vm);
          else this.ready.push(vm);
        }
      } catch (e) {
        this.log(`warm pool: ${e.message}`);
      } finally {
        this.filling = null;
      }
    })();
    return this.filling;
  }

  /** Uma CVM nunca usada para um job. */
  async take() {
    let vm = this.ready.shift();
    const fromPool = Boolean(vm);
    if (!vm) vm = await this._create();
    if (this.provider.singleUse) {
      if (this.handed.has(vm.id)) throw new Error(`job VM ${vm.id} was already handed to a job`);
      this.handed.add(vm.id);
      this.active.set(vm.id, vm);
    }
    this.refill();
    return { ...vm, fromPool, takenAt: new Date().toISOString() };
  }

  /** Depois do job: lê a memória de pico e destrói a CVM. Devolve o registro para a execução. */
  async finish(vm) {
    let stats = null;
    try {
      stats = await getJson(`${vm.url}/stats`, 5000);
    } catch (e) {
      this.log(`job VM ${vm.id}: stats unavailable (${e.message})`);
    }
    let destroyError = null;
    if (this.provider.singleUse) {
      this.active.delete(vm.id);
      try {
        await this.provider.destroy(vm);
      } catch (e) {
        destroyError = e.message;
        this.log(`job VM ${vm.id}: destroy failed (${e.message})`);
      }
    }
    return {
      id: vm.name || vm.id,
      provider: vm.provider,
      singleUse: vm.singleUse,
      fromPool: vm.fromPool,
      bootMs: vm.bootMs,
      createdAt: vm.createdAt,
      takenAt: vm.takenAt,
      destroyedAt: this.provider.singleUse && !destroyError ? new Date().toISOString() : null,
      ...(destroyError ? { destroyError } : {}),
      ...(stats ? { peakRssBytes: stats.peakRssBytes ?? null, cgroupPeakBytes: stats.cgroupPeakBytes ?? null, memTotalBytes: stats.memTotalBytes ?? null, jobsAccepted: stats.jobsAccepted } : {}),
    };
  }

  async close() {
    this.closed = true;
    await this.filling;
    const left = [...this.ready.splice(0), ...this.active.values()];
    if (this.active.size) this.log(`closing with ${this.active.size} job VM(s) still running a job: destroying them`);
    this.active.clear();
    await Promise.all(left.map((vm) => this.provider.destroy(vm).catch(() => {})));
  }

  /** Na partida: destrói as CVMs que esta CVM1 deixou de uma queda anterior (se o provedor souber listar). */
  async sweep() {
    return typeof this.provider.sweep === "function" ? this.provider.sweep() : 0;
  }
}

function poolFromEnv(env = process.env, log = console.error) {
  return new JobVmPool({ provider: providerFromEnv(env), size: Number(env.DNAT_JOB_VM_POOL || 0), log });
}

module.exports = { CommandProvider, DockerProvider, JobVmPool, StaticProvider, dockerRequest, parseBytes, poolFromEnv, providerFromEnv, waitAgent };
