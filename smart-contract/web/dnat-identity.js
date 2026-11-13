/*
 * Identidade no navegador (T-1703, T-1705): a web UI assina os pedidos que criam trabalho como o CLI.
 *
 * - Chave Ed25519 pelo WebCrypto. A semente fica no localStorage desta origem ("dnat-identity"),
 *   no mesmo formato do arquivo do CLI (~/.dnat/identity.json): {version, id, publicKey, seed}.
 *   Dá para importar o arquivo do CLI e exportar a chave daqui. Quem tem a semente age pela
 *   identidade: o localStorage é exposto a qualquer script desta origem (protótipo).
 * - Prova de trabalho: SHA-256(desafio ‖ chave ‖ nonce de 8 bytes) com d bits zero, num Web Worker
 *   com SHA-256 próprio (o crypto.subtle é assíncrono e lento demais para milhões de hashes). O
 *   primeiro bloco (desafio ‖ chave) é constante: o estado intermediário é calculado uma vez.
 * - Pedido assinado: X-Identity, X-Timestamp e X-Signature sobre
 *       "DNAT-REQUEST-v1\n" + MÉTODO + "\n" + caminho + "\n" + carimbo + "\n" + SHA-256(corpo) em hex
 *   O corpo multipart é montado aqui, em bytes, para assinar exatamente o que vai pela rede.
 *
 * Expõe window.DnatIdentity.
 */
