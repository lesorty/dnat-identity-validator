/**
 * Rotas de leitura da interface (web/): modelos e derivados, o Juiz e os jobs de uma identidade.
 *
 * Só leitura e só o que cada papel pode ver (E14 §7–§8, decisões 7 e 8):
 *   GET /api/models     bases custodiadas, com a referência do pai (depositada ou não) e os derivados
 *                       julgados de cada uma: veredito, se está usável, se foi revogado, recibo em hashes.
 *   GET /api/judge      versões do Juiz liberadas (lista permitida), pacote da bateria e referências
 *                       por base: digests e datas, nunca os URIs cifrados nem o conteúdo.
 *   GET /api/my/jobs    ASSINADO: os jobs da identidade que pede, com o estado do derivado e o
 *                       veredito, sem stdout, stderr, motivos nem alertas (o oráculo do atacante).
 *   GET /api/quota-rules  saldo inicial, reserva e custo por desfecho.
 */
const fs = require("node:fs");
const path = require("node:path");

const VERDICTS = ["pending", "approved", "rejected", "inconclusive"];
const ASSET_TYPES = { dataset: 0, application: 1, model: 2, derivative: 3 };

function readJson(p, fallback) {
  try {
    return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, "utf8")) : fallback;
  } catch {
    return fallback;
  }
}

const strip0x = (h) => String(h || "").replace(/^0x/i, "").toLowerCase();

async function derivativeView(contract, asset) {
  const id = BigInt(asset.id);
  const [info, usable, revoked] = await Promise.all([
    contract.getDerivative(id),
    contract.isDerivativeUsable(id).catch(() => false),
    contract.derivativeRevoked(id).catch(() => false),
  ]);
  return {
    id: String(asset.id),
    title: asset.title,
    parentId: info.parentId.toString(),
    verdict: VERDICTS[Number(info.verdict)] || "pending",
    usable,
    revoked,
    active: asset.active,
    decidedAt: Number(info.decidedAt) ? new Date(Number(info.decidedAt) * 1000).toISOString() : null,
    receipt: {
      derivativeHash: strip0x(info.derivativeHash),
      parentReferenceHash: strip0x(info.parentReferenceHash),
      judgeHash: strip0x(info.judgeHash),
      batteryCommitment: strip0x(info.batteryCommitment),
      preregHash: strip0x(info.preregHash),
      verdictHash: strip0x(info.verdictHash),
      identityId: strip0x(info.identityId),
    },
  };
}

function referenceView(ref) {
  return ref ? { digest: ref.digest, source: ref.source || "", createdAtUtc: ref.createdAtUtc || null } : null;
}

/**
 * Monta as rotas no app. deps: {contract, listAssets, requireSignedRequest, paths: {references,
 * battery, allowlist, executions}, loadAllowlist, quota: {initialBalance, reserve, costs, difficulty}}.
 */
function mountUiRoutes(app, deps) {
  const { contract, listAssets, requireSignedRequest, paths, loadAllowlist, quota } = deps;

  app.get("/api/models", async (_req, res) => {
    try {
      const { all } = await listAssets();
      const refs = readJson(paths.references, {}).references || {};
      const derivs = await Promise.all(
        all.filter((a) => a.assetType === ASSET_TYPES.derivative).map((a) => derivativeView(contract, a)),
      );
      const bases = all
        .filter((a) => a.assetType === ASSET_TYPES.model)
        .map((a) => ({
          id: String(a.id),
          title: a.title,
          description: a.description,
          owner: a.owner,
          digest: strip0x(a.contentHash),
          active: a.active,
          reference: referenceView(refs[String(a.id)]),
          derivatives: derivs.filter((d) => d.parentId === String(a.id)).sort((x, y) => Number(y.id) - Number(x.id)),
        }));
      const known = new Set(bases.map((b) => b.id));
      res.json({ bases, orphans: derivs.filter((d) => !known.has(d.parentId)) });
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  app.get("/api/judge", (_req, res) => {
    let releases = [];
    let allowlistError = null;
    try {
      releases = loadAllowlist(paths.allowlist).map((j) => ({
        judgeHash: j.judgeHash,
        preregSha256: j.preregSha256,
        batteryCommitment: j.batteryCommitment,
        evaluatorKind: j.evaluatorKind,
        evaluatorDigest: j.evaluatorDigest,
        batteryPackDigest: j.batteryPackDigest,
        note: j.note,
      }));
    } catch (e) {
      allowlistError = fs.existsSync(paths.allowlist) ? e.message : "nenhum Juiz liberado ainda";
    }
    const battery = readJson(paths.battery, null);
    const refs = readJson(paths.references, {}).references || {};
    res.json({
      releases,
      allowlistError,
      battery: battery ? { digest: battery.digest, source: battery.source || "", createdAtUtc: battery.createdAtUtc || null } : null,
      references: Object.fromEntries(Object.entries(refs).map(([k, v]) => [k, referenceView(v)])),
    });
  });

  app.get("/api/quota-rules", (_req, res) => res.json(quota));

  app.get("/api/my/jobs", requireSignedRequest, (req, res) => {
    try {
      const root = paths.executions;
      const ids = fs.existsSync(root)
        ? fs.readdirSync(root, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name)
        : [];
      const jobs = [];
      for (const id of ids.sort().reverse()) {
        const m = readJson(path.join(root, id, "metadata.json"), null);
        if (!m || m.identityId !== req.identity.id) continue;
        const d = m.derivative || null;
        jobs.push({
          executionId: id,
          createdAtUtc: m.createdAtUtc || null,
          status: m.status || "unknown",
          parentModelId: m.parentModelId || null,
          derivative: d ? { status: d.status || null, verdict: d.verdict || null, assetId: d.assetId || null, digest: d.digest || null } : null,
          verdict: m.judge?.outcome || d?.verdict || null,
        });
      }
      res.json({ identityId: req.identity.id, jobs });
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });
}

module.exports = { mountUiRoutes, VERDICTS, ASSET_TYPES };
