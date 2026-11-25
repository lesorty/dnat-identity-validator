#!/usr/bin/env node
/**
 * Teste 11: o atacante com muitas identidades (P6; D7, E14 §18.5, T-1708, T-1212).
 *
 * Quem ataca o Juiz quer muitas tentativas. Cada identidade custa uma prova de trabalho e tem uma
 * cota; este roteiro faz o papel do atacante e do usuário honesto contra as rotas reais da CVM1
 * (registro, pedidos assinados e livro de cotas, por HTTP, num Express só com a identidade, o mesmo
 * do Teste 9). O veredito é SIMULADO no corpo do job: o que se testa aqui é o limite de tentativas,
 * não o Juiz. A taxa de escape do Juiz (e) vem do Teste 6; enquanto ele não roda, o modelo usa uma
 * faixa de e.
 *
 *   1. N identidades de atacante: cada uma minera a prova, registra e submete derivados reprovados
 *      até a CVM1 recusar (402). Conta as tentativas aceitas por identidade.
 *   2. Um atacante cujos derivados caem em inconclusivo (custa 2): o pior caso para a cota.
 *   3. Truques: a prova de uma chave para outra chave, a mesma chave de novo, pedido sem assinatura
 *      e o mesmo pedido assinado duas vezes. Jobs que falham não gastam cota (e não dão veredito).
 *   4. Usuários honestos: derivados aprovados (custa 1) até a recusa.
 *   5. Economia: com a taxa de hash do Teste 10 (ou medida aqui), o custo de CPU de um escape para o
 *      atacante e de uma aprovação para o honesto, e a chance de escape por orçamento de CPU.
 *
 *   node e2e/t11_atacante_sybil.js                   d = 16, 10 atacantes, 2 honestos (~1 min)
 *   node e2e/t11_atacante_sybil.js --d 20            o da nuvem (~2 min numa VM de 4 vCPU)
 *
 * Resultado em results/T11_atacante_sybil.{json,md}.
 */
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { INITIAL_BALANCE, RESERVE_COST, SETTLE_COSTS, signRequest, solveProof } = require("../scripts/identity");
const client = require("../scripts/identity_client");
const { identityOnlyApp, listen } = require("./demo_cota");

const HOUR = 3600;
const RESULTS = path.join(__dirname, "..", "results");

/** Quantos jobs de um desfecho uma identidade nova consegue antes da recusa, pela regra do livro. */
function attemptsPerIdentity(outcome, balance = INITIAL_BALANCE) {
  let n = 0;
  while (balance >= RESERVE_COST) {
    balance -= SETTLE_COSTS[outcome];
    n += 1;
    if (SETTLE_COSTS[outcome] === 0) return Infinity;
  }
  return n;
}

/**
 * Economia do ataque (E14 §18.5). Com k1 tentativas por identidade e escape com probabilidade e por
 * tentativa, o atacante precisa em média de 1/e tentativas, ou 1/(k1·e) identidades; o honesto paga
 * uma identidade a cada `honest` aprovações.
 */
function economics({ rate1, rateN, workersN, k1Rejected, k1Inconclusive, honest, escapeRates, difficulties, budgetsHours }) {
  const perD = difficulties.map((d) => {
    const cId = 2 ** d / rate1; // segundos de um núcleo por identidade
    return {
      difficulty: d,
      identitySeconds: cId,
      honestPerApprovalSeconds: cId / honest,
      attacker: escapeRates.map((e) => ({
        e,
        perEscapeSeconds: cId / (k1Rejected * e),
        perEscapeSecondsBestCase: cId / (k1Inconclusive * e),
        ratioToHonest: honest / (k1Rejected * e),
      })),
    };
  });
  const budgets = [];
  for (const d of difficulties.filter((x) => x >= 28)) {
    for (const hours of budgetsHours) {
      const identities = Math.floor((hours * HOUR * rateN) / 2 ** d);
      const k = identities * k1Rejected;
      budgets.push({
        difficulty: d,
        hours,
        workers: workersN,
        identities,
        attempts: k,
        pEscape: escapeRates.map((e) => ({ e, p: 1 - (1 - e) ** k })),
      });
    }
  }
  return { perD, budgets };
}

function human(seconds) {
  if (!Number.isFinite(seconds)) return "∞";
  if (seconds < 1) return `${(seconds * 1e3).toFixed(0)} ms`;
  if (seconds < 120) return `${seconds.toFixed(1)} s`;
  if (seconds < 2 * HOUR) return `${(seconds / 60).toFixed(1)} min`;
  if (seconds < 48 * HOUR) return `${(seconds / HOUR).toFixed(1)} h`;
  return `${(seconds / 86400).toFixed(1)} dias`;
}

const pct = (x) => (x > 0.999 && x < 1 ? "> 99.9%" : `${(x * 100).toFixed(x < 0.01 ? 2 : 1)}%`);

