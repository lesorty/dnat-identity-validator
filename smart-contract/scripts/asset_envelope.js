/**
 * Envelope de cifra dos ativos do marketplace (AES-256-GCM + gzip).
 *
 * Vive no plano de controle: e o unico lugar que conhece a ASSET_ENCRYPTION_KEY.
 * Compartilhado por api-server.js e cli.js para que as duas vias de registro
 * produzam exatamente o mesmo formato.
 *
 * Layout: "DNATENC2" | uint32BE(tamanho do header) | header JSON | ciphertext
 */
const crypto = require("node:crypto");
const fs = require("node:fs");
const zlib = require("node:zlib");
const { pipeline } = require("node:stream/promises");

const ASSET_ENCRYPTION_KEY = process.env.ASSET_ENCRYPTION_KEY || "dnat-dev-asset-key";
const APP_ARTIFACT_FORMAT = "dnat-ext4-application-v1";
const DATASET_FORMAT = "dnat-dataset-v1";
// Derivado retido (T-803): tar.gz do diretório do derivado, cifrado como os datasets.
const DERIVATIVE_FORMAT = "dnat-derivative-v1";
// Modelo base depositado pelo dono (T-809): tar.gz do diretório do modelo; o contentHash é o digest dele.
const MODEL_FORMAT = "dnat-model-v1";
// Referência do pai medida sob custódia (T-312): tar.gz do diretório da referência.
const REFERENCE_FORMAT = "dnat-reference-v1";
// Pacote da bateria do Juiz (T-807): textos dos pedidos, pares do S2, corpus de utilidade.
const BATTERY_FORMAT = "dnat-battery-v1";
const APP_ARTIFACT_ENVELOPE_MAGIC = Buffer.from("DNATENC2");

function deriveAssetEncryptionKey() {
  return crypto.createHash("sha256").update(String(ASSET_ENCRYPTION_KEY)).digest();
}

function encryptBuffer(buffer, metadata = {}, format = APP_ARTIFACT_FORMAT) {
  const compressed = zlib.gzipSync(buffer, { level: 9 });
  const iv = crypto.randomBytes(12);
  const key = deriveAssetEncryptionKey();
  const cipher = crypto.createCipheriv("aes-256-gcm", key, iv);
  const ciphertext = Buffer.concat([cipher.update(compressed), cipher.final()]);
  const tag = cipher.getAuthTag();
  const header = Buffer.from(
    JSON.stringify({
      version: 2,
      format,
      cipher: "aes-256-gcm",
      iv: iv.toString("base64"),
      tag: tag.toString("base64"),
      compression: "gzip",
      metadata,
    }),
    "utf8",
  );
  const headerLength = Buffer.alloc(4);
  headerLength.writeUInt32BE(header.length, 0);
  return Buffer.concat([APP_ARTIFACT_ENVELOPE_MAGIC, headerLength, header, ciphertext]);
}

function hasEncryptedEnvelope(buffer) {
  return (
    Buffer.isBuffer(buffer) &&
    buffer.length >= APP_ARTIFACT_ENVELOPE_MAGIC.length &&
    buffer.subarray(0, APP_ARTIFACT_ENVELOPE_MAGIC.length).equals(APP_ARTIFACT_ENVELOPE_MAGIC)
  );
}

function decryptBufferEnvelope(buffer, allowedFormats = [APP_ARTIFACT_FORMAT]) {
  let parsed;
  let ciphertext;

  if (hasEncryptedEnvelope(buffer)) {
    const headerLength = buffer.readUInt32BE(APP_ARTIFACT_ENVELOPE_MAGIC.length);
    const headerStart = APP_ARTIFACT_ENVELOPE_MAGIC.length + 4;
    const headerEnd = headerStart + headerLength;
    parsed = JSON.parse(buffer.subarray(headerStart, headerEnd).toString("utf8"));
    ciphertext = buffer.subarray(headerEnd);
  } else {
    parsed = JSON.parse(buffer.toString("utf8"));
    ciphertext = Buffer.from(parsed.ciphertext, "base64");
  }

  if (!allowedFormats.includes(parsed.format)) {
    throw new Error(`Unsupported artifact format: ${parsed.format || "unknown"}`);
  }
  if (parsed.cipher !== "aes-256-gcm") {
    throw new Error(`Unsupported cipher: ${parsed.cipher || "unknown"}`);
  }

  const iv = Buffer.from(parsed.iv, "base64");
  const tag = Buffer.from(parsed.tag, "base64");
  const key = deriveAssetEncryptionKey();
  const decipher = crypto.createDecipheriv("aes-256-gcm", key, iv);
  decipher.setAuthTag(tag);
  const decrypted = Buffer.concat([decipher.update(ciphertext), decipher.final()]);
  const plaintext = parsed.compression === "gzip" ? zlib.gunzipSync(decrypted) : decrypted;
  return { plaintext, metadata: parsed.metadata || {} };
}

