#!/usr/bin/env node
/**
 * Fluxo inteiro numa máquina comum, no modo direto (T-811). Verificação de funcionamento: os tempos
 * e desfechos daqui NÃO são dado do artigo (todo dado do artigo sai da nuvem).
 *
 * Sobe, sem Docker e sem root:
 *   - cadeia: `hardhat node` e o DnatMarketplace implantado, com a CVM1 como operador;
 *   - IPFS: um servidor mínimo em memória com /api/v0/add e /api/v0/cat (só para este roteiro);
 *   - CVM2: build_vm_runtime/builder.py com DNAT_NO_MICROVM=1 (build-direct.sh, ext4 por mkfs -d);
 *   - CVM de job: vm_runtime/executor.py com DNAT_NO_MICROVM=1 (run-direct.sh, ext4 lido por debugfs);
 *   - CVM1: scripts/api-server.js, com estado num diretório temporário.
 *
 * E roda, pelo cliente assinado (identity_client.js), o caminho do derivado:
 *   identidade com prova de trabalho → depósito do base (tar.gz de um modelo minúsculo) → dataset →
 *   aplicação de fine-tuning simulado → compra de acesso → referência do pai depositada pelo
 *   operador → run-from-cids com parentModelId → derivado retido → Juiz como segundo job → recibo
 *   e cota.
 *
 * Cenários:
 *   A. Juiz real (model_gate): os estágios que dependem da nuvem ainda levantam StageNotReady, então
 *      o job termina em falha, nada vai ao contrato e a reserva da cota volta.
 *   B. Juiz SIMULADO aprovando (e2e/simulated_judge.js, numa lista permitida só de teste): recibo no
 *      contrato, derivado usável, cota 1.
 *   C. Juiz SIMULADO reprovando: recibo gravado, derivado inativo, cota 5.
 *
 *   node e2e/run_direct.js [--keep] [--serve] [--base-dir DIR]
 *       resultados em results/e2e_direct.{json,md}; com --base-dir, results/e2e_direct_<nome>.{json,md}
 *   --base-dir: um modelo real como base (T-805), por exemplo o Qwen2.5-0.5B de $MODEL_GATE_DATA;
 *   sem ele, o modelo minúsculo dos testes do model_gate.
 */
const fs = require("node:fs");
const path = require("node:path");
const { modelDirDigest, packModelDir } = require("../scripts/model_store");
const { MODEL_GATE_DATA, SC, Stack, finish, newClient, sha } = require("./stack");

const KEEP = process.argv.includes("--keep");
// --serve: depois dos cenários, deixa a pilha no ar (para usar a web UI) até Ctrl+C.
const SERVE = process.argv.includes("--serve");
const BASE_DIR = (() => {
  const i = process.argv.indexOf("--base-dir");
  return i >= 0 ? path.resolve(process.argv[i + 1]) : null;
})();
const LABEL = BASE_DIR ? `_${path.basename(path.dirname(BASE_DIR)).replace(/[^A-Za-z0-9.-]+/g, "_")}` : "";
const stack = new Stack("e2e");
const state = stack.state;
const step = (name, fn) => stack.step(name, fn);
const log = (msg) => stack.log(msg);

// ------------------------------------------------------------------ roteiro