/** Taxas de hash: as do Teste 10, se o resultado existe; senão uma medida rápida aqui. */
function hashRates(t10Path) {
  if (t10Path && fs.existsSync(t10Path)) {
    const t10 = JSON.parse(fs.readFileSync(t10Path, "utf8"));
    const rel = path.relative(path.join(__dirname, ".."), t10Path);
    return { source: rel.startsWith("..") ? path.basename(t10Path) : rel, rate1: t10.bench.hashesPerSecond,
      rateN: t10.multicore.hashesPerSecond, workersN: t10.multicore.workers, machine: t10.machine };
  }
  const bench = client.benchProof({ minBits: 14, maxBits: 18, reps: 3 });
  const n = os.cpus().length;
  return { source: "medida rápida neste roteiro (sem Teste 10); núcleos extrapolados como 1 núcleo × n",
    rate1: bench.hashesPerSecond, rateN: bench.hashesPerSecond * n, workersN: n, machine: client.machineInfo() };
}

async function run({ difficulty = 16, attackers = 10, honest = 2, escapeRates = [0.005, 0.01, 0.02, 0.05],
  modelDifficulties = [20, 24, 28, 30, 32, 34, 36], budgetsHours = [24, 168], t10Path = path.join(RESULTS, "T10_preco_identidade.json"),
  log = console.error } = {}) {
  const state = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-t11-"));
  const { app } = identityOnlyApp({ statePath: path.join(state, "identities.json"), difficulty });
  const { server, url } = await listen(app);
  const job = (identity, verdict) => client.signedRequest({ apiUrl: url, identity, path: "/api/demo/job", json: { verdict } })
    .then((r) => ({ status: 200, ...r }), (e) => ({ status: e.status, error: e.body?.error || e.message }));
  /** Submete até a recusa (ou `cap` jobs); devolve as tentativas aceitas e o status que parou. */
  const untilRefused = async (identity, verdict, cap = 100) => {
    let accepted = 0;
    let last;
    for (let i = 0; i < cap; i += 1) {
      last = await job(identity, verdict);
      if (last.status !== 200) break;
      accepted += 1;
    }
    return { accepted, stoppedWith: last.status, balance: last.balance };
  };
  const register = async (identity) => {
    const t0 = process.hrtime.bigint();
    const reg = await client.registerIdentity({ apiUrl: url, identity });
    return { reg, seconds: Number(process.hrtime.bigint() - t0) / 1e9 };
  };
  const post = (p, body, headers = {}) => fetch(`${url}${p}`, { method: "POST", headers: { "Content-Type": "application/json", ...headers }, body });

  try {
    // 1. Atacantes com derivados reprovados.
    log(`T11: ${attackers} identidades de atacante, d = ${difficulty}`);
    const attackerRows = [];
    for (let i = 0; i < attackers; i += 1) {
      const identity = client.generateIdentity();
      const { seconds } = await register(identity);
      const r = await untilRefused(identity, "rejected");
      attackerRows.push({ identity: identity.id.slice(0, 12), registerSeconds: seconds, ...r });
      log(`  atacante ${i + 1}: prova em ${human(seconds)}, ${r.accepted} reprovados aceitos, depois ${r.stoppedWith}`);
    }

    // 2. Derivados que caem em inconclusivo: o caso em que a cota rende mais ao atacante.
    const incId = client.generateIdentity();
    await register(incId);
    const inconclusive = await untilRefused(incId, "inconclusive");
    log(`T11: atacante só com inconclusivos: ${inconclusive.accepted} tentativas`);

    // 3. Truques.
    const { challenge } = await (await fetch(`${url}/api/identity/challenge`)).json();
    const a = client.generateIdentity();
    const b = client.generateIdentity();
    const nonceA = solveProof(Buffer.from(challenge, "hex"), Buffer.from(a.publicKey, "hex"), difficulty);
    const regA = await post("/api/identity/register", JSON.stringify({ publicKey: a.publicKey, nonce: nonceA.toString() }));
    const reuse = await post("/api/identity/register", JSON.stringify({ publicKey: b.publicKey, nonce: nonceA.toString() }));
    const again = await post("/api/identity/register", JSON.stringify({ publicKey: a.publicKey, nonce: nonceA.toString() }));
    const unsigned = await post("/api/demo/job", JSON.stringify({ verdict: "rejected" }));
    const body = JSON.stringify({ verdict: "rejected" });
    const headers = signRequest({ privateKey: a.seed, publicKey: a.publicKey, method: "POST", path: "/api/demo/job", body: Buffer.from(body) });
    const first = await post("/api/demo/job", body, headers);
    const replay = await post("/api/demo/job", body, headers);
    const failures = [];
    for (let i = 0; i < 3; i += 1) failures.push(await job(a, "failure"));
    const tricks = [
      { name: "a prova da chave A registra A", status: regA.status, expected: 201 },
      { name: "a prova de A não registra a chave B", status: reuse.status, expected: 400 },
      { name: "a chave A não registra de novo", status: again.status, expected: 409 },
      { name: "job sem assinatura", status: unsigned.status, expected: 401 },
      { name: "o pedido assinado, primeira vez", status: first.status, expected: 200 },
      { name: "o mesmo pedido assinado, repetido", status: replay.status, expected: 401 },
    ].map((t) => ({ ...t, ok: t.status === t.expected }));
    const failureBalances = failures.map((f) => f.balance);

    // 4. Honestos.
    log(`T11: ${honest} usuários honestos`);
    const honestRows = [];
    for (let i = 0; i < honest; i += 1) {
      const identity = client.generateIdentity();
      const { seconds } = await register(identity);
      const r = await untilRefused(identity, "approved");
      honestRows.push({ identity: identity.id.slice(0, 12), registerSeconds: seconds, ...r });
      log(`  honesto ${i + 1}: ${r.accepted} aprovações, depois ${r.stoppedWith}`);
    }

    // 5. Economia.
    const k1Rejected = attemptsPerIdentity("rejected");
    const k1Inconclusive = attemptsPerIdentity("inconclusive");
    const honestPerId = attemptsPerIdentity("approved");
    const rates = hashRates(t10Path);
    const econ = economics({ rate1: rates.rate1, rateN: rates.rateN, workersN: rates.workersN, k1Rejected, k1Inconclusive,
      honest: honestPerId, escapeRates, difficulties: modelDifficulties, budgetsHours });

    const totalAttempts = attackerRows.reduce((s, r) => s + r.accepted, 0);
    const checks = [
      [`cada identidade de atacante aceita exatamente ${k1Rejected} reprovados e depois recebe 402`,
        attackerRows.every((r) => r.accepted === k1Rejected && r.stoppedWith === 402)],
      [`${attackers} identidades dão ${attackers * k1Rejected} tentativas, nem uma a mais`, totalAttempts === attackers * k1Rejected],
      [`só com inconclusivos, ${k1Inconclusive} tentativas e depois 402`, inconclusive.accepted === k1Inconclusive && inconclusive.stoppedWith === 402],
      [`o honesto faz ${honestPerId} aprovações por identidade e depois recebe 402`,
        honestRows.every((r) => r.accepted === honestPerId && r.stoppedWith === 402)],
      ["os truques são recusados (prova reaproveitada, chave repetida, sem assinatura, repetição)", tricks.every((t) => t.ok)],
      ["jobs que falham não gastam cota", failureBalances.every((x) => x === failureBalances[0]) && failures.every((f) => f.status === 200)],
    ].map(([name, ok]) => ({ name, ok }));

    return {
      note: "Teste 11 (P6): o atacante com muitas identidades. Rotas reais de identidade e cota da CVM1 por HTTP; veredito SIMULADO no corpo do job. A taxa de escape e é uma faixa até o Teste 6 medir a do Juiz.",
      measuredAtUtc: new Date().toISOString(),
      params: { difficulty, attackers, honest, escapeRates, modelDifficulties, budgetsHours, quota: { initialBalance: INITIAL_BALANCE, reserve: RESERVE_COST, costs: SETTLE_COSTS } },
      attackerRows,
      inconclusive,
      tricks,
      failureBalances,
      honestRows,
      perIdentity: { rejected: k1Rejected, inconclusive: k1Inconclusive, approved: honestPerId },
      rates: { source: rates.source, oneCore: rates.rate1, allCores: rates.rateN, workers: rates.workersN, machine: rates.machine },
      economics: econ,
      checks,
    };
  } finally {
    server.close();
    fs.rmSync(state, { recursive: true, force: true });
  }
}

