#!/usr/bin/env node
/**
 * Ensaio local do Teste 8 com o Juiz real (T-814; parte local da T-813). VERIFICAÇÃO DE
 * FUNCIONAMENTO: avaliador e prereg de fumaça, n pequeno; não é dado do artigo.
 *
 * Sobre a pilha do modo direto (e2e/stack.js), com o Qwen2.5-0.5B real como base:
 *   1. o operador deposita o pacote da bateria e libera o Juiz atual com o prereg de fumaça
 *      (model_gate/experiments/judge_local_prereg.yaml) e o avaliador detector;
 *   2. o dono deposita o base (register-model); o operador deposita a referência do pai medida
 *      com o mesmo desenho e avaliador (python -m model_gate.reference, T-312 na nuvem);
 *   3. o usuário roda duas aplicações de fine-tuning pelo run-from-cids com o modelo pai:
 *        abliteração  e2e/abliterate_app.py (direção de recusa do pai embutida)  → reprovado
 *        ajuste leve  e2e/fine_tune_app.py (bits trocados num tensor)          → sem veto
 *      e o Juiz real julga cada derivado como segundo job;
 *   4. confere no contrato: o reprovado fica retido e o dono não o reativa; o operador revoga o
 *      outro, que deixa de ser usável e também não volta; a cota acerta (5 e 2, ou 1).
 *
 *   node e2e/teste8.js [--base-dir DIR] [--reference-dir DIR] [--keep]
 *   (resultados em results/T-814_teste8_local.{json,md})
 */
const fs = require("node:fs");
const path = require("node:path");
const { modelDirDigest, packModelDir } = require("../scripts/model_store");
const { MODEL_GATE, MODEL_GATE_DATA, SC, Stack, finish, newClient, sha } = require("./stack");

const arg = (name, fallback) => {
  const i = process.argv.indexOf(name);
  return i >= 0 ? path.resolve(process.argv[i + 1]) : fallback;
};
const KEEP = process.argv.includes("--keep");
const BASE_DIR = arg("--base-dir", path.join(MODEL_GATE_DATA, "models", "Qwen__Qwen2.5-0.5B-Instruct", "7ae557604adf67be50417f59c2c2f167def9a775"));
const PREREG = path.join(MODEL_GATE, "experiments", "judge_local_prereg.yaml");
const BATTERY = path.join(MODEL_GATE_DATA, "battery", "local_t807");
const REFERENCE_DIR = arg("--reference-dir", null);
const DIRECTION = path.join(MODEL_GATE_DATA, "references", "base_05b61d72bec3", "refusal_dirs.safetensors");
const DIRECTION_LAYER = 12; // a mesma da receita de fumaça d12
const OUT = path.join(SC, "results", "T-814_teste8_local");
const stack = new Stack("teste8");

/** Linha `layer` do tensor dirs [L, d] F32 do pacote da direção (safetensors lido à mão). */
function directionRow(file, layer) {
  const b = fs.readFileSync(file);
  const n = Number(b.readBigUInt64LE(0));
  const header = JSON.parse(b.subarray(8, 8 + n).toString("utf8"));
  const m = header.dirs;
  if (m.dtype !== "F32") throw new Error(`dirs em ${m.dtype}`);
  const d = m.shape[1];
  const start = 8 + n + m.data_offsets[0] + layer * d * 4;
  return b.subarray(start, start + d * 4);
}

/** Referência medida para este base e este desenho: a dada ou a da T-807 com o mesmo prereg e pacote. */
function findReference(baseDigest) {
  const candidates = REFERENCE_DIR ? [REFERENCE_DIR] : fs.readdirSync(path.join(MODEL_GATE_DATA, "references"))
    .filter((d) => d.startsWith("t807_detector_")).map((d) => path.join(MODEL_GATE_DATA, "references", d));
  for (const dir of candidates) {
    const f = path.join(dir, "reference.json");
    if (fs.existsSync(f) && JSON.parse(fs.readFileSync(f, "utf8")).base_digest === baseDigest) return dir;
  }
  throw new Error("sem referência medida para este base: rode `uv run python -m experiments.judge_local` no model_gate");
}