async function main() {
  const machine = stack.machine;
  // Antes de qualquer conexão: o spawnSync trava este processo, e uma conexão ociosa do cliente
  // seria fechada pelo servidor (keep-alive de 5 s) e reaproveitada depois ("other side closed").
  const baseDir = BASE_DIR || stack.makeTinyBase(path.join(state, "base"));
  const baseArchive = packModelDir(baseDir, path.join(state, "base.tar.gz"));
  const ipfsUrl = await step("IPFS em memória", () => stack.startIpfs());
  const chain = await step("hardhat node e implantação do contrato", () => stack.startChain());
  await step("CVM2 (builder, modo direto)", () => stack.startBuilder());
  await step("CVM de job (executor, modo direto)", () => stack.startExecutor());

  const battery = sha("T-304 pendente: compromisso provisório da parte secreta");
  // Pacote da bateria (T-807), se já montado no notebook (experiments.battery_pack); fica fora do git.
  const localPack = path.join(MODEL_GATE_DATA, "battery", "local_t807");
  if (fs.existsSync(path.join(localPack, "battery.json"))) {
    await step("pacote da bateria depositado pelo operador (judge_cli battery)", () =>
      stack.judgeCli(["battery", "--dir", localPack, "--source", "roteiro T-811"]));
  }
  const release = await step("liberar o Juiz atual na lista permitida (judge_cli allow)", () =>
    stack.judgeCli(["allow", "--battery-commitment", battery, "--evaluator-kind", "detector", "--note", "roteiro T-811"]));

  const cvmEnv = stack.cvmEnv();
  let cvm1 = await step("CVM1 (api-server)", () => stack.startCvm1("cvm1", cvmEnv));

  const who = await step("identidade com prova de trabalho (d = 12)", () => newClient(cvm1.api));
  const reg = who.reg;
  const signed = who.signed;
  const multipart = (name, filename, data) => who.multipart(name, filename, data, "roteiro T-811");

  const model = await step("depósito do modelo base (register-model)", () => {
    const m = multipart(BASE_DIR ? path.basename(path.dirname(BASE_DIR)) : "modelo minúsculo", "base.tar.gz", fs.readFileSync(baseArchive));
    return signed("/api/register-model", { body: m.body, contentType: m.contentType });
  });
  if (model.onChainAsset.contentHash !== `0x${modelDirDigest(baseDir).digest}`) throw new Error("contentHash do base não é o digest do diretório");

  const csv = "prompt,response\nWhat is the capital of France?,Paris\nName a primary color.,Blue\nHow many legs does a spider have?,Eight\n";
  const dataset = await step("dataset (register-dataset)", () => {
    const m = multipart("dataset benigno", "dataset.csv", Buffer.from(csv));
    return signed("/api/register-dataset", { body: m.body, contentType: m.contentType });
  });
  const app = await step("aplicação de fine-tuning simulado (register-application, build no CVM2)", () => {
    const m = multipart("fine-tuning simulado", "application.py", fs.readFileSync(path.join(__dirname, "fine_tune_app.py")));
    return signed("/api/register-application", { body: m.body, contentType: m.contentType });
  });
  await step("compra de acesso (purchase-access)", async () => {
    const r = await fetch(`${cvm1.api}/api/purchase-access`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ datasetId: dataset.assetId, applicationId: app.assetId }) });
    if (!r.ok) throw new Error(await r.text());
  });

  const refDir = path.join(state, "reference");
  fs.mkdirSync(refDir);
  fs.writeFileSync(path.join(refDir, "reference.json"), JSON.stringify({ placeholder: "T-312 roda na nuvem; esta referência é só do roteiro" }));
  await step("referência do pai depositada pelo operador (judge_cli reference)", () =>
    stack.judgeCli(["reference", "--parent", model.assetId, "--dir", refDir, "--source", "roteiro T-811 (placeholder)"]));

  const job = { datasetId: dataset.assetId, applicationId: app.assetId, parentModelId: model.assetId };
  const balance = who.balance;
  const scenarios = {};

  scenarios.A = await step("A · fine-tuning + Juiz real (model_gate)", () => signed("/api/run-from-cids", { json: job }));
  scenarios.A.balanceAfter = await balance();

  // B e C: a CVM1 reinicia com o Juiz SIMULADO, numa lista permitida só de teste.
  stack.stop(cvm1.p);
  const simHash = sha("juiz simulado do roteiro T-811");
  const simAllow = path.join(state, "judge_allowlist_simulado.json");
  fs.writeFileSync(simAllow, JSON.stringify({ schema: "dnat.judge-allowlist.v1", judges: [{ ...release, judgeHash: simHash, note: "SIMULADO" }] }));
  const simEnv = { ...cvmEnv, DNAT_JUDGE_ALLOWLIST: simAllow, DNAT_JUDGE_CMD: JSON.stringify([process.execPath, path.join(__dirname, "simulated_judge.js")]), SIMULATED_JUDGE_HASH: simHash };
  cvm1 = await stack.startCvm1("cvm1-simulado", { ...simEnv, SIMULATED_JUDGE_STATE: "aprovado" });
  who.useApi(cvm1.api);
  scenarios.B = await step("B · fine-tuning + Juiz SIMULADO aprovando", () => signed("/api/run-from-cids", { json: job }));
  scenarios.B.balanceAfter = await balance();
  stack.stop(cvm1.p);
  cvm1 = await stack.startCvm1("cvm1-simulado-reprova", { ...simEnv, SIMULATED_JUDGE_STATE: "reprovado" });
  who.useApi(cvm1.api);
  scenarios.C = await step("C · fine-tuning + Juiz SIMULADO reprovando", () => signed("/api/run-from-cids", { json: job }));
  scenarios.C.balanceAfter = await balance();

  const onChain = {};
  for (const k of ["B", "C"]) {
    const id = scenarios[k].judge?.assetId;
    if (!id) continue;
    const a = await chain.contract.getAsset(BigInt(id));
    const d = await chain.contract.getDerivative(BigInt(id));
    onChain[k] = { assetId: id, active: a.active, usable: await chain.contract.isDerivativeUsable(BigInt(id)), verdict: Number(d.verdict), verdictHash: d.verdictHash, judgeHash: d.judgeHash };
  }

  const summary = (s) => ({
    exitCode: s.exitCode,
    metrics: s.result?.metrics ?? null,
    derivative: s.metadata?.derivative ?? null,
    judge: s.judge,
    quota: s.quota,
    balanceAfter: s.balanceAfter,
  });
  const result = {
    note: "Verificação de funcionamento (T-811), não é dado do artigo. B e C usam um Juiz SIMULADO.",
    machine,
    judgeRelease: release,
    base: { dir: BASE_DIR ? path.basename(path.dirname(BASE_DIR)) : "minúsculo (tests/tiny.py)", digest: modelDirDigest(baseDir).digest,
      archiveBytes: fs.statSync(baseArchive).size },
    assets: { model: model.assetId, dataset: dataset.assetId, application: app.assetId },
    identity: { id: reg.record.id, difficulty: reg.difficulty, proofSeconds: reg.proofSeconds },
    scenarios: { A: summary(scenarios.A), B: summary(scenarios.B), C: summary(scenarios.C) },
    onChain,
    timings: stack.timings,
  };

  const checks = [
    // A falha tem de vir do job do Juiz (prereg sem valores), não da custódia antes dele.
    ["A: Juiz real termina em falha (prereg sem valores, T-606)", scenarios.A.judge?.outcome === "failure" && scenarios.A.judge?.alert === "judge_failure"],
    ["A: reserva devolvida (saldo 20)", scenarios.A.balanceAfter === 20],
    ["B: aprovado, derivado usável no contrato", scenarios.B.judge?.outcome === "approved" && onChain.B?.usable === true],
    ["B: cota 1 (saldo 19)", scenarios.B.balanceAfter === 19],
    ["C: reprovado, derivado inativo", scenarios.C.judge?.outcome === "rejected" && onChain.C?.active === false],
    ["C: cota 5 (saldo 14)", scenarios.C.balanceAfter === 14],
  ];
  result.checks = checks.map(([name, ok]) => ({ name, ok }));
  writeResults(result);
  for (const [name, ok] of checks) log(`${ok ? "ok  " : "FALHOU"} ${name}`);
  if (SERVE) {
    log(`pilha no ar: web UI em ${cvm1.api}/ (Juiz SIMULADO reprovando, modelo base ${model.assetId}); Ctrl+C encerra`);
    await new Promise((resolve) => {
      process.once("SIGINT", resolve);
      process.once("SIGTERM", resolve);
    });
  }
  return checks.every(([, ok]) => ok) ? 0 : 1;
}

