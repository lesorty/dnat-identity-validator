#!/usr/bin/env node
/**
 * Teste 10: o preço da identidade (P6; D7, E14 §18.3, T-1705).
 *
 * O Teste 9 prova que o mecanismo funciona. Este mede o que o artigo afirma sobre ele: criar uma
 * identidade é caro e conferir é barato, e o preço escolhe-se pela dificuldade d. Mede na máquina
 * onde roda (a VM da nuvem, para o artigo):
 *
 *   1. a prova de trabalho de d = min…max num núcleo (benchProof, o mesmo laço do cliente);
 *   2. a taxa de hash com todos os núcleos (worker_threads), que é o que um atacante usa;
 *   3. o tempo de conferir uma prova (um hash), em vários d: não depende de d;
 *   4. a lei do custo: cada bit a mais dobra o número de hashes (inclinação de log2 × d perto de 1);
 *   5. que a prova não se reaproveita: outra chave, outro desafio e chave repetida são recusados;
 *   6. a extrapolação para d até 32 e o d de referência para 1 h e 5 h de CPU, num núcleo, em todos
 *      os núcleos e, se dada com --gpu-rate, numa GPU (ex.: `hashcat -b -m 1400`, SHA-256 puro).
 *
 *   node e2e/t10_preco_identidade.js                       d de 16 a 22, 5 repetições (~3 min)
 *   node e2e/t10_preco_identidade.js --max 27 --reps 3     o da nuvem (~1 h numa VM de 4 vCPU)
 *   node e2e/t10_preco_identidade.js --gpu-rate 2.1e10     inclui a GPU na extrapolação
 *
 * Resultado em results/T10_preco_identidade.{json,md}.
 */
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { Worker } = require("node:worker_threads");
const { IdentityError, IdentityRegistry, powHash, solveProof, verifyProof } = require("../scripts/identity");
const client = require("../scripts/identity_client");

const IDENTITY_JS = path.join(__dirname, "..", "scripts", "identity.js");

/** Taxa de hash com n threads, cada uma testando `perWorker` nonces do mesmo laço do cliente. */
function multicoreRate({ workers = os.cpus().length, perWorker = 1 << 21 } = {}) {
  const code = `
    const { parentPort, workerData } = require("node:worker_threads");
    const crypto = require("node:crypto");
    const { powHash } = require(workerData.identityJs);
    const key = crypto.randomBytes(32), challenge = crypto.randomBytes(32);
    let acc = 0;
    for (let n = 0n; n < BigInt(workerData.count); n += 1n) acc ^= powHash(challenge, key, n)[0];
    parentPort.postMessage(acc);
  `;
  const t0 = process.hrtime.bigint();
  const runs = Array.from({ length: workers }, () => new Promise((resolve, reject) => {
    const w = new Worker(code, { eval: true, workerData: { identityJs: IDENTITY_JS, count: perWorker } });
    w.once("message", resolve);
    w.once("error", reject);
  }));
  return Promise.all(runs).then(() => {
    const seconds = Number(process.hrtime.bigint() - t0) / 1e9;
    return { workers, hashes: workers * perWorker, seconds, hashesPerSecond: (workers * perWorker) / seconds };
  });
}

/** Tempo médio de conferir uma prova válida de dificuldade d (um hash), em microssegundos. */
function verifyCost(difficulties = [8, 12, 16], iterations = 100000) {
  return difficulties.map((d) => {
    const key = crypto.randomBytes(32);
    const challenge = crypto.randomBytes(32);
    const nonce = solveProof(challenge, key, d);
    let ok = true;
    const t0 = process.hrtime.bigint();
    for (let i = 0; i < iterations; i += 1) ok = verifyProof(challenge, key, nonce, d) && ok;
    const seconds = Number(process.hrtime.bigint() - t0) / 1e9;
    return { difficulty: d, iterations, valid: ok, microseconds: (seconds / iterations) * 1e6 };
  });
}

/**
 * Lei do custo: regressão de log2(hashes testados) em d, com todas as provas medidas. O número de
 * hashes de uma prova é geométrico (média 2^d), então a inclinação esperada é 1 e o intercepto 0;
 * a razão agregada Σhashes ÷ Σ2^d é o estimador do quanto a média bate com 2^d.
 */
