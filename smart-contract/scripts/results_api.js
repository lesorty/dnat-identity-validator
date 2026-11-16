/**
 * Resultados das verificações locais, para a aba Resultados da interface (web/index.html).
 *
 *   GET /api/results               experimentos (catálogo abaixo), com o que cada um responde, os
 *                                  números de destaque e as conferências; mais os arquivos sem
 *                                  experimento no catálogo.
 *   GET /api/results/file/:root/:stem   um resultado: metadados, o .md (se houver) e o JSON.
 *   GET /api/runs                  todas as runs: cada arquivo de resultado e cada linha do registro
 *                                  de experimentos ($MODEL_GATE_DATA/runs/*.jsonl, T-206).
 *
 * Tudo aqui é verificação local (regra de 12/11: todo dado do artigo sai da nuvem). Só leitura de
 * arquivos que já estão no repositório e do registro de execuções, que guarda só métricas (T-211).
 */
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const REPO = path.resolve(__dirname, "..", "..");
const ROOTS = {
  model_gate: path.join(REPO, "model_gate", "results"),
  smart_contract: path.join(REPO, "smart-contract", "results"),
};
// Pacotes da campanha na nuvem importados (tools/cloud/importar.sh): resultados_nuvem/<pacote>/.
const CLOUD = path.join(REPO, "resultados_nuvem");

/** Raízes de resultado: as locais e, por pacote importado, results/model_gate e results/smart-contract. */
function roots() {
  const out = Object.entries(ROOTS).map(([id, dir]) => ({ id, dir, base: id, origem: "local", pacote: null }));
  if (!fs.existsSync(CLOUD)) return out;
  for (const name of fs.readdirSync(CLOUD).sort()) {
    const meta = readJson(path.join(CLOUD, name, "pacote.json"));
    if (!meta) continue;
    for (const [base, sub] of [["model_gate", "model_gate"], ["smart_contract", "smart-contract"]]) {
      const dir = path.join(CLOUD, name, "results", sub);
      if (fs.existsSync(dir)) out.push({ id: `nuvem.${name}.${base}`, dir, base, origem: "nuvem",
        pacote: { nome: name, host: meta.host, commit: meta.head?.commit, congelado: Boolean(meta.congelado),
          maquina: machineSummary(path.join(CLOUD, name, "machine")) } });
    }
  }
  return out;
}

function machineSummary(dir) {
  try {
    const f = fs.readdirSync(dir).find((x) => x.endsWith(".json"));
    const c = f && readJson(path.join(dir, f));
    if (!c) return null;
    return { cpu: c.cpu?.model, cpus: c.cpu?.logical_cpus, bf16: Boolean(c.cpu?.flags?.avx512_bf16 || c.cpu?.flags?.amx_bf16),
      confidencial: c.confidential?.kind || null, nuvem: c.cloud?.provider || null, tipo: c.cloud?.vm_size || c.cloud?.shape || null };
  } catch {
    return null;
  }
}

const RUNS_DIR = () =>
  path.join(process.env.MODEL_GATE_DATA || path.join(os.homedir(), "model_gate_data"), "runs");

const pct = (x) => (typeof x === "number" ? `${(100 * x).toFixed(0)}%` : "—");
const num = (x, d = 1) => (typeof x === "number" ? x.toLocaleString("pt-BR", { maximumFractionDigits: d }) : "—");
const VERD = { aprovado: "aprovado", reprovado: "reprovado", inconclusivo: "inconclusivo", approved: "aprovado",
  rejected: "reprovado", inconclusive: "inconclusivo", failure: "falha" };

/**
 * Catálogo: cada experimento junta arquivos de resultado, diz o que se propõe a responder e extrai
 * os números de destaque. `d(stem)` devolve o JSON do arquivo (ou null).
 */