function markdown(r) {
  const es = r.params.escapeRates;
  return `# Teste 11: o atacante com muitas identidades

${r.note}

Cota: saldo inicial ${r.params.quota.initialBalance}; todo job reserva ${r.params.quota.reserve}; o veredito cobra ${r.params.quota.costs.approved} (aprovado), ${r.params.quota.costs.inconclusive} (inconclusivo), ${r.params.quota.costs.rejected} (reprovado) ou ${r.params.quota.costs.failure} (falha). Prova de trabalho com d = ${r.params.difficulty} neste roteiro.

## Tentativas por identidade, medidas pela API

| Quem | Desfecho de cada job | Jobs aceitos | Depois |
|---|---|---:|---:|
${r.attackerRows.map((x, i) => `| atacante ${i + 1} (${x.identity}…) | reprovado | ${x.accepted} | ${x.stoppedWith} |`).join("\n")}
| atacante só com inconclusivos | inconclusivo | ${r.inconclusive.accepted} | ${r.inconclusive.stoppedWith} |
${r.honestRows.map((x, i) => `| honesto ${i + 1} (${x.identity}…) | aprovado | ${x.accepted} | ${x.stoppedWith} |`).join("\n")}

Como todo job reserva ${r.params.quota.reserve}, a identidade para quando o saldo fica abaixo disso: o honesto faz **${r.perIdentity.approved}** aprovações (não ${r.params.quota.initialBalance}) e o atacante tem **${r.perIdentity.rejected}** tentativas reprovadas, ou até **${r.perIdentity.inconclusive}** se todas caírem em inconclusivo.

## Truques do atacante

| Tentativa | HTTP | Esperado |
|---|---:|---:|
${r.tricks.map((t) => `| ${t.name} | ${t.status} | ${t.expected} |`).join("\n")}
| 3 jobs que falham (saldo depois de cada um) | ${r.failureBalances.join(", ")} | sem gasto |

Um job que falha devolve a reserva e não dá veredito ao atacante: não ensina nada, mas gasta CVM da plataforma (limite a tratar à parte, fora da cota).

## Economia do ataque

Taxas de hash (${r.rates.source}): ${Math.round(r.rates.oneCore).toLocaleString("pt-BR")} por segundo num núcleo; ${Math.round(r.rates.allCores).toLocaleString("pt-BR")} com ${r.rates.workers} núcleos.

Custo em CPU de um núcleo. Escape: tentativas reprovadas (${r.perIdentity.rejected} por identidade); entre parênteses, o caso em que todas caem em inconclusivo (${r.perIdentity.inconclusive}).

| d | uma identidade | honesto, por aprovação | ${es.map((e) => `atacante por escape, e = ${pct(e)}`).join(" | ")} |
|---:|---:|---:|${es.map(() => "---:").join("|")}|
${r.economics.perD.map((x) => `| ${x.difficulty} | ${human(x.identitySeconds)} | ${human(x.honestPerApprovalSeconds)} | ${x.attacker.map((a) => `${human(a.perEscapeSeconds)} (${human(a.perEscapeSecondsBestCase)})`).join(" | ")} |`).join("\n")}

Razão entre o custo de um escape e o de uma aprovação honesta: ${r.economics.perD[0].attacker.map((a) => `${Math.round(a.ratioToHonest)}× com e = ${pct(a.e)}`).join("; ")}. Não depende de d: o d escolhe o preço absoluto, a cota escolhe a razão.

Chance de escape com um orçamento de CPU (todos os ${r.rates.workers} núcleos):

| d | orçamento | identidades | tentativas | ${es.map((e) => `P(escape), e = ${pct(e)}`).join(" | ")} |
|---:|---:|---:|---:|${es.map(() => "---:").join("|")}|
${r.economics.budgets.map((b) => `| ${b.difficulty} | ${b.hours} h | ${b.identities.toLocaleString("pt-BR")} | ${b.attempts.toLocaleString("pt-BR")} | ${b.pEscape.map((p) => pct(p.p)).join(" | ")} |`).join("\n")}

## Conferências

${r.checks.map((c) => `- ${c.ok ? "✅" : "❌"} ${c.name}`).join("\n")}
`;
}

