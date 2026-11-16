#!/usr/bin/env node
/**
 * Conferência da interface num Chrome headless, pelo DevTools Protocol (sem dependências).
 *
 *   node tools/ui_check.js [URL] [--out DIR] [--width 1280,390] [--no-identity]
 *
 * URL: padrão, a pilha de desenvolvimento no ar (smart-contract/.dev_stack.json) ou localhost:3001.
 * Percorre as abas, cria uma identidade pela página (prova de trabalho no navegador), tira uma
 * tela de cada aba em cada largura e falha (saída 1) se houver erro de JavaScript, recurso que não
 * carrega (fora o favicon) ou rolagem horizontal.
 */
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const argv = process.argv.slice(2);
const opt = (n, f) => (argv.includes(n) ? argv[argv.indexOf(n) + 1] : f);
const statusFile = path.join(__dirname, "..", "smart-contract", ".dev_stack.json");
const URL_ = argv.find((a) => /^https?:/.test(a)) ||
  (fs.existsSync(statusFile) ? JSON.parse(fs.readFileSync(statusFile, "utf8")).url : "http://localhost:3001/");
const OUT = opt("--out", fs.mkdtempSync(path.join(os.tmpdir(), "dnat-ui-check-")));
const WIDTHS = opt("--width", "1280,390").split(",").map(Number);
const TABS = ["#modelos", "#treinar", "#jobs", "#juiz", "#resultados", "#resultados?v=runs", "#identidade"];
const CHROME = ["google-chrome", "chromium", "chromium-browser"].find((c) => {
  try { require("node:child_process").execFileSync("which", [c], { stdio: "ignore" }); return true; } catch { return false; }
});
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function check(width) {
  const port = 9300 + Math.floor(Math.random() * 600);
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-ui-profile-"));
  const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${port}`, "--no-first-run",
    "--no-default-browser-check", `--user-data-dir=${profile}`, "about:blank"], { stdio: "ignore" });
  try {
    let target;
    for (let i = 0; i < 60 && !target; i++) {
      try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page"); } catch { await sleep(200); }
    }
    if (!target) throw new Error("o Chrome não abriu o DevTools");
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
    let id = 0; const pending = new Map(); const errors = [];
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); }
      if (d.method === "Runtime.exceptionThrown") errors.push(`exceção: ${d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text}`);
      if (d.method === "Runtime.consoleAPICalled" && d.params.type === "error") errors.push(`console: ${d.params.args.map((a) => a.value || a.description).join(" ")}`);
      if (d.method === "Log.entryAdded" && d.params.entry.level === "error" && !/favicon/.test(d.params.entry.url || "")) errors.push(`recurso: ${d.params.entry.text} ${d.params.entry.url || ""}`);
    };
    const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
    const evalJs = async (e) => (await send("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true })).result?.result?.value;
    await send("Runtime.enable"); await send("Log.enable"); await send("Page.enable");
    await send("Emulation.setDeviceMetricsOverride", { width, height: 1000, deviceScaleFactor: 1, mobile: width < 500 });
    await send("Page.navigate", { url: `${URL_.replace(/\/?$/, "/")}#modelos` }); await sleep(2500);
    const overflow = [];
    const shot = async (name) => {
      const r = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
      fs.writeFileSync(path.join(OUT, `${width}-${name.replace(/[^a-z0-9]+/gi, "_")}.png`), Buffer.from(r.result.data, "base64"));
      if (await evalJs("document.documentElement.scrollWidth > window.innerWidth")) overflow.push(name);
    };
    if (!argv.includes("--no-identity") && !(await evalJs("!!window.DnatIdentity.load()"))) {
      await evalJs(`location.hash = "#identidade"`); await sleep(1500);
      await evalJs(`document.querySelector("#icreate")?.click()`);
      for (let i = 0; i < 90 && !(await evalJs("!!window.DnatIdentity.load()")); i++) await sleep(1000);
      if (!(await evalJs("!!window.DnatIdentity.load()"))) errors.push("a identidade não foi criada pela página em 90 s");
    }
    const stuck = [];
    for (const tab of TABS) {
      await evalJs(`location.hash = ${JSON.stringify(tab)}`);
      await sleep(800);
      // espera os carregamentos da aba terminarem (até 25 s); o que continuar girando é falha
      let spinning = true;
      for (let i = 0; i < 50 && spinning; i++) { spinning = await evalJs(`!!document.querySelector("#view .spin")`); if (spinning) await sleep(500); }
      if (spinning) stuck.push(tab);
      await shot(tab);
    }
    if (stuck.length) errors.push(`ainda carregando depois de 25 s: ${stuck.join(", ")}`);
    ws.close();
    return { width, errors, overflow };
  } finally {
    chrome.kill();
    await sleep(300);
    fs.rmSync(profile, { recursive: true, force: true });
  }
}

(async () => {
  if (!CHROME) { console.error("Chrome/Chromium não encontrado"); process.exit(2); }
  console.log(`interface: ${URL_}`);
  let bad = 0;
  for (const w of WIDTHS) {
    const r = await check(w);
    const ok = !r.errors.length && !r.overflow.length;
    bad += ok ? 0 : 1;
    console.log(`${ok ? "ok    " : "FALHOU"} ${w}px · ${TABS.length} abas${r.overflow.length ? ` · rolagem horizontal em ${r.overflow.join(", ")}` : ""}`);
    for (const e of r.errors) console.log(`       ${e}`);
  }
  console.log(`telas em ${OUT}`);
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
