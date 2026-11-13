/* T-701: tipos Model e Derivative em AssetType e campos do derivado (T-702 absorvida).
 * O derivado entra pelo caminho real, registerDerivative chamado pelo operador (T-703). */
const assert = require("node:assert");
const { ethers } = require("hardhat");

const AssetType = { Dataset: 0, Application: 1, Model: 2, Derivative: 3 };
const Verdict = { Pending: 0, Approved: 1, Rejected: 2, Inconclusive: 3 };
const h = (s) => ethers.keccak256(ethers.toUtf8Bytes(s));

async function register(contract, signer, assetType, title, price = 0n) {
  const tx = await contract
    .connect(signer)
    .registerAsset(assetType, title, "", `ipfs://${title}`, `ipfs://${title}-m`, h(title), price, "0x");
  const receipt = await tx.wait();
  const ev = receipt.logs.map((l) => contract.interface.parseLog(l)).find((e) => e && e.name === "AssetRegistered");
  return ev.args.id;
}

describe("DnatMarketplace: tipos Model e Derivative (T-701)", function () {
  let contract;
  let owner;
  let other;
  let operator;

  beforeEach(async function () {
    [owner, other, operator] = await ethers.getSigners();
    contract = await ethers.deployContract("DnatMarketplace", [operator.address]);
  });

  const registerDerivative = (info) =>
    contract.connect(operator).registerDerivative(info, other.address, "derivado", "ipfs://derivado");

  it("Dataset e Application mantêm os valores 0 e 1 e o fluxo de compra", async function () {
    const d = await register(contract, owner, AssetType.Dataset, "dados", 10n);
    const a = await register(contract, owner, AssetType.Application, "app", 5n);
    assert.strictEqual(Number((await contract.getAsset(d)).assetType), 0);
    assert.strictEqual(Number((await contract.getAsset(a)).assetType), 1);

    await (await contract.connect(other).purchaseAccess(d, a, { value: 15n })).wait();
    assert.strictEqual(await contract.hasAccessByIds(other.address, d, a), true);
  });

  it("registerAsset aceita Model, e purchaseAccess não o aceita como dataset nem como aplicação", async function () {
    const m = await register(contract, owner, AssetType.Model, "base");
    const d = await register(contract, owner, AssetType.Dataset, "dados");
    const a = await register(contract, owner, AssetType.Application, "app");
    assert.strictEqual(Number((await contract.getAsset(m)).assetType), AssetType.Model);

    await assert.rejects(contract.purchaseAccess(m, a), /datasetId is not dataset/);
    await assert.rejects(contract.purchaseAccess(d, m), /applicationId is not application/);
  });

  it("registerAsset recusa Derivative: o derivado não nasce ativo sem veredito", async function () {
    await assert.rejects(register(contract, other, AssetType.Derivative, "derivado"), /Derivative only via executor/);
  });

  it("getDerivative devolve os campos gravados e o evento DerivativeRegistered os repete", async function () {
    const parentId = await register(contract, owner, AssetType.Model, "base");
    const info = {
      parentId,
      parentReferenceHash: h("referencia"),
      derivativeHash: h("derivado"),
      judgeHash: h("juiz"),
      batteryCommitment: h("bateria"),
      preregHash: h("prereg"),
      datasetHash: h("dataset"),
      verdictHash: h("verdict.json"),
      identityId: h("identidade"),
      verdict: Verdict.Rejected,
      decidedAt: 1_700_000_000n,
    };
    const receipt = await (await registerDerivative(info)).wait();
    const ev = receipt.logs.map((l) => contract.interface.parseLog(l)).find((e) => e && e.name === "DerivativeRegistered");
    const id = ev.args.id;
    assert.strictEqual(ev.args.parentId, parentId);

    const got = await contract.getDerivative(id);
    for (const [k, v] of Object.entries(info)) {
      assert.strictEqual(got[k].toString(), v.toString(), `campo ${k}`);
      assert.strictEqual(ev.args.info[k].toString(), v.toString(), `evento ${k}`);
    }
    assert.strictEqual(Number((await contract.getAsset(id)).assetType), AssetType.Derivative);
  });

  it("getDerivative reverte para asset que não é Derivative ou não existe", async function () {
    const m = await register(contract, owner, AssetType.Model, "base");
    await assert.rejects(contract.getDerivative(m), /Not a derivative/);
    await assert.rejects(contract.getDerivative(999n), /Asset not found/);
  });

  it("um derivado sem veredito lê Pending (o zero do enum)", async function () {
    const parentId = await register(contract, owner, AssetType.Model, "base");
    const zero = ethers.ZeroHash;
    const receipt = await (
      await registerDerivative({
        parentId,
        parentReferenceHash: zero,
        derivativeHash: h("d"),
        judgeHash: zero,
        batteryCommitment: zero,
        preregHash: zero,
        datasetHash: zero,
        verdictHash: zero,
        identityId: zero,
        verdict: Verdict.Pending,
        decidedAt: 0n,
      })
    ).wait();
    const id = receipt.logs.map((l) => contract.interface.parseLog(l)).find((e) => e && e.name === "DerivativeRegistered").args.id;
    assert.strictEqual(Number((await contract.getDerivative(id)).verdict), Verdict.Pending);
  });
});
