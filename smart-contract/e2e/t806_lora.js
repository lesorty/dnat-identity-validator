#!/usr/bin/env node
/**
 * Fine-tuning LoRA de verdade numa CVM de job de uso único (T-806), na pilha local. Verificação de
 * funcionamento: os tempos daqui NÃO são dado do artigo (todo dado do artigo sai da nuvem).
 *
 * A primeira metade do fluxo do DNAT, com treino real:
 *   - a aplicação é o script único da T-901 (model_gate/experiments/population/lora.py), embutido
 *     verbatim em e2e/lora_app_template.py, com torch (CPU), transformers e peft nas versões do
 *     uv.lock do model_gate, empacotados pelo builder da pilha direta (container dnat-builder);
 *   - o base é o Qwen2.5-0.5B-Instruct de $MODEL_GATE_DATA, depositado pelo dono (register-model);
 *   - o job roda numa CVM de uso único (DNAT_JOB_VM_PROVIDER=docker, T-801), com 8 GB de memória,
 *     rede entra-só, destruída depois;
 *   - o derivado (só o adaptador) volta à CVM1 e fica retido, cifrado no IPFS, com digest.
 *
 * Sem referência do pai nem Juiz liberado: o segundo job (Juiz) não tem como rodar, e a reserva da
 * cota volta (o Juiz real com LoRA já foi verificado na T-807 e na T-814).
 *
 *   node e2e/t806_lora.js [--keep] [--steps N]      resultado em results/T-806_lora_uso_unico.{json,md}
 *
 * Pré-requisitos: a pilha direta no ar (docker compose -f docker/direct.compose.yaml up -d), com a
 * rede dnat-runtime e as imagens dnat-executor-direct e dnat-builder-direct.
 */
const fs = require("node:fs");
const path = require("node:path");
const { dockerRequest } = require("../scripts/job_vm");
const { modelDirDigest, packModelDir } = require("../scripts/model_store");
const { APP_ARTIFACT_ENVELOPE_MAGIC } = require("../scripts/asset_envelope");
const { MODEL_GATE, MODEL_GATE_DATA, SC, Stack, finish, newClient } = require("./stack");

const KEEP = process.argv.includes("--keep");
const STEPS = (() => {
  const i = process.argv.indexOf("--steps");
  return i >= 0 ? Number(process.argv[i + 1]) : 10;
})();
const BASE_DIR = path.join(MODEL_GATE_DATA, "models", "Qwen__Qwen2.5-0.5B-Instruct", "7ae557604adf67be50417f59c2c2f167def9a775");
// Do cache de wheels do builder (pré-carregado com pip download): a mesma wheel CPU do uv.lock do model_gate.
const TORCH = "torch==2.15.0+cpu";
const DEPENDENCIES = [TORCH, "transformers==5.22.1", "peft==0.21.2", "accelerate==1.15.0", "safetensors==0.8.0", "tokenizers==0.23.3", "numpy==2.5.4"];
const stack = new Stack("t806");

/** application.py: o template com o lora.py da T-901 e os módulos de que ele depende, verbatim. */
function buildApplication(recipe) {
  const src = (rel) => fs.readFileSync(path.join(MODEL_GATE, rel), "utf8");
  const sources = {
    "model_gate/__init__.py": "",
    "model_gate/io/__init__.py": "",
    "model_gate/io/digest.py": src("src/model_gate/io/digest.py"),
    "model_gate/io/generate.py": src("src/model_gate/io/generate.py"),
    "model_gate/io/load.py": src("src/model_gate/io/load.py"),
    "experiments/__init__.py": "",
    "experiments/population/__init__.py": "",
    "experiments/population/lora.py": src("experiments/population/lora.py"),
  };
  const template = fs.readFileSync(path.join(__dirname, "lora_app_template.py"), "utf8");
  return template.replace("__SOURCES__", JSON.stringify(sources)).replace("__RECIPE__", JSON.stringify(recipe));
}

async function containerIp(name, network = "dnat-runtime") {
  const info = await dockerRequest("/var/run/docker.sock", "GET", `/containers/${name}/json`);
  const ip = info.NetworkSettings?.Networks?.[network]?.IPAddress;
  if (!ip) throw new Error(`${name} sem endereço na rede ${network}: suba a pilha direta`);
  return ip;
}