function costLaw(rows) {
  const pts = [];
  let hashes = 0;
  let expected = 0;
  for (const r of rows) {
    for (const h of r.hashes) {
      pts.push([r.difficulty, Math.log2(h)]);
      hashes += h;
      expected += 2 ** r.difficulty;
    }
  }
  const n = pts.length;
  const mx = pts.reduce((a, p) => a + p[0], 0) / n;
  const my = pts.reduce((a, p) => a + p[1], 0) / n;
  const sxx = pts.reduce((a, p) => a + (p[0] - mx) ** 2, 0);
  const sxy = pts.reduce((a, p) => a + (p[0] - mx) * (p[1] - my), 0);
  const slope = sxx > 0 ? sxy / sxx : NaN;
  // log2 de uma geométrica de média grande tem desvio π / (√6 · ln 2) ≈ 1,85 bit, seja qual for d:
  // é o erro-padrão teórico da inclinação, que a conferência usa no lugar de uma margem fixa.
  const se = sxx > 0 ? (Math.PI / (Math.sqrt(6) * Math.LN2)) / Math.sqrt(sxx) : NaN;
  return { points: n, slope, slopeStdErr: se, pooledRatio: hashes / expected };
}

/** A prova amarra chave e implantação: outra chave, outro desafio e chave repetida são recusados. */
function reuseChecks(statePath, difficulty = 16) {
  const registry = new IdentityRegistry({ statePath, difficulty });
  const challenge = Buffer.from(registry.challenge().challenge, "hex");
  const a = client.generateIdentity();
  const b = client.generateIdentity();
  const nonce = solveProof(challenge, Buffer.from(a.publicKey, "hex"), difficulty);
  const status = (fn) => {
    try {
      fn();
      return 201;
    } catch (e) {
      return e instanceof IdentityError ? e.status : 500;
    }
  };
  const otherDeployment = crypto.randomBytes(32);
  const foreignNonce = solveProof(otherDeployment, Buffer.from(b.publicKey, "hex"), difficulty);
  return [
    { name: "a prova de A registra A", status: status(() => registry.register({ publicKey: a.publicKey, nonce: nonce.toString() })), expected: 201 },
    { name: "a mesma prova não registra outra chave", status: status(() => registry.register({ publicKey: b.publicKey, nonce: nonce.toString() })), expected: 400 },
    { name: "prova feita para outra implantação é recusada", status: status(() => registry.register({ publicKey: b.publicKey, nonce: foreignNonce.toString() })), expected: 400 },
    { name: "a mesma chave não registra duas vezes", status: status(() => registry.register({ publicKey: a.publicKey, nonce: nonce.toString() })), expected: 409 },
  ].map((c) => ({ ...c, ok: c.status === c.expected }));
}

const HOUR = 3600;

/** Segundos para criar uma identidade, por d e por atacante (1 núcleo, todos os núcleos, GPU). */
function extrapolate({ single, multi, gpu = null, difficulties = [20, 24, 26, 28, 30, 32, 36] }) {
  const rates = [["1 núcleo", single], [`${multi.workers} núcleos`, multi.hashesPerSecond]];
  if (gpu) rates.push(["GPU", gpu]);
  return {
    rates: rates.map(([who, rate]) => ({ who, hashesPerSecond: rate })),
    rows: difficulties.map((d) => ({ difficulty: d, seconds: Object.fromEntries(rates.map(([who, rate]) => [who, 2 ** d / rate])) })),
    // Menor d em que uma identidade custa pelo menos o alvo a quem tem aquele hardware.
    reference: [1, 5].map((hours) => ({
      hours,
      difficulty: Object.fromEntries(rates.map(([who, rate]) => [who, Math.ceil(Math.log2(hours * HOUR * rate))])),
    })),
  };
}