function parseArgs(argv) {
  const opts = {};
  for (let i = 0; i < argv.length; i += 2) {
    if (!argv[i].startsWith("--")) throw new Error(`argumento inesperado: ${argv[i]}`);
    opts[argv[i].slice(2)] = argv[i + 1];
  }
  const num = (k, def) => (opts[k] === undefined ? def : Number(opts[k]));
  const list = (k, def) => (opts[k] === undefined ? def : String(opts[k]).split(",").map(Number));
  return {
    difficulty: num("d", 16),
    attackers: num("attackers", 10),
    honest: num("honest", 2),
    escapeRates: list("e", [0.005, 0.01, 0.02, 0.05]),
    t10Path: opts.t10 || path.join(RESULTS, "T10_preco_identidade.json"),
    out: opts.out || path.join(RESULTS, "T11_atacante_sybil"),
  };
}

async function main(argv = process.argv.slice(2)) {
  const { out, ...options } = parseArgs(argv);
  const result = await run(options);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(`${out}.json`, JSON.stringify(result, null, 2) + "\n");
  fs.writeFileSync(`${out}.md`, markdown(result));
  for (const c of result.checks) console.log(`${c.ok ? "ok    " : "FALHOU"} ${c.name}`);
  console.log(`resultado: ${out}.{json,md}`);
  return result.checks.every((c) => c.ok) ? 0 : 1;
}

if (require.main === module) {
  main().then((code) => process.exit(code), (e) => {
    console.error(e);
    process.exit(1);
  });
}

module.exports = { attemptsPerIdentity, economics, markdown, run };