const EXPERIMENTS = [
  {
    id: "fluxo", titulo: "Fluxo inteiro no DNAT", tasks: ["T-811", "T-801"], teste: "Teste 8 (ensaio)", objetivo: "O3",
    pergunta: "Do depósito do base ao recibo, o fluxo roda: treino, retenção, Juiz como segundo job, recibo on-chain e cota; e cada job numa CVM de uso único.",
    arquivos: ["smart_contract/e2e_direct", "smart_contract/e2e_direct_uso_unico", "smart_contract/e2e_direct_Qwen_Qwen2.5-0.5B-Instruct", "smart_contract/e2e_direct_Qwen_Qwen2.5-0.5B-Instruct_uso_unico"],
    destaques: (d) => {
      const e = d("smart_contract/e2e_direct");
      const q = d("smart_contract/e2e_direct_Qwen_Qwen2.5-0.5B-Instruct_uso_unico");
      const out = [];
      if (e?.scenarios) out.push({ rotulo: "Cenários A · B · C", valor: Object.values(e.scenarios).map((s) => VERD[s.judge?.outcome] || s.judge?.outcome || "—").join(" · "), nota: "A com o Juiz real sem prereg; B e C com Juiz simulado" });
      if (e?.scenarios) out.push({ rotulo: "Cota depois de B e C", valor: `${e.scenarios.B?.balanceAfter ?? "—"} e ${e.scenarios.C?.balanceAfter ?? "—"}`, nota: "saldo 20; aprovado custa 1, reprovado 5" });
      const vm = q?.scenarios?.B?.jobVm;
      if (vm) out.push({ rotulo: "Pico de RSS do job (Qwen)", valor: `${num(vm.peakRssBytes / 2 ** 30, 2)} GB`, nota: "CVM de uso único, destruída depois" });
      return out;
    },
  },
  {
    id: "teste8", titulo: "Teste 8 local com o Juiz real", tasks: ["T-814"], teste: "Teste 8", objetivo: "O3",
    pergunta: "Reprovado não sai, inconclusivo fica retido, o operador revoga e a cota é gasta por veredito, com o Juiz real.",
    arquivos: ["smart_contract/T-814_teste8_local"],
    destaques: (d) => {
      const r = d("smart_contract/T-814_teste8_local")?.runs || {};
      return Object.entries(r).map(([k, v]) => ({ rotulo: k === "abliteracao" ? "Abliteração" : k === "ajuste" ? "Ajuste (LoRA)" : k,
        valor: `${VERD[v.judge?.outcome] || v.judge?.outcome || "—"} (regra ${v.rule ?? "—"})`, nota: (v.reasons || []).join(", ") }));
    },
  },
  {
    id: "lora", titulo: "LoRA real numa CVM de uso único", tasks: ["T-806"], teste: "Teste 8 (ensaio)", objetivo: "O3",
    pergunta: "O treino de verdade (script da T-901, torch e peft) roda numa CVM de uso único e o derivado só existe cifrado.",
    arquivos: ["smart_contract/T-806_lora_uso_unico"],
    destaques: (d) => {
      const x = d("smart_contract/T-806_lora_uso_unico");
      if (!x) return [];
      return [
        { rotulo: "Passos / perda final", valor: `${x.job?.metrics?.steps ?? "—"} / ${num(x.job?.metrics?.loss, 5)}` },
        { rotulo: "Tempo de treino", valor: `${num(x.job?.metrics?.train_seconds, 0)} s` },
        { rotulo: "Pico de RSS", valor: `${num((x.jobVm?.peakRssBytes || 0) / 2 ** 30, 2)} GB`, nota: "a CVM de treino precisa de 8 GB ou mais" },
        { rotulo: "Derivado cifrado", valor: `${num((x.derivative?.envelopeBytes || 0) / 2 ** 20, 0)} MB` },
      ];
    },
  },
  {
    id: "identidade", titulo: "Identidade e cota", tasks: ["T-1705", "T-1707"], teste: "Teste 9", objetivo: "O6",
    pergunta: "A identidade custa uma prova de trabalho; a cota esgota quem tenta enganar o Juiz e recusa o job sem saldo.",
    arquivos: ["smart_contract/identity_pow_cost", "smart_contract/demo_cota"],
    destaques: (d) => {
      const p = d("smart_contract/identity_pow_cost");
      const row = (k) => p?.rows?.find((r) => r.difficulty === k);
      return [
        { rotulo: "Hashes por segundo", valor: num(p?.hashesPerSecond, 0), nota: "notebook, 1 núcleo" },
        { rotulo: "Prova com d = 20", valor: `${num(row(20)?.medianSeconds, 1)} s`, nota: `esperado ${num(row(20)?.expectedSeconds, 1)} s` },
        { rotulo: "Prova com d = 24", valor: `${num(row(24)?.medianSeconds, 1)} s`, nota: `esperado ${num(row(24)?.expectedSeconds, 1)} s` },
      ];
    },
  },
  {
    id: "gas", titulo: "Gás do recibo e da revogação", tasks: ["T-709"], teste: "Teste 7 (custo)", objetivo: "O4",
    pergunta: "Quanto custa on-chain o recibo de cada veredito e a revogação.",
    arquivos: ["smart_contract/gas"],
    destaques: (d) => (d("smart_contract/gas")?.rows || [])
      .filter((r) => /registerDerivative|revokeDerivative/.test(r.fn))
      .map((r) => ({ rotulo: r.fn, valor: num(r.gasUsed, 0) })),
  },
  {
    id: "juiz", titulo: "O Juiz real e a referência forjada", tasks: ["T-807", "T-1205"], teste: "Teste 1 (ensaio) e Teste 7", objetivo: "O1 · O4",
    pergunta: "O Juiz real separa abliterados do base; sem a referência custodiada do pai, o veto some (A3).",
    arquivos: ["model_gate/T-807_juiz_local", "model_gate/T-1205_referencia_forjada"],
    destaques: (d) => [
      ...(d("model_gate/T-807_juiz_local")?.results || []).map((r) => ({ rotulo: r.derivative, valor: `${r.state} (regra ${r.rule})`, nota: `${num(r.seconds, 0)} s` })),
      ...(d("model_gate/T-1205_referencia_forjada")?.runs || []).map((r) => ({ rotulo: r.run.replace(/_/g, " "), valor: `${r.state} (regra ${r.rule})` })),
    ],
  },
  {
    id: "direcao", titulo: "Direção de recusa do S2", tasks: ["T-402", "T-414"], teste: "Teste 1", objetivo: "O1",
    pergunta: "Em que camada a direção de recusa do Qwen2.5-0.5B carrega a recusa, para o S2 ler a abliteração.",
    arquivos: ["model_gate/T-402_direcao", "model_gate/T-414_camada", "model_gate/T-414_arditi"],
    destaques: (d) => {
      const a = d("model_gate/T-414_arditi");
      const c = d("model_gate/T-402_direcao");
      return [
        { rotulo: "Camada da T-402", valor: String(c?.direction?.layer ?? "—"), nota: "maior separação na validação" },
        { rotulo: "Arditi: candidatos que passam", valor: a ? `${a.passam_induce_e_kl} de ${a.candidatos?.length}` : "—", nota: "5 posições × 20 camadas" },
        { rotulo: "Nocivos que o base recusa", valor: a ? `${a.validacao?.n_harmful_kept} de ${a.validacao?.n_harmful_val}` : "—", nota: "filtro do artigo" },
        { rotulo: "Recusa com a camada 6 ablada", valor: a ? `${pct(a.recusa_gerada?.ablado_t402)} (base ${pct(a.recusa_gerada?.base)})` : "—", nota: "a camada 6 não carrega a recusa" },
      ];
    },
  },
  {
    id: "populacao", titulo: "População de fumaça", tasks: ["T-901", "T-908"], teste: "Testes 2 e 3 (receitas)", objetivo: "O2",
    pergunta: "As receitas de derivado funcionam: LoRA benigno e abliteração mudam o que deveriam.",
    arquivos: ["model_gate/T-901_fumaca", "model_gate/T-908_fumaca_fumaca-abl-d6-a1-todas", "model_gate/T-908_fumaca_fumaca-abl-d12-a1-todas"],
    destaques: (d) => {
      const l = d("model_gate/T-901_fumaca");
      const out = [];
      if (l) out.push({ rotulo: "LoRA: perda", valor: `${num(l.perda_primeiro_passo, 3)} → ${num(l.perda_ultimo_passo, 3)}`, nota: `${l.passos} passos` });
      for (const k of ["d6", "d12"]) {
        const x = d(`model_gate/T-908_fumaca_fumaca-abl-${k}-a1-todas`);
        if (x) out.push({ rotulo: `Abliteração ${k}: recusa nos nocivos`, valor: `${pct(x.recusa?.base?.nocivos_vazio)} → ${pct(x.recusa?.derivado?.nocivos_vazio)}`,
          nota: `S2 camada 6: ${num(x.s2?.derivado?.ratio, 2)}; faixa: ${num(x.s2?.derivado?.ratio_band, 2)}` });
      }
      return out;
    },
  },
  {
    id: "custo", titulo: "Custo e calibragem do instrumento", tasks: ["T-208", "T-301", "T-307", "T-309"], teste: "Teste 1 (custo, G1)", objetivo: "O1",
    pergunta: "O veredito cabe em 80 min em 4 vCPU? Quantas âncoras a bateria rende e o detector de recusa é confiável?",
    arquivos: ["model_gate/T-208_vazao", "model_gate/T-208_comprimento", "model_gate/T-309_avaliador", "model_gate/T-301_ancoras", "model_gate/T-301_dimensionamento", "model_gate/T-307_detector", "model_gate/T-307_exemplo"],
    destaques: (d) => {
      const v = d("model_gate/T-208_vazao")?.cells || [];
      const b1 = v.find((c) => c.batch_size === 1), b4 = v.find((c) => c.batch_size === 4);
      const g = d("model_gate/T-309_avaliador")?.runs?.[0];
      const anc = d("model_gate/T-301_ancoras")?.anchors_in_both_conditions;
      return [
        { rotulo: "Vazão (lote 1 → 4)", valor: `${num(b1?.mean_tok_s)} → ${num(b4?.mean_tok_s)} tok/s`, nota: "4 núcleos do notebook" },
        { rotulo: "Avaliador por veredito", valor: g ? `${num(g.verdict_minutes, 0)} min` : "—", nota: g ? `${g.judge}, ${num(g.seconds_per_item)} s/item; meta 80 min` : "" },
        { rotulo: "Âncoras nas duas condições", valor: anc ? num(Object.values(anc).reduce((a, b) => a + b, 0), 0) : "—", nota: "6 categorias do StrongREJECT" },
        { rotulo: "Precisão do detector", valor: "25/25", nota: "T-307: nenhum item cumprido vira âncora" },
      ];
    },
  },
];

