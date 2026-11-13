/**
 * Custódia de diretórios de modelo na CVM1 (T-809, T-811): base, derivado e referência do pai.
 *
 * Um diretório de modelo viaja como tar.gz cifrado (asset_envelope) e é identificado pelo digest
 * de model_gate.io.digest, o mesmo que o Juiz confere e que o agente calcula no derivado
 * (vm_runtime/derivative.py):
 *
 *     digest = SHA-256 de "<caminho>\0<sha256 do arquivo>\n", linhas ordenadas por caminho,
 *     sem arquivos ocultos, README* nem LICENSE*; links simbólicos ignorados.
 *
 * A extração recusa caminho absoluto, "..", link simbólico e link físico: o pacote do derivado vem
 * de um job não confiável.
 */
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const IGNORED_PREFIXES = ["README", "LICENSE"];

function fileSha256(p) {
  const h = crypto.createHash("sha256");
  const fd = fs.openSync(p, "r");
  try {
    const buf = Buffer.alloc(1 << 20);
    let n;
    while ((n = fs.readSync(fd, buf, 0, buf.length, null)) > 0) h.update(buf.subarray(0, n));
  } finally {
    fs.closeSync(fd);
  }
  return h.digest("hex");
}

/** Caminhos relativos (com "/") que entram no digest, em ordem de código. */
function modelFiles(root) {
  const out = [];
  const walk = (dir, rel) => {
    for (const name of fs.readdirSync(dir)) {
      if (name.startsWith(".")) continue;
      const abs = path.join(dir, name);
      const r = rel ? `${rel}/${name}` : name;
      const st = fs.lstatSync(abs);
      if (st.isSymbolicLink()) continue;
      if (st.isDirectory()) walk(abs, r);
      else if (st.isFile() && !IGNORED_PREFIXES.some((p) => name.startsWith(p))) out.push(r);
    }
  };
  walk(root, "");
  // Ordem dos bytes UTF-8, que é a ordem de código do sorted() do Python.
  return out.sort((a, b) => Buffer.compare(Buffer.from(a), Buffer.from(b)));
}

function setDigest(entries) {
  const h = crypto.createHash("sha256");
  const sorted = [...entries].sort((a, b) => Buffer.compare(Buffer.from(a.path), Buffer.from(b.path)));
  for (const e of sorted) h.update(`${e.path}\0${e.sha256}\n`, "utf8");
  return h.digest("hex");
}

/** { digest, files: [{path, size, sha256}] } de um diretório de modelo. */
function modelDirDigest(root) {
  if (!fs.statSync(root).isDirectory()) throw new Error(`${root} is not a directory`);
  const files = modelFiles(root).map((rel) => {
    const abs = path.join(root, ...rel.split("/"));
    return { path: rel, size: fs.statSync(abs).size, sha256: fileSha256(abs) };
  });
  if (!files.length) throw new Error(`${root} has no model files`);
  return { digest: setDigest(files), files };
}

function run(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { encoding: opts.encoding ?? "utf8", maxBuffer: 64 << 20, ...opts });
  if (r.error) throw r.error;
  if (r.status !== 0) throw new Error(`${cmd} ${args[0]} failed (${r.status}): ${String(r.stderr).slice(0, 300)}`);
  return r.stdout;
}

/** Empacota os arquivos do digest num tar.gz (sem ocultos nem links). */
function packModelDir(root, outPath) {
  const files = modelFiles(root);
  if (!files.length) throw new Error(`${root} has no model files`);
  const list = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "dnat-pack-")), "files.txt");
  try {
    fs.writeFileSync(list, files.join("\n") + "\n");
    run("tar", ["-czf", outPath, "-C", root, "--no-recursion", "-T", list]);
  } finally {
    fs.rmSync(path.dirname(list), { recursive: true, force: true });
  }
  return outPath;
}

/** Extrai um tar.gz em destDir recusando entradas perigosas. */
function safeExtractTarGz(archivePath, destDir) {
  const listing = run("tar", ["-tvzf", archivePath]).split("\n").filter(Boolean);
  const names = run("tar", ["-tzf", archivePath]).split("\n").filter(Boolean);
  if (listing.length !== names.length) throw new Error("unsafe archive: unexpected listing");
  listing.forEach((line, i) => {
    const kind = line[0];
    const name = names[i];
    if (kind !== "-" && kind !== "d") throw new Error(`unsafe archive entry (type ${kind}): ${name}`);
    const norm = path.posix.normalize(name);
    if (path.posix.isAbsolute(name) || norm === ".." || norm.startsWith("../")) {
      throw new Error(`unsafe archive path: ${name}`);
    }
  });
  fs.mkdirSync(destDir, { recursive: true });
  run("tar", ["-xzf", archivePath, "-C", destDir, "--no-same-owner", "--no-same-permissions"]);
  return destDir;
}

/** Extrai e confere o digest; devolve o diretório. */
function extractVerified(archivePath, destDir, expectedDigest) {
  safeExtractTarGz(archivePath, destDir);
  const { digest } = modelDirDigest(destDir);
  const want = String(expectedDigest || "").toLowerCase().replace(/^0x/, "");
  if (want && digest !== want) throw new Error(`digest mismatch: ${digest} != ${want}`);
  return digest;
}

module.exports = { extractVerified, fileSha256, modelDirDigest, modelFiles, packModelDir, safeExtractTarGz, setDigest };