async function main() {
  const state = stack.state;
  const baseArchive = packModelDir(BASE_DIR, path.join(state, "base.tar.gz"));
  const appFile = path.join(state, "application.py");
  fs.writeFileSync(appFile, buildApplication({ name: "t806-aritmetica", steps: STEPS, seed: 0 }));

  await stack.step("IPFS em disco", () => stack.startIpfs());
  const chain = await stack.step("hardhat node e implantação do contrato", () => stack.startChain());
  const builderUrl = `http://${await containerIp("dnat-builder")}:5100`;
  const cvm1 = await stack.step("CVM1 (api-server) com CVMs de job de uso único", () => stack.startCvm1("cvm1", stack.cvmEnv({
    BUILDER_URL: builderUrl,
    DNAT_JOB_VM_PROVIDER: "docker",
    DNAT_JOB_VM_POOL: "0",
    DNAT_JOB_VM_MEMORY: process.env.DNAT_JOB_VM_MEMORY || "8g",
    DNAT_JOB_VM_ENV: JSON.stringify({ DNAT_TRAIN_THREADS: "4", DNAT_JOB_TIMEOUT_MAX_SECONDS: "3600" }),
    DNAT_JOB_TIMEOUT_SECONDS: "3000",
  })));

  const who = await stack.step("identidade com prova de trabalho (d = 12)", () => newClient(cvm1.api));
  const model = await stack.step("depósito do Qwen2.5-0.5B (register-model)", () => {
    const m = who.multipart("Qwen2.5-0.5B-Instruct", "base.tar.gz", fs.readFileSync(baseArchive), "T-806");
    return who.signed("/api/register-model", { body: m.body, contentType: m.contentType });
  });
  // Dados benignos sintéticos da fumaça da T-901 (somas), 32 exemplos.
  const rows = [];
  let seed = 901;
  const rnd = () => ((seed = (seed * 1103515245 + 12345) % 2 ** 31) / 2 ** 31);
  for (let i = 0; i < 32; i++) {
    const a = 10 + Math.floor(rnd() * 90);
    const b = 10 + Math.floor(rnd() * 90);
    rows.push(`What is ${a} + ${b}?,${a} + ${b} = ${a + b}.`);
  }
  const dataset = await stack.step("dataset benigno (register-dataset)", () => {
    const m = who.multipart("somas", "dataset.csv", Buffer.from(`prompt,response\n${rows.join("\n")}\n`), "T-806");
    return who.signed("/api/register-dataset", { body: m.body, contentType: m.contentType });
  });
  const app = await stack.step("aplicação LoRA (register-application: builder com torch, transformers e peft)", () => {
    const client = require("../scripts/identity_client");
    const m = client.buildMultipart(
      { "manifest.name": "LoRA T-901", "manifest.description": "T-806", "manifest.dependencies": JSON.stringify(DEPENDENCIES) },
      { file: { filename: "application.py", data: fs.readFileSync(appFile) } },
    );
    return who.signed("/api/register-application", { body: m.body, contentType: m.contentType });
  });
  await stack.step("compra de acesso (purchase-access)", async () => {
    const r = await fetch(`${cvm1.api}/api/purchase-access`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ datasetId: dataset.assetId, applicationId: app.assetId }) });
    if (!r.ok) throw new Error(await r.text());
  });
  const run = await stack.step(`fine-tuning LoRA (${STEPS} passos) numa CVM de uso único`, () =>
    who.signed("/api/run-from-cids", { json: { datasetId: dataset.assetId, applicationId: app.assetId, parentModelId: model.assetId } }));

  const der = run.metadata?.derivative || {};
  const derivatives = JSON.parse(fs.readFileSync(path.join(state, "derivatives.json"), "utf8"));
  const record = Object.values(derivatives.derivatives || derivatives).find((d) => d && d.executionId === run.metadata?.executionId) || null;
  const appAsset = await chain.contract.getAsset(BigInt(app.assetId));
  const ipfsFile = (uri) => path.join(state, "ipfs", String(uri).replace(/^ipfs:\/\//, ""));
  const head = (uri, n = 8) => {
    const fd = fs.openSync(ipfsFile(uri), "r");
    const b = Buffer.alloc(n);
    fs.readSync(fd, b, 0, n, 0);
    fs.closeSync(fd);
    return b;
  };
  const appEnvelopeBytes = fs.statSync(ipfsFile(appAsset.encryptedUri)).size;
  const derivativeCipher = record?.encryptedUri ? head(record.encryptedUri) : null;
  const derivativeBytes = record?.encryptedUri ? fs.statSync(ipfsFile(record.encryptedUri)).size : 0;
  const vm = run.jobVm || {};

  const result = {
    note: "Verificação de funcionamento (T-806), não é dado do artigo.",
    machine: stack.machine,
    base: { name: "Qwen2.5-0.5B-Instruct", digest: modelDirDigest(BASE_DIR).digest },
    recipe: { steps: STEPS, seed: 0, examples: rows.length, dependencies: DEPENDENCIES },
    application: { assetId: app.assetId, envelopeBytes: appEnvelopeBytes },
    job: { exitCode: run.exitCode, metrics: run.result?.metrics ?? null, timings: run.metadata?.timeouts ?? null },
    derivative: { status: der.status ?? null, digest: record?.digest ?? null, encryptedUri: record?.encryptedUri ?? null,
      envelopeBytes: derivativeBytes, judge: run.judge, quota: run.quota },
    jobVm: vm,
    timings: stack.timings,
  };
  const checks = [
    ["o job de treino termina com sucesso e devolve só as métricas permitidas", run.exitCode === 0 && run.result?.metrics?.steps === STEPS],
    ["derivado retido, com digest", Boolean(record?.digest) && /retained|rejected|released/.test(String(record?.status || der.status))],
    ["no IPFS o derivado só existe cifrado (envelope DNATENC2)", derivativeCipher?.equals(APP_ARTIFACT_ENVELOPE_MAGIC) === true],
    ["CVM de uso único destruída depois do job, com a memória de pico registrada", vm.singleUse === true && Boolean(vm.destroyedAt) && (vm.cgroupPeakBytes || 0) > 0],
    ["sem Juiz liberado nem referência: a reserva da cota volta (saldo 20)", run.quota?.balance === 20],
  ];
  result.checks = checks.map(([name, ok]) => ({ name, ok }));
  const dir = path.join(SC, "results");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "T-806_lora_uso_unico.json"), JSON.stringify(result, null, 2) + "\n");
  const mb = (b) => (b / 2 ** 20).toFixed(0);
  fs.writeFileSync(path.join(dir, "T-806_lora_uso_unico.md"), `# Fine-tuning LoRA numa CVM de uso único (T-806)

${result.note}

Base: Qwen2.5-0.5B-Instruct \`${result.base.digest.slice(0, 12)}\` · ${STEPS} passos, 32 exemplos, script da T-901 · máquina: ${stack.machine.cpuModel}, ${stack.machine.logicalCpus} CPUs

| Item | Valor |
|---|---|
| Aplicação cifrada no IPFS | ${mb(appEnvelopeBytes)} MB |
| Perda final / passos | ${run.result?.metrics?.loss ?? "-"} / ${run.result?.metrics?.steps ?? "-"} |
| Tempo do script (train_seconds) | ${run.result?.metrics?.train_seconds ?? "-"} s |
| Derivado (adaptador) cifrado no IPFS | ${mb(derivativeBytes)} MB · digest \`${String(record?.digest || "-").slice(0, 12)}\` |
| CVM de job | ${vm.id ?? "-"} · subida ${((vm.bootMs || 0) / 1000).toFixed(1)} s · pico do cgroup (com cache de página) ${mb(vm.cgroupPeakBytes || 0)} MB · pico RSS ${mb(vm.peakRssBytes || 0)} MB · destruída ${vm.destroyedAt ? "sim" : "NÃO"} |

## Conferências

${result.checks.map((c) => `- ${c.ok ? "✅" : "❌"} ${c.name}`).join("\n")}

## Tempo por etapa (s)

| Etapa | s |
|---|---|
${stack.timings.map((t) => `| ${t.step} | ${t.seconds.toFixed(1)} |`).join("\n")}
`);
  for (const [name, ok] of checks) stack.log(`${ok ? "ok  " : "FALHOU"} ${name}`);
  return checks.every(([, ok]) => ok) ? 0 : 1;
}

finish(stack, main(), { keep: KEEP });