// ------------------------------------------------------------------ leitura dos arquivos

function readJson(p) {
  try {
    return JSON.parse(fs.readFileSync(p, "utf8"));
  } catch {
    return null;
  }
}

function listResultFiles() {
  const out = [];
  for (const r of roots()) {
    if (!fs.existsSync(r.dir)) continue;
    const stems = new Set(fs.readdirSync(r.dir).filter((f) => /\.(json|md)$/.test(f)).map((f) => f.replace(/\.(json|md)$/, "")));
    for (const stem of stems) out.push({ root: r.id, stem, key: `${r.id}/${stem}`, dir: r.dir, baseKey: `${r.base}/${stem}`, origem: r.origem, pacote: r.pacote });
  }
  return out;
}

const ISO = /(20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d)/;
const RUNID = /(20\d\d)(\d\d)(\d\d)T(\d\d)(\d\d)(\d\d)/;

function fileDate(json, mdText, jsonPath) {
  const direct = json && (json.measuredAtUtc || json.ts || json.createdAtUtc);
  if (direct) return new Date(direct).toISOString();
  const rid = json && String(json.run_id || "").match(RUNID);
  if (rid) return new Date(`${rid[1]}-${rid[2]}-${rid[3]}T${rid[4]}:${rid[5]}:${rid[6]}-03:00`).toISOString();
  const iso = (json ? JSON.stringify(json) : "").match(ISO) || (mdText || "").match(ISO);
  if (iso) return new Date(iso[1] + "Z").toISOString();
  try {
    return fs.statSync(jsonPath).mtime.toISOString();
  } catch {
    return null;
  }
}