async function main() {
  const baseDigest = modelDirDigest(BASE_DIR).digest;
  const refDir = findReference(baseDigest);
  const baseArchive = await stack.step("empacotar o base", () => packModelDir(BASE_DIR, path.join(stack.state, "base.tar.gz")));
  const appAbl = path.join(stack.state, "abliterate_app.py");
  fs.writeFileSync(appAbl, fs.readFileSync(path.join(__dirname, "abliterate_app.py"), "utf8")
    .replace("__DIRECTION_B64__", directionRow(DIRECTION, DIRECTION_LAYER).toString("base64")));

  await stack.step("IPFS em disco", () => stack.startIpfs());
  const chain = await stack.step("hardhat node e implantação do contrato", () => stack.startChain());
  await stack.step("CVM2 (builder, modo direto)", () => stack.startBuilder());
  await stack.step("CVM de job (executor, modo direto)", () => stack.startExecutor());
  await stack.step("pacote da bateria (judge_cli battery)", () => stack.judgeCli(["battery", "--dir", BATTERY, "--source", "T-814"]));
  const release = await stack.step("liberar o Juiz com o prereg de fumaça (judge_cli allow)", () =>
    stack.judgeCli(["allow", "--battery-commitment", sha("T-304 pendente"), "--prereg", PREREG, "--evaluator-kind", "detector", "--note", "T-814 fumaça"]));
  const cvm1 = await stack.step("CVM1 (api-server)", () => stack.startCvm1("cvm1", stack.cvmEnv()));
  const who = await stack.step("identidade com prova de trabalho", () => newClient(cvm1.api));

  const model = await stack.step("depósito do base (register-model)", () => {
    const m = who.multipart("Qwen2.5-0.5B-Instruct", "base.tar.gz", fs.readFileSync(baseArchive), "T-814");
    return who.signed("/api/register-model", { body: m.body, contentType: m.contentType });
  });
  if (model.onChainAsset.contentHash !== `0x${baseDigest}`) throw new Error("contentHash do base não é o digest do diretório");
  await stack.step("referência do pai (judge_cli reference)", () =>
    stack.judgeCli(["reference", "--parent", model.assetId, "--dir", refDir, "--source", `T-814: ${path.basename(refDir)}`]));

  const csv = "prompt,response\nWhat is the capital of France?,Paris\nName a primary color.,Blue\n";
  const dataset = await stack.step("dataset (register-dataset)", () => {
    const m = who.multipart("dataset benigno", "dataset.csv", Buffer.from(csv), "T-814");
    return who.signed("/api/register-dataset", { body: m.body, contentType: m.contentType });
  });
  const apps = {};
  for (const [key, file, name] of [["abliteracao", appAbl, "abliteração (camada 12)"], ["ajuste", path.join(__dirname, "fine_tune_app.py"), "ajuste leve"]]) {
    apps[key] = await stack.step(`aplicação: ${name} (register-application)`, () => {
      const m = who.multipart(name, "application.py", fs.readFileSync(file), "T-814");
      return who.signed("/api/register-application", { body: m.body, contentType: m.contentType });
    });
    await fetch(`${cvm1.api}/api/purchase-access`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ datasetId: dataset.assetId, applicationId: apps[key].assetId }) });
  }

  const runs = {};
  for (const key of ["abliteracao", "ajuste"]) {
    const res = await stack.step(`${key}: fine-tuning + Juiz real`, () =>
      who.signed("/api/run-from-cids", { json: { datasetId: dataset.assetId, applicationId: apps[key].assetId, parentModelId: model.assetId } }));
    const rec = JSON.parse(fs.readFileSync(path.join(stack.state, "derivatives.json"), "utf8")).derivatives[res.metadata.executionId] || {};
    runs[key] = { exitCode: res.exitCode, judge: res.judge, balanceAfter: await who.balance(), digest: rec.digest,
      rule: rec.rule ?? null, reasons: rec.reasons ?? [], judgeAlert: rec.judgeAlert ?? null, judgeError: rec.judgeError ?? null };
    stack.log(`${key}: ${JSON.stringify(runs[key])}`);
  }

  // Contrato (T-704, T-705): retenção, reativação negada, revogação pelo operador.
  const c = chain.contract;
  const reverts = async (p) => {
    try {
      await (await p).wait();
      return null;
    } catch (e) {
      return e.shortMessage || e.reason || e.message;
    }
  };
  const contract = {};
  const ablId = runs.abliteracao.judge?.assetId;
  if (ablId) {
    contract.abliteracao = {
      active: (await c.getAsset(BigInt(ablId))).active,
      usable: await c.isDerivativeUsable(BigInt(ablId)),
      reactivate: await reverts(c.updateAsset(BigInt(ablId), 0n, true)),
    };
  }
  const ajId = runs.ajuste.judge?.assetId;
  if (ajId) {
    const before = await c.isDerivativeUsable(BigInt(ajId));
    const revoke = await reverts(c.revokeDerivative(BigInt(ajId), "T-814: revogação pelo operador"));
    contract.ajuste = { usableBefore: before, revoke, usableAfter: await c.isDerivativeUsable(BigInt(ajId)),
      reactivate: await reverts(c.updateAsset(BigInt(ajId), 0n, true)) };
  }

  const ajusteCost = runs.ajuste.judge?.outcome === "approved" ? 1 : 2;
  const checks = [
    ["abliteração reprovada pelo Juiz real (regra 1)", runs.abliteracao.judge?.outcome === "rejected" && runs.abliteracao.rule === "1"],
    ["abliteração retida: inativa e não usável", contract.abliteracao?.active === false && contract.abliteracao?.usable === false],
    ["o dono não reativa o reprovado", typeof contract.abliteracao?.reactivate === "string"],
    ["ajuste leve sem veto (aprovado ou inconclusivo, recibo gravado)", ["approved", "inconclusive"].includes(runs.ajuste.judge?.outcome)],
    ["o operador revoga o ajuste; deixa de ser usável e não volta",
      contract.ajuste?.revoke === null && contract.ajuste?.usableAfter === false && typeof contract.ajuste?.reactivate === "string"],
    [`cota: 20 − 5 − ${ajusteCost} = ${20 - 5 - ajusteCost}`, runs.ajuste.balanceAfter === 20 - 5 - ajusteCost],
  ];
  const result = {
    note: "Ensaio local do Teste 8 (T-814) com o Juiz real; avaliador e prereg de FUMAÇA. Não é dado do artigo.",
    machine: stack.machine, release, base: { dir: BASE_DIR, digest: baseDigest, archiveBytes: fs.statSync(baseArchive).size },
    reference: path.basename(refDir), runs, contract, timings: stack.timings,
    checks: checks.map(([name, ok]) => ({ name, ok })),
  };
  writeResults(result);
  for (const [name, ok] of checks) stack.log(`${ok ? "ok  " : "FALHOU"} ${name}`);
  return checks.every(([, ok]) => ok) ? 0 : 1;
}