function human(seconds) {
  if (seconds < 1e-3) return `${(seconds * 1e6).toFixed(1)} µs`;
  if (seconds < 1) return `${(seconds * 1e3).toFixed(1)} ms`;
  if (seconds < 120) return `${seconds.toFixed(1)} s`;
  if (seconds < 2 * HOUR) return `${(seconds / 60).toFixed(1)} min`;
  if (seconds < 48 * HOUR) return `${(seconds / HOUR).toFixed(1)} h`;
  return `${(seconds / 86400).toFixed(1)} dias`;
}

function markdown(r) {
  const who = r.extrapolation.rates.map((x) => x.who);
  return `# Teste 10: o preço da identidade

${r.note}

Máquina: ${r.machine.cpuModel}, ${r.machine.logicalCpus} CPUs lógicas, Node ${r.machine.node}. Commit \`${r.commit}\`.

## Taxas de hash

| Quem | Hashes SHA-256 por segundo |
|---|---:|
${r.extrapolation.rates.map((x) => `| ${x.who} | ${Math.round(x.hashesPerSecond).toLocaleString("pt-BR")} |`).join("\n")}

## Prova medida num núcleo

| d | repetições | mediana | média | esperado (2^d ÷ taxa) |
|---:|---:|---:|---:|---:|
${r.bench.rows.map((x) => `| ${x.difficulty} | ${x.reps} | ${human(x.medianSeconds)} | ${human(x.meanSeconds)} | ${human(x.expectedSeconds)} |`).join("\n")}

Lei do custo: inclinação de log2(hashes) em d = **${r.law.slope.toFixed(3)} ± ${r.law.slopeStdErr.toFixed(3)}** (esperado 1), razão Σhashes ÷ Σ2^d = **${r.law.pooledRatio.toFixed(2)}** (esperado 1), com ${r.law.points} provas.

## Conferir custa um hash, em qualquer d

| d | conferências | tempo por conferência |
|---:|---:|---:|
${r.verify.map((v) => `| ${v.difficulty} | ${v.iterations.toLocaleString("pt-BR")} | ${v.microseconds.toFixed(2)} µs |`).join("\n")}

## Tempo para criar uma identidade (extrapolado de 2^d ÷ taxa)

| d | ${who.join(" | ")} |
|---:|${who.map(() => "---:").join("|")}|
${r.extrapolation.rows.map((x) => `| ${x.difficulty} | ${who.map((w) => human(x.seconds[w])).join(" | ")} |`).join("\n")}

**d de referência** (menor d em que uma identidade custa pelo menos o alvo):

| Alvo | ${who.join(" | ")} |
|---|${who.map(() => "---:").join("|")}|
${r.extrapolation.reference.map((x) => `| ${x.hours} h | ${who.map((w) => x.difficulty[w]).join(" | ")} |`).join("\n")}

Razão criar ÷ conferir em d = 30, num núcleo: **${r.asymmetryD30.toExponential(2)}**.

## A prova não se reaproveita

| Caso | HTTP | Esperado |
|---|---:|---:|
${r.reuse.map((c) => `| ${c.name} | ${c.status} | ${c.expected} |`).join("\n")}

## Conferências

${r.checks.map((c) => `- ${c.ok ? "✅" : "❌"} ${c.name}`).join("\n")}
`;
}

function parseArgs(argv) {
  const opts = {};
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (!a.startsWith("--")) throw new Error(`argumento inesperado: ${a}`);
    opts[a.slice(2)] = argv[i + 1];
    i += 1;
  }
  const num = (k, def) => (opts[k] === undefined ? def : Number(opts[k]));
  return {
    minBits: num("min", 16),
    maxBits: num("max", 22),
    reps: num("reps", 5),
    workers: num("workers", os.cpus().length),
    gpuRate: opts["gpu-rate"] === undefined ? null : Number(opts["gpu-rate"]),
    out: opts.out || path.join(__dirname, "..", "results", "T10_preco_identidade"),
  };
}

function gitCommit() {
  try {
    return require("node:child_process").execSync("git rev-parse --short HEAD", { cwd: __dirname, stdio: ["ignore", "pipe", "ignore"] }).toString().trim();
  } catch {
    return "desconhecido";
  }
}