function checksOf(json) {
  const c = Array.isArray(json?.checks) ? json.checks : null;
  if (!c) return null;
  const items = c.map((x) => ({ name: String(x.name ?? x.label ?? ""), ok: Boolean(x.ok) }));
  return { ok: items.filter((x) => x.ok).length, total: items.length, failed: items.filter((x) => !x.ok).map((x) => x.name) };
}

function meta(f) {
  const jsonPath = path.join(f.dir, `${f.stem}.json`);
  const mdPath = path.join(f.dir, `${f.stem}.md`);
  const json = fs.existsSync(jsonPath) ? readJson(jsonPath) : null;
  const md = fs.existsSync(mdPath) ? fs.readFileSync(mdPath, "utf8") : null;
  const title = (md && md.match(/^#\s+(.+)$/m)?.[1]) || f.stem.replace(/_/g, " ");
  const task = json?.task || json?.tarefa || (title.match(/T-\d{3,4}/) || f.stem.match(/T-\d{3,4}/) || [null])[0];
  return {
    key: f.key, root: f.root, stem: f.stem, title, task,
    date: fileDate(json, md, fs.existsSync(jsonPath) ? jsonPath : mdPath),
    runId: json?.run_id || null, commit: json?.git_commit || null, dirty: json?.dirty ?? null,
    checks: checksOf(json), hasMd: Boolean(md), hasJson: Boolean(json),
    nota: json?.origem || json?.note || null,
    origem: f.origem || "local", pacote: f.pacote || null, baseKey: f.baseKey || f.key,
  };
}

function readRunLog() {
  const dir = RUNS_DIR();
  if (!fs.existsSync(dir)) return [];
  const out = [];
  for (const f of fs.readdirSync(dir).filter((x) => x.endsWith(".jsonl"))) {
    const lines = fs.readFileSync(path.join(dir, f), "utf8").split("\n").filter(Boolean);
    for (const line of lines) {
      try {
        const r = JSON.parse(line);
        out.push({ runId: r.run_id, date: r.ts ? new Date(r.ts.replace(/([+-]\d\d)(\d\d)$/, "$1:$2")).toISOString() : null,
          instrument: r.instrument, metric: r.metric, value: r.value, extra: r.extra ?? null,
          commit: r.git_commit, dirty: r.dirty, modelDigest: r.model_digest, seed: r.seed, gen: r.gen ?? null });
      } catch {
        // linha corrompida: fica de fora
      }
    }
  }
  return out;
}

/** Uma linha por execução do registro: métricas agrupadas, com valores de prévia. */
function aggregateRuns(lines) {
  const by = new Map();
  for (const l of lines) {
    if (!by.has(l.runId)) by.set(l.runId, []);
    by.get(l.runId).push(l);
  }
  return [...by.entries()].map(([runId, ls]) => {
    ls.sort((a, b) => String(a.date).localeCompare(String(b.date)));
    const metrics = {};
    for (const l of ls) (metrics[l.metric] ||= []).push(l.value);
    const preview = Object.entries(metrics).slice(0, 6).map(([m, vs]) => {
      const nums = vs.filter((v) => typeof v === "number");
      if (vs.length === 1) return { metric: m, value: typeof vs[0] === "object" && vs[0] !== null ? JSON.stringify(vs[0]) : vs[0] };
      if (nums.length === vs.length) return { metric: m, value: `${vs.length} valores, média ${num(nums.reduce((a, b) => a + b, 0) / nums.length, 3)}` };
      if (vs.every((v) => typeof v === "boolean")) return { metric: m, value: `${vs.filter(Boolean).length} de ${vs.length} verdadeiros` };
      return { metric: m, value: `${vs.length} valores` };
    });
    const f = ls[0];
    return { kind: "registro", runId, date: f.date, task: f.instrument, instrument: f.instrument, lines: ls.length,
      metrics: Object.keys(metrics).length, preview, commit: f.commit, dirty: ls.some((l) => l.dirty), modelDigest: f.modelDigest };
  });
}

const experimentOf = (key) => EXPERIMENTS.find((e) => e.arquivos.includes(key))?.id || null;
const rootById = (id) => roots().find((r) => r.id === id) || null;

function mountResultsRoutes(app) {
  app.get("/api/results", (_req, res) => {
    try {
      const all = listResultFiles().map(meta);
      const files = all.filter((f) => f.origem === "local");
      const cloud = all.filter((f) => f.origem === "nuvem");
      const byKey = Object.fromEntries(files.map((f) => [f.key, f]));
      const cache = {};
      const d = (key) => {
        if (!(key in cache)) {
          const [root, stem] = key.split("/");
          cache[key] = ROOTS[root] ? readJson(path.join(ROOTS[root], `${stem}.json`)) : null;
        }
        return cache[key];
      };
      const experiments = EXPERIMENTS.map((e) => {
        const fs_ = e.arquivos.map((k) => byKey[k]).filter(Boolean);
        let destaques = [];
        try {
          destaques = e.destaques(d);
        } catch (err) {
          destaques = [{ rotulo: "destaques", valor: "—", nota: `não lidos: ${err.message}` }];
        }
        const ok = fs_.reduce((a, f) => a + (f.checks?.ok || 0), 0);
        const total = fs_.reduce((a, f) => a + (f.checks?.total || 0), 0);
        const dates = fs_.map((f) => f.date).filter(Boolean).sort();
        return { id: e.id, titulo: e.titulo, tasks: e.tasks, teste: e.teste, objetivo: e.objetivo, pergunta: e.pergunta,
          destaques, checks: total ? { ok, total } : null, ultima: dates.at(-1) || null, arquivos: fs_,
          nuvem: cloud.filter((f) => e.arquivos.includes(f.baseKey)) };
      });
      const known = new Set(EXPERIMENTS.flatMap((e) => e.arquivos));
      res.json({ experiments, avulsos: files.filter((f) => !known.has(f.key)),
        nuvemAvulsos: cloud.filter((f) => !known.has(f.baseKey)), pacotes: roots().filter((r) => r.pacote).map((r) => r.pacote)
          .filter((p, i, a) => a.findIndex((q) => q.nome === p.nome) === i) });
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  app.get("/api/results/file/:root/:stem", (req, res) => {
    const { root, stem } = req.params;
    const r = rootById(root);
    if (!r || !/^[\w.+-]+$/.test(stem)) return res.status(404).json({ error: "resultado desconhecido" });
    const f = { root, stem, key: `${root}/${stem}`, dir: r.dir, baseKey: `${r.base}/${stem}`, origem: r.origem, pacote: r.pacote };
    const m = meta(f);
    if (!m.hasJson && !m.hasMd) return res.status(404).json({ error: "resultado desconhecido" });
    res.json({
      meta: { ...m, experiment: experimentOf(f.baseKey) },
      md: m.hasMd ? fs.readFileSync(path.join(f.dir, `${stem}.md`), "utf8") : null,
      json: m.hasJson ? readJson(path.join(f.dir, `${stem}.json`)) : null,
    });
  });

  app.get("/api/runs", (_req, res) => {
    try {
      const results = listResultFiles().map(meta).map((m) => ({ kind: m.origem === "nuvem" ? "nuvem" : "resultado", ...m, experiment: experimentOf(m.baseKey) }));
      const fileByRun = Object.fromEntries(results.filter((r) => r.runId).map((r) => [r.runId, r]));
      const log = aggregateRuns(readRunLog()).map((r) => {
        const f = fileByRun[r.runId];
        return { ...r, resultKey: f?.key || null, experiment: f?.experiment || null };
      });
      const all = [...results, ...log].sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")));
      res.json({ runs: all, runsDir: fs.existsSync(RUNS_DIR()) });
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  app.get("/api/runs/:runId", (req, res) => {
    if (!/^[\w-]+$/.test(req.params.runId)) return res.status(404).json({ error: "run desconhecida" });
    const lines = readRunLog().filter((l) => l.runId === req.params.runId);
    if (!lines.length) return res.status(404).json({ error: "run desconhecida" });
    res.json({ runId: req.params.runId, lines });
  });
}

module.exports = { mountResultsRoutes, EXPERIMENTS };