// --------------------------------------------------------------------------- em fluxo (T-805)
// Modelos de GB não cabem em Buffer: cifra e decifra de arquivo para arquivo, no mesmo layout. O
// tag do GCM só sai no fim; o header é gravado com um marcador de 24 caracteres (o tamanho do tag
// em base64) e o marcador é trocado no lugar quando a cifra termina.

const TAG_PLACEHOLDER = "*".repeat(24);

async function encryptFileToFile(srcPath, dstPath, metadata = {}, format = DATASET_FORMAT, { level = 1 } = {}) {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", deriveAssetEncryptionKey(), iv);
  const headerText = JSON.stringify({
    version: 2,
    format,
    cipher: "aes-256-gcm",
    iv: iv.toString("base64"),
    tag: TAG_PLACEHOLDER,
    compression: "gzip",
    metadata,
  });
  const header = Buffer.from(headerText, "utf8");
  const tagAt = APP_ARTIFACT_ENVELOPE_MAGIC.length + 4 + Buffer.byteLength(headerText.slice(0, headerText.indexOf(TAG_PLACEHOLDER)), "utf8");
  const headerLength = Buffer.alloc(4);
  headerLength.writeUInt32BE(header.length, 0);
  fs.writeFileSync(dstPath, Buffer.concat([APP_ARTIFACT_ENVELOPE_MAGIC, headerLength, header]));
  try {
    // Nível 1 por padrão: pesos quase não comprimem e o gzip 9 de 1 GB custa minutos.
    await pipeline(fs.createReadStream(srcPath), zlib.createGzip({ level }), cipher, fs.createWriteStream(dstPath, { flags: "a" }));
    const tag = Buffer.from(cipher.getAuthTag().toString("base64"), "utf8");
    if (tag.length !== TAG_PLACEHOLDER.length) throw new Error("unexpected GCM tag length");
    const fd = fs.openSync(dstPath, "r+");
    try {
      fs.writeSync(fd, tag, 0, tag.length, tagAt);
    } finally {
      fs.closeSync(fd);
    }
  } catch (e) {
    fs.rmSync(dstPath, { force: true });
    throw e;
  }
  return dstPath;
}

function readEnvelopeHeader(srcPath) {
  const fd = fs.openSync(srcPath, "r");
  try {
    const head = Buffer.alloc(APP_ARTIFACT_ENVELOPE_MAGIC.length + 4);
    fs.readSync(fd, head, 0, head.length, 0);
    if (!head.subarray(0, APP_ARTIFACT_ENVELOPE_MAGIC.length).equals(APP_ARTIFACT_ENVELOPE_MAGIC)) {
      throw new Error("not a DNAT encrypted envelope");
    }
    const length = head.readUInt32BE(APP_ARTIFACT_ENVELOPE_MAGIC.length);
    if (length > 1 << 20) throw new Error("envelope header too large");
    const header = Buffer.alloc(length);
    fs.readSync(fd, header, 0, length, head.length);
    return { parsed: JSON.parse(header.toString("utf8")), start: head.length + length };
  } finally {
    fs.closeSync(fd);
  }
}

/** Decifra um envelope em arquivo para outro arquivo. Tag que não confere apaga a saída e falha. */
async function decryptFileToFile(srcPath, dstPath, allowedFormats = [APP_ARTIFACT_FORMAT]) {
  const { parsed, start } = readEnvelopeHeader(srcPath);
  if (!allowedFormats.includes(parsed.format)) throw new Error(`Unsupported artifact format: ${parsed.format || "unknown"}`);
  if (parsed.cipher !== "aes-256-gcm") throw new Error(`Unsupported cipher: ${parsed.cipher || "unknown"}`);
  const decipher = crypto.createDecipheriv("aes-256-gcm", deriveAssetEncryptionKey(), Buffer.from(parsed.iv, "base64"));
  decipher.setAuthTag(Buffer.from(parsed.tag, "base64"));
  const stages = [fs.createReadStream(srcPath, { start }), decipher];
  if (parsed.compression === "gzip") stages.push(zlib.createGunzip());
  stages.push(fs.createWriteStream(dstPath));
  try {
    await pipeline(...stages);
  } catch (e) {
    fs.rmSync(dstPath, { force: true });
    throw e;
  }
  return { metadata: parsed.metadata || {} };
}

module.exports = {
  APP_ARTIFACT_FORMAT,
  DATASET_FORMAT,
  DERIVATIVE_FORMAT,
  MODEL_FORMAT,
  REFERENCE_FORMAT,
  BATTERY_FORMAT,
  APP_ARTIFACT_ENVELOPE_MAGIC,
  deriveAssetEncryptionKey,
  encryptBuffer,
  decryptBufferEnvelope,
  hasEncryptedEnvelope,
  encryptFileToFile,
  decryptFileToFile,
};
