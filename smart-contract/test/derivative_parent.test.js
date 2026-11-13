/* T-707: derivado de um pai revogado deixa de valer, sem laço sobre os filhos (cascata preguiçosa). */
const assert = require("node:assert");
const { ethers } = require("hardhat");

const AssetType = { Dataset: 0, Application: 1, Model: 2, Derivative: 3 };
const Verdict = { Pending: 0, Approved: 1, Rejected: 2, Inconclusive: 3 };
const h = (s) => ethers.keccak256(ethers.toUtf8Bytes(s));
const parsed = (c, r, name) => r.logs.map((l) => c.interface.parseLog(l)).find((e) => e && e.name === name);

describe("DnatMarketplace: derivados de um pai revogado (T-707)", function () {
  let contract;
  let operator;
  let parentOwner;
  let owner;
  let parentId;

  const info = (verdict = Verdict.Approved, parent = parentId) => ({
    parentId: parent, parentReferenceHash: h("ref"), derivativeHash: h("d"), judgeHash: h("j"),
    batteryCommitment: h("b"), preregHash: h("p"), datasetHash: h("ds"), verdictHash: h("v"),
    identityId: h("id"), verdict, decidedAt: 1n,
  });
  const derive = async (verdict, parent) => {
    const r = await (await contract.connect(operator).registerDerivative(info(verdict, parent), owner.address, "d", "ipfs://d")).wait();
    return parsed(contract, r, "DerivativeRegistered").args.id;
  };
  const usable = (id) => contract.isDerivativeUsable(id);

  beforeEach(async function () {
    let admin;
    [admin, operator, parentOwner, owner] = await ethers.getSigners();
    contract = await ethers.deployContract("DnatMarketplace", [operator.address]);
    const r = await (await contract.connect(parentOwner)
      .registerAsset(AssetType.Model, "base", "", "ipfs://b", "ipfs://bm", h("base"), 0n, "0x")).wait();
    parentId = parsed(contract, r, "AssetRegistered").args.id;
  });

  it("aprovado com pai ativo é usável; reprovado, revogado ou inativo pelo dono não é", async function () {
    const ok = await derive(Verdict.Approved);
    assert.strictEqual(await usable(ok), true);
    assert.strictEqual(await usable(await derive(Verdict.Rejected)), false);
    const revoked = await derive(Verdict.Approved);
    await (await contract.connect(operator).revokeDerivative(revoked, "x")).wait();
    assert.strictEqual(await usable(revoked), false);
    const withdrawn = await derive(Verdict.Approved);
    await (await contract.connect(owner).updateAsset(withdrawn, 0n, false)).wait();
    assert.strictEqual(await usable(withdrawn), false);
  });

  it("revogar o pai derruba todos os filhos de uma vez, com gás que não cresce com o número de filhos", async function () {
    const kids = [];
    for (let i = 0; i < 5; i += 1) kids.push(await derive(Verdict.Approved));
    for (const k of kids) assert.strictEqual(await usable(k), true);
    const r = await (await contract.connect(parentOwner).revokeAsset(parentId)).wait();
    for (const k of kids) {
      assert.strictEqual(await usable(k), false);
      assert.strictEqual((await contract.getAsset(k)).active, true); // o estado próprio fica; o efetivo cai
    }
    // a revogação do pai não percorre os filhos: o gás é o de uma escrita só
    const other = await ethers.deployContract("DnatMarketplace", [operator.address]);
    const r0 = await (await other.connect(parentOwner)
      .registerAsset(AssetType.Model, "base", "", "ipfs://b", "ipfs://bm", h("base"), 0n, "0x")).wait();
    const lonely = parsed(other, r0, "AssetRegistered").args.id;
    const r1 = await (await other.connect(parentOwner).revokeAsset(lonely)).wait();
    assert.strictEqual(r.gasUsed, r1.gasUsed);
  });

  it("com o pai inativo, o dono não reativa o derivado; nem se cria derivado novo dele", async function () {
    const k = await derive(Verdict.Approved);
    await (await contract.connect(owner).updateAsset(k, 0n, false)).wait();
    await (await contract.connect(parentOwner).revokeAsset(parentId)).wait();
    await assert.rejects(contract.connect(owner).updateAsset(k, 0n, true), /Parent inactive/);
    await assert.rejects(derive(Verdict.Approved), /Parent inactive/);
  });

  it("isDerivativeUsable recusa asset inexistente ou que não é derivado", async function () {
    await assert.rejects(usable(999n), /Asset not found/);
    await assert.rejects(usable(parentId), /Not a derivative/);
  });
});