(function () {
  const STORAGE_KEY = "dnat-identity";
  const KEY_FILE_VERSION = 1;
  const TAG = "DNAT-REQUEST-v1";
  const PKCS8_PREFIX = hexToBytes("302e020100300506032b657004220420");
  const enc = new TextEncoder();

  function hexToBytes(hex) {
    const s = String(hex).trim().toLowerCase();
    if (!/^([0-9a-f]{2})*$/.test(s)) throw new Error("hex inválido");
    const out = new Uint8Array(s.length / 2);
    for (let i = 0; i < out.length; i += 1) out[i] = parseInt(s.slice(2 * i, 2 * i + 2), 16);
    return out;
  }

  function bytesToHex(bytes) {
    return Array.from(new Uint8Array(bytes), (b) => b.toString(16).padStart(2, "0")).join("");
  }

  function concat(...parts) {
    const total = parts.reduce((n, p) => n + p.length, 0);
    const out = new Uint8Array(total);
    let off = 0;
    for (const p of parts) {
      out.set(p, off);
      off += p.length;
    }
    return out;
  }

  async function sha256Hex(bytes) {
    return bytesToHex(await crypto.subtle.digest("SHA-256", bytes));
  }

  // ------------------------------------------------------------- prova de trabalho (Web Worker)

  // Fonte do worker: SHA-256 de 72 bytes (2 blocos) com o primeiro bloco pré-calculado.
  const WORKER_SOURCE = `
const K = new Uint32Array([
  0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
  0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
  0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
  0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
  0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
  0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
  0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
  0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]);
const H0 = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
const W = new Uint32Array(64);
function compress(st, w) {
  for (let i = 16; i < 64; i++) {
    const a = w[i-15], b = w[i-2];
    const s0 = ((a>>>7)|(a<<25)) ^ ((a>>>18)|(a<<14)) ^ (a>>>3);
    const s1 = ((b>>>17)|(b<<15)) ^ ((b>>>19)|(b<<13)) ^ (b>>>10);
    w[i] = (w[i-16] + s0 + w[i-7] + s1) | 0;
  }
  let a=st[0],b=st[1],c=st[2],d=st[3],e=st[4],f=st[5],g=st[6],h=st[7];
  for (let i = 0; i < 64; i++) {
    const S1 = ((e>>>6)|(e<<26)) ^ ((e>>>11)|(e<<21)) ^ ((e>>>25)|(e<<7));
    const t1 = (h + S1 + ((e & f) ^ (~e & g)) + K[i] + w[i]) | 0;
    const S0 = ((a>>>2)|(a<<30)) ^ ((a>>>13)|(a<<19)) ^ ((a>>>22)|(a<<10));
    const t2 = (S0 + ((a & b) ^ (a & c) ^ (b & c))) | 0;
    h=g; g=f; f=e; e=(d+t1)|0; d=c; c=b; b=a; a=(t1+t2)|0;
  }
  return [(st[0]+a)|0,(st[1]+b)|0,(st[2]+c)|0,(st[3]+d)|0,(st[4]+e)|0,(st[5]+f)|0,(st[6]+g)|0,(st[7]+h)|0];
}
function zeroBits(h) {
  let bits = 0;
  for (const word of h) { const z = Math.clz32(word); bits += z; if (z < 32) break; }
  return bits;
}
onmessage = (ev) => {
  const { block1, difficulty } = ev.data;  // 64 bytes: desafio ‖ chave
  for (let i = 0; i < 16; i++) W[i] = (block1[4*i]<<24)|(block1[4*i+1]<<16)|(block1[4*i+2]<<8)|block1[4*i+3];
  const mid = compress(H0, W);
  const started = Date.now();
  for (let hi = 0; hi < 0x100000000; hi++) {
    for (let lo = 0; lo < 0x100000000; lo++) {
      W.fill(0);
      W[0] = hi; W[1] = lo; W[2] = 0x80000000; W[15] = 576;  // 72 bytes = 576 bits
      if (zeroBits(compress(mid, W)) >= difficulty) {
        postMessage({ done: true, nonce: (BigInt(hi) << 32n | BigInt(lo >>> 0)).toString(), tried: hi * 4294967296 + lo + 1, ms: Date.now() - started });
        return;
      }
      if ((lo & 0xfffff) === 0 && lo > 0) postMessage({ done: false, tried: hi * 4294967296 + lo, ms: Date.now() - started });
    }
  }
};`;

  function solveProof(challengeHex, publicKeyHex, difficulty, onProgress) {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(new Blob([WORKER_SOURCE], { type: "text/javascript" }));
      const worker = new Worker(url);
      worker.onmessage = (ev) => {
        if (ev.data.done) {
          worker.terminate();
          URL.revokeObjectURL(url);
          resolve(ev.data);
        } else if (onProgress) onProgress(ev.data);
      };
      worker.onerror = (e) => {
        worker.terminate();
        reject(new Error(e.message || "falha no worker da prova de trabalho"));
      };
      worker.postMessage({ block1: concat(hexToBytes(challengeHex), hexToBytes(publicKeyHex)), difficulty });
    });
  }

  // ------------------------------------------------------------- chave e armazenamento

  async function idOf(publicKeyHex) {
    return sha256Hex(hexToBytes(publicKeyHex));
  }

  async function validate(data) {
    if (!data || data.version !== KEY_FILE_VERSION) throw new Error(`arquivo de chave: versão ${data && data.version} não suportada`);
    if (!/^[0-9a-f]{64}$/.test(data.publicKey || "") || !/^[0-9a-f]{64}$/.test(data.seed || "")) {
      throw new Error("arquivo de chave: publicKey e seed precisam de 64 hex");
    }
    if ((await idOf(data.publicKey)) !== data.id) throw new Error("arquivo de chave: o id não bate com a chave pública");
    // a semente tem de gerar a chave pública declarada: assina e confere
    const key = await privateKey(data.seed);
    const msg = enc.encode("dnat-key-check");
    const sig = await crypto.subtle.sign({ name: "Ed25519" }, key, msg);
    const pub = await crypto.subtle.importKey("raw", hexToBytes(data.publicKey), { name: "Ed25519" }, false, ["verify"]);
    if (!(await crypto.subtle.verify({ name: "Ed25519" }, pub, sig, msg))) throw new Error("arquivo de chave: a semente não é desta chave pública");
    return { version: KEY_FILE_VERSION, id: data.id, publicKey: data.publicKey, seed: data.seed,
      ...(data.registeredAtUtc ? { registeredAtUtc: data.registeredAtUtc } : {}) };
  }

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function save(identity) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(identity));
  }

  function clear() {
    localStorage.removeItem(STORAGE_KEY);
  }

  function privateKey(seedHex) {
    return crypto.subtle.importKey("pkcs8", concat(PKCS8_PREFIX, hexToBytes(seedHex)), { name: "Ed25519" }, false, ["sign"]);
  }

  async function generate() {
    const pair = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
    const publicKey = bytesToHex(await crypto.subtle.exportKey("raw", pair.publicKey));
    const pkcs8 = new Uint8Array(await crypto.subtle.exportKey("pkcs8", pair.privateKey));
    return { version: KEY_FILE_VERSION, id: await idOf(publicKey), publicKey, seed: bytesToHex(pkcs8.slice(-32)) };
  }

  /** Cria a chave, faz a prova de trabalho e registra na CVM1. A chave só é guardada depois do registro. */
  async function create(onProgress) {
    if (!crypto.subtle) throw new Error("WebCrypto indisponível: abra a página por HTTPS ou localhost");
    const identity = await generate();
    const ch = await (await fetch("/api/identity/challenge")).json();
    const proof = await solveProof(ch.challenge, identity.publicKey, ch.difficulty, onProgress);
    const res = await fetch("/api/identity/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ publicKey: identity.publicKey, nonce: proof.nonce }),
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.error || `registro recusado (${res.status})`);
    const saved = { ...identity, registeredAtUtc: body.registeredAtUtc };
    save(saved);
    return { identity: saved, difficulty: ch.difficulty, proof };
  }

  async function importJson(text) {
    const identity = await validate(JSON.parse(text));
    save(identity);
    return identity;
  }

  function exportJson(identity) {
    return JSON.stringify(identity, null, 2);
  }

  // ------------------------------------------------------------- pedidos assinados

  /** Corpo multipart/form-data em bytes. fields: {nome: texto}; files: {nome: File}. */
  async function buildMultipart(fields, files) {
    const boundary = `----dnat${bytesToHex(crypto.getRandomValues(new Uint8Array(12)))}`;
    const parts = [];
    for (const [name, value] of Object.entries(fields || {})) {
      parts.push(enc.encode(`--${boundary}\r\nContent-Disposition: form-data; name="${name}"\r\n\r\n${value ?? ""}\r\n`));
    }
    for (const [name, file] of Object.entries(files || {})) {
      if (!file) continue;
      const fname = String(file.name || "file").replace(/["\r\n]/g, "_");
      parts.push(enc.encode(`--${boundary}\r\nContent-Disposition: form-data; name="${name}"; filename="${fname}"\r\nContent-Type: ${file.type || "application/octet-stream"}\r\n\r\n`));
      parts.push(new Uint8Array(await file.arrayBuffer()), enc.encode("\r\n"));
    }
    parts.push(enc.encode(`--${boundary}--\r\n`));
    return { body: concat(...parts), contentType: `multipart/form-data; boundary=${boundary}` };
  }

  /** fetch assinado pela identidade guardada. body: Uint8Array ou texto (JSON já serializado). */
  async function signedFetch(path, { method = "POST", body = null, contentType = null } = {}) {
    const identity = load();
    if (!identity) throw new Error("sem identidade: crie ou importe uma no painel Identidade");
    const bytes = body === null ? new Uint8Array(0) : typeof body === "string" ? enc.encode(body) : body;
    const timestamp = String(Date.now());
    const message = enc.encode([TAG, method.toUpperCase(), path, timestamp, await sha256Hex(bytes)].join("\n"));
    const signature = await crypto.subtle.sign({ name: "Ed25519" }, await privateKey(identity.seed), message);
    const headers = { "X-Identity": identity.id, "X-Timestamp": timestamp, "X-Signature": bytesToHex(signature) };
    if (contentType) headers["Content-Type"] = contentType;
    return fetch(path, { method, headers, body: body === null ? undefined : bytes });
  }

  window.DnatIdentity = { load, save, clear, create, importJson, exportJson, signedFetch, buildMultipart, solveProof };
})();
