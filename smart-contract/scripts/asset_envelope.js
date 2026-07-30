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
const zlib = require("node:zlib");

const ASSET_ENCRYPTION_KEY = process.env.ASSET_ENCRYPTION_KEY || "dnat-dev-asset-key";
const APP_ARTIFACT_FORMAT = "dnat-ext4-application-v1";
const DATASET_FORMAT = "dnat-dataset-v1";
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

module.exports = {
  APP_ARTIFACT_FORMAT,
  DATASET_FORMAT,
  APP_ARTIFACT_ENVELOPE_MAGIC,
  deriveAssetEncryptionKey,
  encryptBuffer,
  decryptBufferEnvelope,
  hasEncryptedEnvelope,
};
