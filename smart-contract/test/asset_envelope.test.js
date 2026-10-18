/* Envelope de cifra dos ativos: round-trip, compatibilidade e deteccao de adulteracao. */
const assert = require("node:assert");
const {
  APP_ARTIFACT_FORMAT,
  DATASET_FORMAT,
  encryptBuffer,
  decryptBufferEnvelope,
  hasEncryptedEnvelope,
} = require("../scripts/asset_envelope");

let pass = 0;
const check = (nome, fn) => {
  try {
    fn();
    console.log(`  ok    ${nome}`);
    pass++;
  } catch (e) {
    console.log(`  FALHA ${nome}: ${e.message}`);
    process.exitCode = 1;
  }
};

const csv = Buffer.from("cpf,nome,score\n11111111111,Fulano,720\n22222222222,Beltrano,655\n");

check("dataset: round-trip preserva os bytes", () => {
  const env = encryptBuffer(csv, { sourceFileName: "d.csv" }, DATASET_FORMAT);
  assert.ok(decryptBufferEnvelope(env, [DATASET_FORMAT]).plaintext.equals(csv));
});

check("dataset: ciphertext nao contem o plaintext", () => {
  const env = encryptBuffer(csv, {}, DATASET_FORMAT);
  assert.ok(!env.includes(Buffer.from("11111111111")));
  assert.ok(!env.includes(Buffer.from("Fulano")));
});

check("aplicacao: round-trip no formato padrao segue funcionando", () => {
  const art = Buffer.from("ext4-artifact-bytes");
  assert.ok(decryptBufferEnvelope(encryptBuffer(art)).plaintext.equals(art));
});

check("compat: dataset antigo em claro nao e detectado como envelope", () => {
  assert.strictEqual(hasEncryptedEnvelope(csv), false);
  assert.strictEqual(hasEncryptedEnvelope(Buffer.alloc(3)), false);
});

check("envelope novo e detectado", () => {
  assert.strictEqual(hasEncryptedEnvelope(encryptBuffer(csv, {}, DATASET_FORMAT)), true);
});

check("formatos nao se cruzam: dataset recusado como aplicacao", () => {
  const env = encryptBuffer(csv, {}, DATASET_FORMAT);
  assert.throws(() => decryptBufferEnvelope(env, [APP_ARTIFACT_FORMAT]), /Unsupported artifact format/);
});

check("GCM detecta adulteracao do ciphertext", () => {
  const env = encryptBuffer(csv, {}, DATASET_FORMAT);
  env[env.length - 1] ^= 0xff;
  assert.throws(() => decryptBufferEnvelope(env, [DATASET_FORMAT]));
});

check("IV aleatorio: duas cifras do mesmo dado diferem", () => {
  assert.ok(!encryptBuffer(csv, {}, DATASET_FORMAT).equals(encryptBuffer(csv, {}, DATASET_FORMAT)));
});

console.log(`\n${pass}/8 testes passaram`);
