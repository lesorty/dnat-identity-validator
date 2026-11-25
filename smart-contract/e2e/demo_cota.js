#!/usr/bin/env node
/**
 * Demonstração do Teste 9 (T-1707): identidade e cota, sem cadeia nem executor.
 *
 * Monta um Express só com as rotas de identidade da CVM1 (identityRouter) e uma rota de job de
 * demonstração, assinada, que faz o mesmo que o run-from-cids faz com a cota: reserva 5 no aceite e
 * acerta pelo veredito (aqui SIMULADO, vindo no corpo). Roteiro:
 *
 *   1. registra uma identidade com prova de trabalho (d = 12 na demonstração) e mostra o saldo Q = 20;
 *   2. pedido sem assinatura e pedido com carimbo velho: 401;
 *   3. job que falha: a reserva volta inteira;
 *   4. quatro jobs reprovados: 5 cada, o saldo chega a 0;
 *   5. o 5º job é recusado com 402 antes de gastar CVM.
 *
 *   node e2e/demo_cota.js          resultado em results/demo_cota.{json,md}
 */
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const express = require("express");
const { IdentityError, IdentityRegistry, RequestVerifier, identityRouter, signRequest } = require("../scripts/identity");
const client = require("../scripts/identity_client");

/** Express só com identidade e a rota de job de demonstração (a mesma usada pelo teste). */
function identityOnlyApp({ statePath, difficulty = 12 }) {
  const registry = new IdentityRegistry({ statePath, difficulty });
  const app = express();
  app.use(express.json({ verify: (req, _res, buf) => { req.rawBody = buf; } }));
  app.use("/api/identity", identityRouter(registry));
  const signed = new RequestVerifier({ registry }).middleware();
  // Job de demonstração: a reserva no aceite e o acerto pelo veredito, como no run-from-cids.
  app.post("/api/demo/job", signed, (req, res) => {
    const reservationId = crypto.randomUUID();
    try {
      registry.reserve(req.identity.id, reservationId);
    } catch (e) {
      return res.status(e instanceof IdentityError ? e.status : 500).json({ error: e.message });
    }
    const settled = registry.settle(reservationId, req.body?.verdict ?? "failure");
    res.json({ reservationId, outcome: settled.outcome, charged: settled.charged, refunded: settled.refunded, balance: settled.balance });
  });
  return { app, registry };
}

async function listen(app) {
  return new Promise((resolve) => {
    const server = app.listen(0, "127.0.0.1", () => resolve({ server, url: `http://127.0.0.1:${server.address().port}` }));
  });
}

async function main() {
  const state = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-demo-cota-"));
  const { app } = identityOnlyApp({ statePath: path.join(state, "identities.json") });
  const { server, url } = await listen(app);
  const steps = [];
  const note = (step, status, detail) => {
    steps.push({ step, status, ...detail });
    console.log(`${String(status).padEnd(4)} ${step}${detail.balance !== undefined ? ` · saldo ${detail.balance}` : ""}`);
  };
  try {
    const identity = client.generateIdentity();
    const reg = await client.registerIdentity({ apiUrl: url, identity });
    note("1. identidade registrada com prova de trabalho", 201, { id: reg.record.id.slice(0, 16), difficulty: reg.difficulty, balance: reg.record.balance });

    const job = (verdict, opts = {}) => client.signedRequest({ apiUrl: url, identity, path: "/api/demo/job", json: { verdict }, ...opts })
      .then((r) => ({ status: 200, ...r }))
      .catch((e) => ({ status: e.status, error: e.body?.error || e.message }));

    const unsigned = await fetch(`${url}/api/demo/job`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    note("2a. job sem assinatura", unsigned.status, {});
    const body = JSON.stringify({ verdict: "rejected" });
    const old = signRequest({ privateKey: identity.seed, publicKey: identity.publicKey, method: "POST", path: "/api/demo/job",
      body: Buffer.from(body), timestamp: Date.now() - 10 * 60 * 1000 });
    const stale = await fetch(`${url}/api/demo/job`, { method: "POST", headers: { "Content-Type": "application/json", ...old }, body });
    note("2b. job com carimbo de 10 min atrás", stale.status, {});

    const failed = await job("failure");
    note("3. job que falha: reserva devolvida", failed.status, { charged: failed.charged, balance: failed.balance });
    for (let i = 1; i <= 4; i++) {
      const r = await job("rejected");
      note(`4.${i} job reprovado`, r.status, { charged: r.charged, balance: r.balance });
    }
    const fifth = await job("rejected");
    note("5. 5º job, sem saldo para a reserva", fifth.status, { error: fifth.error });
    const summary = await (await fetch(`${url}/api/identity/${reg.record.id}`)).json();

    const checks = [
      ["registro abre saldo Q = 20", reg.record.balance === 20],
      ["sem assinatura e carimbo velho: 401", unsigned.status === 401 && stale.status === 401],
      ["falha devolve a reserva (saldo continua 20)", failed.balance === 20 && failed.charged === 0],
      ["4 reprovados esgotam o saldo", steps.filter((s) => s.step.startsWith("4.")).map((s) => s.balance).join() === "15,10,5,0"],
      ["o 5º job é recusado com 402", fifth.status === 402],
      ["contagens: 4 reprovados, 1 falha", summary.counts.rejected === 4 && summary.counts.failure === 1],
    ];
    for (const [n, ok] of checks) console.log(`${ok ? "ok  " : "FALHOU"} ${n}`);
    const result = { note: "Demonstração do Teste 9 (T-1707), sem cadeia nem executor; veredito SIMULADO no corpo do job.", steps, summary,
      checks: checks.map(([name, ok]) => ({ name, ok })) };
    const dir = process.env.DEMO_COTA_DIR || path.join(__dirname, "..", "results"); // o Teste 9 (tools/testes) grava na pasta do passo
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, "demo_cota.json"), JSON.stringify(result, null, 2) + "\n");
    fs.writeFileSync(path.join(dir, "demo_cota.md"), `# Demonstração da identidade e da cota (T-1707)

${result.note}

| Passo | HTTP | Cobrado | Saldo | Erro |
|---|---|---|---|---|
${steps.map((s) => `| ${s.step} | ${s.status} | ${s.charged ?? "-"} | ${s.balance ?? "-"} | ${s.error ?? "-"} |`).join("\n")}

## Conferências

${result.checks.map((c) => `- ${c.ok ? "✅" : "❌"} ${c.name}`).join("\n")}
`);
    return checks.every(([, ok]) => ok) ? 0 : 1;
  } finally {
    server.close();
    fs.rmSync(state, { recursive: true, force: true });
  }
}

if (require.main === module) {
  main().then((code) => process.exit(code), (e) => {
    console.error(e);
    process.exit(1);
  });
}

module.exports = { identityOnlyApp, listen };
