/* Testes 10 e 11 (P6): o preço da identidade e o atacante com muitas identidades. Rodam os roteiros
 * com parâmetros pequenos e conferem as contas com entradas sintéticas.
 */
const assert = require("node:assert");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const t10 = require("../e2e/t10_preco_identidade");
const t11 = require("../e2e/t11_atacante_sybil");

describe("Teste 10: o preço da identidade", function () {
  this.timeout(120000);

  it("lei do custo: hashes iguais a 2^d dão inclinação 1 e razão 1", function () {
    const rows = [16, 17, 18, 19, 20].map((d) => ({ difficulty: d, hashes: [2 ** d, 2 ** d] }));
    const law = t10.costLaw(rows);
    assert.ok(Math.abs(law.slope - 1) < 1e-9);
    assert.ok(Math.abs(law.pooledRatio - 1) < 1e-9);
    assert.ok(law.slopeStdErr > 0);
  });

  it("lei do custo: hashes constantes (sem trabalho) dão inclinação 0", function () {
    const law = t10.costLaw([16, 18, 20].map((d) => ({ difficulty: d, hashes: [1000, 1000] })));
    assert.ok(Math.abs(law.slope) < 1e-9);
  });

  it("extrapolação: 2^d ÷ taxa e o menor d que custa o alvo", function () {
    const x = t10.extrapolate({ single: 2 ** 20, multi: { workers: 4, hashesPerSecond: 2 ** 22 }, gpu: 2 ** 30, difficulties: [30] });
    assert.deepStrictEqual(x.rates.map((r) => r.who), ["1 núcleo", "4 núcleos", "GPU"]);
    assert.strictEqual(x.rows[0].seconds["1 núcleo"], 2 ** 10);
    assert.strictEqual(x.rows[0].seconds["4 núcleos"], 2 ** 8);
    // 1 h = 3600 s; com 2^20 hashes/s, 2^d ≥ 3600·2^20 ⇔ d ≥ 20 + log2(3600) ≈ 31,81
    assert.strictEqual(x.reference.find((r) => r.hours === 1).difficulty["1 núcleo"], 32);
  });

  it("conferir uma prova é um hash e não depende de d", function () {
    const v = t10.verifyCost([8, 12], 2000);
    assert.ok(v.every((r) => r.valid && r.microseconds > 0 && r.microseconds < 1000));
  });

  it("a prova não se reaproveita: outra chave 400, outra implantação 400, chave repetida 409", function () {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-t10-test-"));
    try {
      const reuse = t10.reuseChecks(path.join(dir, "identities.json"), 12);
      assert.deepStrictEqual(reuse.map((c) => c.status), [201, 400, 400, 409]);
    } catch (e) {
      // d = 12: uma prova serve por acaso para outra chave com chance 2^-12; repete uma vez
      const reuse = t10.reuseChecks(path.join(dir, `identities-${crypto.randomUUID()}.json`), 12);
      assert.deepStrictEqual(reuse.map((c) => c.status), [201, 400, 400, 409], e.message);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it("o roteiro inteiro, pequeno: tabela, extrapolação, conferências e Markdown", async function () {
    const r = await t10.run({ minBits: 8, maxBits: 11, reps: 3, workers: 2, perWorker: 1 << 14, gpuRate: null }, () => {});
    assert.strictEqual(r.bench.rows.length, 4);
    assert.ok(r.bench.rows.every((row) => row.hashes.length === 3));
    assert.ok(r.verify.every((v) => v.valid));
    assert.ok(r.reuse.every((c) => c.ok));
    assert.ok(r.extrapolation.rows.some((x) => x.difficulty === 32));
    const md = t10.markdown(r);
    assert.match(md, /# Teste 10: o preço da identidade/);
    assert.match(md, /d de referência/);
  });
});

describe("Teste 11: o atacante com muitas identidades", function () {
  this.timeout(120000);

  it("tentativas por identidade pela regra do livro: 4 reprovados, 8 inconclusivos, 16 aprovados", function () {
    assert.strictEqual(t11.attemptsPerIdentity("rejected"), 4);
    assert.strictEqual(t11.attemptsPerIdentity("inconclusive"), 8);
    assert.strictEqual(t11.attemptsPerIdentity("approved"), 16);
    assert.strictEqual(t11.attemptsPerIdentity("failure"), Infinity);
  });

  it("economia: o escape custa (honesto ÷ (k1·e)) aprovações honestas, em qualquer d", function () {
    const econ = t11.economics({ rate1: 2 ** 20, rateN: 2 ** 22, workersN: 4, k1Rejected: 4, k1Inconclusive: 8, honest: 16,
      escapeRates: [0.01], difficulties: [20, 30], budgetsHours: [24] });
    for (const row of econ.perD) {
      assert.strictEqual(row.attacker[0].ratioToHonest, 400);
      assert.ok(Math.abs(row.attacker[0].perEscapeSeconds - row.identitySeconds / 0.04) < 1e-6);
    }
    const b = econ.budgets[0];
    assert.strictEqual(b.identities, Math.floor((24 * 3600 * 2 ** 22) / 2 ** 30));
    assert.strictEqual(b.attempts, b.identities * 4);
    assert.ok(Math.abs(b.pEscape[0].p - (1 - 0.99 ** b.attempts)) < 1e-12);
  });

  it("o roteiro contra a API: atacantes param em 4, honestos em 16, truques recusados", async function () {
    const r = await t11.run({ difficulty: 8, attackers: 3, honest: 1, t10Path: null, log: () => {} });
    for (const c of r.checks) assert.ok(c.ok, c.name);
    assert.strictEqual(r.attackerRows.reduce((s, x) => s + x.accepted, 0), 12);
    assert.match(t11.markdown(r), /# Teste 11/);
  });
});
