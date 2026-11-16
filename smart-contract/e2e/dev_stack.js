#!/usr/bin/env node
/**
 * Pilha de desenvolvimento já semeada, para usar a interface e os roteiros sem passos manuais.
 * VERIFICAÇÃO DE FUNCIONAMENTO: Juiz real com o prereg e o avaliador de FUMAÇA; nada daqui é dado
 * do artigo.
 *
 * Sobe IPFS, cadeia, builder, executor e CVM1 (e2e/stack.js) e faz tudo o que o operador e um dono
 * fariam antes do primeiro job:
 *   - pacote da bateria (judge_cli battery) e o Juiz atual liberado com o prereg de fumaça e o
 *     avaliador detector (judge_cli allow);
 *   - o base depositado (register-model) e a referência do pai já medida (judge_cli reference);
 *   - um dataset benigno e duas receitas de treino: "ajuste leve" (sem veto) e "abliteração
 *     (camada 12)" (reprovada pelo Juiz real);
 *   - acesso liberado aos dois pares, e uma identidade com o arquivo de chave salvo.
 * Depois fica no ar até Ctrl+C, com a interface em http://localhost:PORTA/.
 *
 *   node e2e/dev_stack.js [--port 3002] [--tiny] [--keep]
 *     --tiny  base minúsculo, sem referência nem Juiz que julgue: só o fluxo, em segundos
 *     padrão  Qwen2.5-0.5B de $MODEL_GATE_DATA e a referência da T-807 (depósito em ~2 min; cada
 *             job de treino + Juiz leva alguns minutos)
 *     --keep  mantém o estado em /tmp ao sair
 *
 * O estado da pilha (URL, identidade, ids) fica em smart-contract/.dev_stack.json enquanto ela roda.
 */
const fs = require("node:fs");
const path = require("node:path");
const { modelDirDigest, packModelDir } = require("../scripts/model_store");
const { MODEL_GATE, MODEL_GATE_DATA, SC, Stack, newClient, sha } = require("./stack");

const argv = process.argv.slice(2);
const opt = (name, fallback) => {
  const i = argv.indexOf(name);
  return i >= 0 ? argv[i + 1] : fallback;
};
const PORT = Number(opt("--port", process.env.DEV_PORT || 3002));
const KEEP = argv.includes("--keep");
const QWEN = path.join(MODEL_GATE_DATA, "models", "Qwen__Qwen2.5-0.5B-Instruct", "7ae557604adf67be50417f59c2c2f167def9a775");
const PREREG = path.join(MODEL_GATE, "experiments", "judge_local_prereg.yaml");
const BATTERY = path.join(MODEL_GATE_DATA, "battery", "local_t807");
const DIRECTION = path.join(MODEL_GATE_DATA, "references", "base_05b61d72bec3", "refusal_dirs.safetensors");
const STATUS = path.join(SC, ".dev_stack.json");
const OPERATOR_TOKEN = process.env.DNAT_OPERATOR_TOKEN || "dev-operator";
const stack = new Stack("dev");

/** Linha `layer` do tensor dirs [L, d] F32 do pacote da direção (o mesmo do e2e/teste8.js). */
function directionRow(file, layer) {
  const b = fs.readFileSync(file);
  const n = Number(b.readBigUInt64LE(0));
  const m = JSON.parse(b.subarray(8, 8 + n).toString("utf8")).dirs;
  const d = m.shape[1];
  const start = 8 + n + m.data_offsets[0] + layer * d * 4;
  return b.subarray(start, start + d * 4);
}

function findReference(baseDigest) {
  const root = path.join(MODEL_GATE_DATA, "references");
  for (const d of fs.existsSync(root) ? fs.readdirSync(root).filter((x) => x.startsWith("t807_detector_")) : []) {
    const f = path.join(root, d, "reference.json");
    if (fs.existsSync(f) && JSON.parse(fs.readFileSync(f, "utf8")).base_digest === baseDigest) return path.join(root, d);
  }
  return null;
}