async function run(options, log = console.error) {
  const { minBits, maxBits, reps, workers, gpuRate, perWorker } = options;
  if (gpuRate !== null && !(gpuRate > 0)) throw new Error("--gpu-rate precisa ser um número positivo (hashes/s)");
  log(`T10: prova de trabalho de d = ${minBits} a ${maxBits}, ${reps} repetições, num núcleo`);
  // benchProof não devolve os hashes de cada prova; o solver abaixo os guarda para a lei do custo.
  const hashesByD = new Map();
  const solve = (challenge, key, d) => {
    const nonce = solveProof(challenge, key, d);
    if (!hashesByD.has(d)) hashesByD.set(d, []);
    hashesByD.get(d).push(Number(nonce) + 1);
    return nonce;
  };
  const bench = client.benchProof({ minBits, maxBits, reps, solve,
    onRow: (row) => log(`  d=${row.difficulty}: mediana ${human(row.medianSeconds)}, esperado ${human(row.expectedSeconds)}`) });
  for (const row of bench.rows) row.hashes = hashesByD.get(row.difficulty);

  log(`T10: taxa com ${workers} threads`);
  const multi = await multicoreRate({ workers, perWorker });
  log("T10: custo de conferir");
  const verify = verifyCost();
  const state = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-t10-"));
  let reuse;
  try {
    reuse = reuseChecks(path.join(state, "identities.json"));
  } finally {
    fs.rmSync(state, { recursive: true, force: true });
  }
  const law = costLaw(bench.rows);
  const extrapolation = extrapolate({ single: bench.hashesPerSecond, multi, gpu: gpuRate });
  const verifySeconds = Math.max(...verify.map((v) => v.microseconds)) / 1e6;
  const asymmetryD30 = 2 ** 30 / bench.hashesPerSecond / verifySeconds;
  const micro = verify.map((v) => v.microseconds);
  const checks = [
    ["a lei do custo vale: inclinação de log2(hashes) em d a até 3 erros-padrão de 1", Math.abs(law.slope - 1) <= 3 * law.slopeStdErr],
    ["a média de hashes tem a ordem de 2^d: razão agregada entre 1/3 e 3", law.pooledRatio >= 1 / 3 && law.pooledRatio <= 3],
    ["conferir não depende de d: o maior tempo é menos que 3× o menor", Math.max(...micro) < 3 * Math.min(...micro)],
    ["conferir custa menos de 1 ms", verifySeconds < 1e-3],
    ["todas as provas conferidas eram válidas", verify.every((v) => v.valid)],
    ["a prova não se reaproveita (outra chave, outra implantação, chave repetida)", reuse.every((c) => c.ok)],
    ["os núcleos juntos fazem mais hashes que um núcleo", workers === 1 || multi.hashesPerSecond > bench.hashesPerSecond],
  ].map(([name, ok]) => ({ name, ok }));
  return {
    note: "Teste 10 (P6): o preço da identidade. Medido na máquina onde rodou; o d acima do medido é extrapolado de 2^d ÷ taxa."
      + (gpuRate ? " A taxa da GPU foi informada com --gpu-rate, não medida por este roteiro." : ""),
    measuredAtUtc: new Date().toISOString(),
    commit: gitCommit(),
    machine: client.machineInfo(),
    params: { minBits, maxBits, reps, workers, gpuRate },
    bench,
    multicore: multi,
    verify,
    law,
    reuse,
    extrapolation,
    asymmetryD30,
    checks,
  };
}

async function main(argv = process.argv.slice(2)) {
  const options = parseArgs(argv);
  const result = await run(options);
  fs.mkdirSync(path.dirname(options.out), { recursive: true });
  fs.writeFileSync(`${options.out}.json`, JSON.stringify(result, null, 2) + "\n");
  fs.writeFileSync(`${options.out}.md`, markdown(result));
  for (const c of result.checks) console.log(`${c.ok ? "ok    " : "FALHOU"} ${c.name}`);
  console.log(`resultado: ${options.out}.{json,md}`);
  return result.checks.every((c) => c.ok) ? 0 : 1;
}

if (require.main === module) {
  main().then((code) => process.exit(code), (e) => {
    console.error(e);
    process.exit(1);
  });
}

module.exports = { costLaw, extrapolate, human, markdown, multicoreRate, reuseChecks, run, verifyCost };