function writeResults(r) {
  const dir = path.join(SC, "results");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, `e2e_direct${LABEL}.json`), JSON.stringify(r, null, 2) + "\n");
  const rows = r.timings.map((t) => `| ${t.step} | ${t.seconds.toFixed(2)} |`).join("\n");
  const sc = (k) => {
    const s = r.scenarios[k];
    return `| ${k} | ${s.exitCode} | ${s.derivative?.status ?? "-"} | ${s.judge?.outcome ?? "-"} | ${s.judge?.alert ?? "-"} | ${s.judge?.assetId ?? "-"} | ${s.balanceAfter} |`;
  };
  const md = `# Fluxo inteiro no modo direto (T-811)

${r.note}

Base: ${r.base.dir} · ${(r.base.archiveBytes / 1e6).toFixed(1)} MB empacotado · digest \`${r.base.digest.slice(0, 12)}\`

Máquina: ${r.machine.cpuModel} · ${r.machine.logicalCpus} CPUs lógicas · ${r.machine.platform} · Node ${r.machine.node} · ${r.machine.startedAtUtc}

Juiz liberado: \`${r.judgeRelease.judgeHash}\` · prereg \`${r.judgeRelease.preregSha256}\`

## Desfechos

| Cenário | Saída do job | Derivado | Veredito | Alerta | Asset | Saldo depois |
|---|---|---|---|---|---|---|
${sc("A")}
${sc("B")}
${sc("C")}

A: Juiz real. B e C: Juiz SIMULADO (e2e/simulated_judge.js), só para exercitar recibo e cota.

## Conferências

${r.checks.map((c) => `- ${c.ok ? "✅" : "❌"} ${c.name}`).join("\n")}

## Tempo por etapa (s)

| Etapa | s |
|---|---|
${rows}
`;
  fs.writeFileSync(path.join(dir, `e2e_direct${LABEL}.md`), md);
}

finish(stack, main(), { keep: KEEP });