async function main() {
  const missing = [QWEN, BATTERY, DIRECTION].filter((p) => !fs.existsSync(p));
  const tiny = argv.includes("--tiny") || missing.length > 0;
  if (!argv.includes("--tiny") && missing.length) stack.log(`sem os dados do Qwen (${missing.join(", ")}): subindo com o base minúsculo`);
  const baseDir = tiny ? stack.makeTinyBase(path.join(stack.state, "base")) : QWEN;
  const baseDigest = modelDirDigest(baseDir).digest;
  const refDir = tiny ? null : findReference(baseDigest);
  const baseArchive = await stack.step("empacotar o base", () => packModelDir(baseDir, path.join(stack.state, "base.tar.gz")));

  await stack.step("IPFS em disco", () => stack.startIpfs());
  await stack.step("hardhat node e implantação do contrato", () => stack.startChain());
  await stack.step("builder (modo direto)", () => stack.startBuilder());
  await stack.step("executor (modo direto)", () => stack.startExecutor());
  if (fs.existsSync(BATTERY)) {
    await stack.step("pacote da bateria (judge_cli battery)", () => stack.judgeCli(["battery", "--dir", BATTERY, "--source", "dev"]));
    await stack.step("Juiz atual liberado com o prereg de fumaça (judge_cli allow)", () =>
      stack.judgeCli(["allow", "--battery-commitment", sha("T-304 pendente"), "--prereg", PREREG, "--evaluator-kind", "detector", "--note", "dev: fumaça"]));
  }
  const cvm1 = await stack.step(`CVM1 na porta ${PORT}`, () =>
    stack.startCvm1("cvm1", stack.cvmEnv({ DNAT_OPERATOR_TOKEN: OPERATOR_TOKEN }), PORT));
  const who = await stack.step("identidade com prova de trabalho", () => newClient(cvm1.api));
  const keyFile = path.join(stack.state, "identity.json");
  fs.writeFileSync(keyFile, JSON.stringify({ version: 1, ...who.identity, registeredAtUtc: who.reg.record.registeredAtUtc }, null, 2));

  const model = await stack.step("depósito do base (register-model)", () => {
    const m = who.multipart(tiny ? "Modelo minúsculo (dev)" : "Qwen2.5-0.5B-Instruct", "base.tar.gz", fs.readFileSync(baseArchive), "pilha de desenvolvimento");
    return who.signed("/api/register-model", { body: m.body, contentType: m.contentType });
  });
  if (refDir) {
    await stack.step("referência do pai (judge_cli reference)", () =>
      stack.judgeCli(["reference", "--parent", model.assetId, "--dir", refDir, "--source", `dev: ${path.basename(refDir)}`]));
  }
  const csv = "prompt,response\nWhat is the capital of France?,Paris\nName a primary color.,Blue\n";
  const dataset = await stack.step("dataset benigno (register-dataset)", () => {
    const m = who.multipart("dataset benigno (2 linhas)", "dataset.csv", Buffer.from(csv), "dev");
    return who.signed("/api/register-dataset", { body: m.body, contentType: m.contentType });
  });
  const recipes = [["ajuste leve (sem veto)", fs.readFileSync(path.join(__dirname, "fine_tune_app.py"), "utf8")]];
  if (!tiny && fs.existsSync(DIRECTION)) {
    recipes.push(["abliteração (camada 12, reprovada)", fs.readFileSync(path.join(__dirname, "abliterate_app.py"), "utf8")
      .replace("__DIRECTION_B64__", directionRow(DIRECTION, 12).toString("base64"))]);
  }
  const apps = [];
  for (const [name, src] of recipes) {
    const app = await stack.step(`receita: ${name}`, () => {
      const m = who.multipart(name, "application.py", Buffer.from(src), "dev");
      return who.signed("/api/register-application", { body: m.body, contentType: m.contentType });
    });
    await fetch(`${cvm1.api}/api/purchase-access`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ datasetId: dataset.assetId, applicationId: app.assetId }) });
    apps.push({ name, assetId: app.assetId });
  }

  const status = { url: `http://localhost:${PORT}/`, api: cvm1.api, pid: process.pid, state: stack.state, logs: stack.logs,
    base: { assetId: model.assetId, tiny, digest: baseDigest, reference: refDir ? path.basename(refDir) : null },
    dataset: dataset.assetId, recipes: apps, identityKey: keyFile, operatorToken: OPERATOR_TOKEN,
    judge: fs.existsSync(BATTERY) ? "real, prereg e avaliador de fumaça" : "nenhum liberado (sem pacote da bateria)" };
  fs.writeFileSync(STATUS, JSON.stringify(status, null, 2));
  stack.log("");
  stack.log(`pilha no ar: ${status.url}`);
  stack.log(`  base ${model.assetId} (${tiny ? "minúsculo, sem referência: o job termina sem veredito" : "Qwen2.5-0.5B, referência depositada"}), dataset ${dataset.assetId}, receitas ${apps.map((a) => `${a.assetId} ${a.name}`).join("; ")}`);
  stack.log(`  identidade semeada: ${keyFile} (importe na aba Identidade, ou crie uma nova)`);
  stack.log(`  operador: X-Operator-Token: ${OPERATOR_TOKEN}; logs em ${stack.logs}`);
  stack.log("  Ctrl+C encerra e apaga o estado (--keep mantém)");
  await new Promise((resolve) => {
    process.once("SIGINT", resolve);
    process.once("SIGTERM", resolve);
  });
}

main()
  .then(() => 0)
  .catch((e) => {
    console.error(`[dev] erro: ${e.stack || e.message}`);
    console.error(`[dev] logs em ${stack.logs}`);
    return 1;
  })
  .then((code) => {
    fs.rmSync(STATUS, { force: true });
    stack.close({ keep: KEEP, ok: code === 0 });
    setTimeout(() => process.exit(code), 500).unref();
  });