function writeResults(r) {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(`${OUT}.json`, JSON.stringify(r, null, 2) + "\n");
  const run = (k) => {
    const x = r.runs[k];
    return `| ${k} | ${x.judge?.outcome ?? "-"} | ${x.rule ?? "-"} | ${(x.reasons || []).join(", ") || x.judgeAlert || "-"} | ${x.judge?.assetId ?? "-"} | ${x.balanceAfter} |`;
  };
  const md = `# Ensaio local do Teste 8 (T-814)

${r.note}

Base: Qwen2.5-0.5B-Instruct · ${(r.base.archiveBytes / 1e6).toFixed(0)} MB empacotado · digest \`${r.base.digest.slice(0, 12)}\` · referência \`${r.reference}\`

Juiz \`${r.release.judgeHash.slice(0, 12)}\` · prereg \`${r.release.preregSha256.slice(0, 12)}\` · avaliador ${r.release.evaluatorKind}

Máquina: ${r.machine.cpuModel} · ${r.machine.logicalCpus} CPUs lógicas · Node ${r.machine.node} · ${r.machine.startedAtUtc}

## Vereditos

| Derivado | Veredito | Regra | Motivos | Asset | Saldo depois |
|---|---|---|---|---|---|
${run("abliteracao")}
${run("ajuste")}

## Contrato

\`\`\`json
${JSON.stringify(r.contract, null, 2)}
\`\`\`

## Conferências

${r.checks.map((c) => `- ${c.ok ? "✅" : "❌"} ${c.name}`).join("\n")}

## Tempo por etapa (s)

| Etapa | s |
|---|---|
${r.timings.map((t) => `| ${t.step} | ${t.seconds.toFixed(1)} |`).join("\n")}
`;
  fs.writeFileSync(`${OUT}.md`, md);
}

finish(stack, main(), { keep: KEEP });
