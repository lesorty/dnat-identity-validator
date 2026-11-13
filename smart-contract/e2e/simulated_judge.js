#!/usr/bin/env node
/**
 * Juiz SIMULADO para o cenário B do roteiro de ponta a ponta (T-811). NÃO é o Juiz.
 *
 * Faz o papel do `python` que a CVM1 chama (DNAT_JUDGE_CMD): responde ao hash do pacote com
 * SIMULATED_JUDGE_HASH e, no job, confere que as entradas do manifesto existem e escreve um
 * verdict.json com o estado SIMULATED_JUDGE_STATE (padrão "aprovado") e os hashes do manifesto.
 * Serve só para exercitar o recibo no contrato e o acerto da cota enquanto os estágios reais do Juiz
 * (S1 com avaliador, S2/S3, utilidade) dependem da nuvem. O hash dele só entra numa lista permitida
 * de teste, nunca na da implantação.
 */
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const args = process.argv.slice(2);
if (args[1] === "model_gate.judge_package") {
  console.log(process.env.SIMULATED_JUDGE_HASH);
  process.exit(0);
}
const manifestPath = args[args.indexOf("--manifest") + 1];
const out = args[args.indexOf("--out") + 1];
const m = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
fs.mkdirSync(out, { recursive: true });
for (const spec of Object.values(m.inputs)) {
  if (!fs.existsSync(path.join(path.dirname(manifestPath), spec.path))) {
    fs.writeFileSync(path.join(out, "job_result.json"), JSON.stringify({ status: "failure", error: `missing ${spec.path}` }));
    process.exit(2);
  }
}
const i = m.inputs;
const state = process.env.SIMULATED_JUDGE_STATE || "aprovado";
const doc = {
  schema: "dnat.verdict.v1",
  state,
  rule: state === "aprovado" ? "-" : "1",
  reasons: state === "aprovado" ? [] : [{ code: "harm_veto" }],
  instruments: { s1: [], integrity: [], guards: [], second_line: [] },
  measures: { n_tests: 0, s1: [], signals: [], utility: null },
  thresholds: null,
  hashes: {
    parent: i.base.digest,
    parent_reference: i.parent_reference.digest,
    derivative: i.derivative.digest,
    judge: m.judge_hash,
    battery_commitment: m.battery_commitment,
    prereg: i.prereg.digest,
    dataset: i.dataset.digest,
    responses: crypto.createHash("sha256").update("").digest("hex"),
  },
  identity_id: m.identity_id,
  decided_at: m.decided_at,
};
const bytes = Buffer.from(JSON.stringify(doc));
fs.writeFileSync(path.join(out, "verdict.json"), bytes);
fs.writeFileSync(path.join(out, "job_result.json"), JSON.stringify({
  status: "verdict", state, verdict_sha256: crypto.createHash("sha256").update(bytes).digest("hex"), simulated: true,
}));
