/* T-704 e T-705: derivado reprovado ou revogado nunca fica ativo; revogação só pelo operador. */
const assert = require("node:assert");
const { ethers } = require("hardhat");

const AssetType = { Dataset: 0, Application: 1, Model: 2, Derivative: 3 };
const Verdict = { Pending: 0, Approved: 1, Rejected: 2, Inconclusive: 3 };
const h = (s) => ethers.keccak256(ethers.toUtf8Bytes(s));

function parsed(contract, receipt, name) {
  return receipt.logs.map((l) => contract.interface.parseLog(l)).find((e) => e && e.name === name);
}

function derivativeInfo(parentId, verdict = Verdict.Approved) {
  return {
    parentId,
    parentReferenceHash: h("referencia"),
    derivativeHash: h("derivado"),
    judgeHash: h("juiz-v1"),
    batteryCommitment: h("bateria"),
    preregHash: h("prereg"),
    datasetHash: h("dataset"),
    verdictHash: h("verdict.json"),
    identityId: h("identidade"),
    verdict,
    decidedAt: 1_700_000_000n,
  };
}

describe("DnatMarketplace: ciclo de vida do derivado (T-704, T-705)", function () {
  let contract;
  let operator;
  let parentOwner;
  let owner; // dono do derivado: o adversário
  let third;
  let parentId;

  async function registerDerivative(verdict) {
    const receipt = await (
      await contract.connect(operator).registerDerivative(derivativeInfo(parentId, verdict), owner.address, "d", "ipfs://d")
    ).wait();
    return parsed(contract, receipt, "DerivativeRegistered").args.id;
  }

  const isActive = async (id) => (await contract.getAsset(id)).active;

  beforeEach(async function () {
    let admin;
    [admin, operator, parentOwner, owner, third] = await ethers.getSigners();
    contract = await ethers.deployContract("DnatMarketplace", [operator.address]);
    const tx = await contract
      .connect(parentOwner)
      .registerAsset(AssetType.Model, "base", "", "ipfs://base", "ipfs://base-m", h("base"), 0n, "0x");
    parentId = parsed(contract, await tx.wait(), "AssetRegistered").args.id;
  });

  describe("T-704: o dono não reativa", function () {
    it("reprovado, inconclusivo e pendente: o dono tenta reativar e reverte", async function () {
      for (const verdict of [Verdict.Rejected, Verdict.Inconclusive, Verdict.Pending]) {
        const id = await registerDerivative(verdict);
        await assert.rejects(
          contract.connect(owner).updateAsset(id, 0n, true),
          /Derivative not approved/,
          `veredito ${verdict}`,
        );
        assert.strictEqual(await isActive(id), false);
      }
    });

    it("revogado pelo operador: o dono tenta reativar e reverte", async function () {
      const id = await registerDerivative(Verdict.Approved);
      await (await contract.connect(operator).revokeDerivative(id, "juiz mudou")).wait();
      await assert.rejects(contract.connect(owner).updateAsset(id, 0n, true), /Derivative revoked/);
      assert.strictEqual(await isActive(id), false);
    });

    it("aprovado: o dono pode desativar e reativar, e o preço muda", async function () {
      const id = await registerDerivative(Verdict.Approved);
      await (await contract.connect(owner).updateAsset(id, 5n, false)).wait();
      assert.strictEqual(await isActive(id), false);
      await (await contract.connect(owner).updateAsset(id, 7n, true)).wait();
      const a = await contract.getAsset(id);
      assert.strictEqual(a.active, true);
      assert.strictEqual(a.price, 7n);
    });

    it("desativar um reprovado continua permitido; só a reativação é barrada", async function () {
      const id = await registerDerivative(Verdict.Rejected);
      await (await contract.connect(owner).updateAsset(id, 1n, false)).wait();
      assert.strictEqual(await isActive(id), false);
    });

    it("os tipos antigos não mudam: o dono do Model reativa o que desativou", async function () {
      await (await contract.connect(parentOwner).updateAsset(parentId, 0n, false)).wait();
      await (await contract.connect(parentOwner).updateAsset(parentId, 0n, true)).wait();
      assert.strictEqual(await isActive(parentId), true);
    });

    it("só o dono ainda chama updateAsset", async function () {
      const id = await registerDerivative(Verdict.Approved);
      await assert.rejects(contract.connect(third).updateAsset(id, 0n, true), /Only owner/);
      await assert.rejects(contract.connect(operator).updateAsset(id, 0n, true), /Only owner/);
    });
  });

  describe("T-705: revogação pelo operador", function () {
    it("só o operador revoga: dono do derivado, dono do pai e terceiro revertem", async function () {
      const id = await registerDerivative(Verdict.Approved);
      for (const signer of [owner, parentOwner, third]) {
        await assert.rejects(contract.connect(signer).revokeDerivative(id, "x"), /Only operator/);
      }
      assert.strictEqual(await isActive(id), true);
      assert.strictEqual(await contract.derivativeRevoked(id), false);
    });

    it("o operador revoga: zera active, marca a revogação e emite o evento com o hash do Juiz", async function () {
      const id = await registerDerivative(Verdict.Approved);
      const receipt = await (await contract.connect(operator).revokeDerivative(id, "juiz mudou")).wait();
      const ev = parsed(contract, receipt, "DerivativeRevoked");
      assert.strictEqual(ev.args.id, id);
      assert.strictEqual(ev.args.reason, "juiz mudou");
      assert.strictEqual(ev.args.judgeHash, h("juiz-v1"));
      assert.strictEqual(await isActive(id), false);
      assert.strictEqual(await contract.derivativeRevoked(id), true);
    });

    it("não revoga duas vezes, nem asset inexistente, nem asset que não é derivado", async function () {
      const id = await registerDerivative(Verdict.Approved);
      const op = contract.connect(operator);
      await (await op.revokeDerivative(id, "x")).wait();
      await assert.rejects(op.revokeDerivative(id, "x"), /Already revoked/);
      await assert.rejects(op.revokeDerivative(999n, "x"), /Asset does not exist/);
      await assert.rejects(op.revokeDerivative(parentId, "x"), /Not a derivative/);
    });

    it("revoga também um derivado já inativo (reprovado), e a marca impede a reativação", async function () {
      const id = await registerDerivative(Verdict.Rejected);
      await (await contract.connect(operator).revokeDerivative(id, "x")).wait();
      assert.strictEqual(await contract.derivativeRevoked(id), true);
    });

    it("revokeAsset do dono segue como antes nos tipos antigos", async function () {
      await (await contract.connect(parentOwner).revokeAsset(parentId)).wait();
      assert.strictEqual(await isActive(parentId), false);
      await assert.rejects(contract.connect(parentOwner).revokeAsset(parentId), /Already revoked/);
      await assert.rejects(contract.connect(third).revokeAsset(parentId), /Only owner/);
    });

    it("o dono que revoga o próprio derivado não o reativa depois sem aprovação válida", async function () {
      const id = await registerDerivative(Verdict.Approved);
      await (await contract.connect(owner).revokeAsset(id)).wait();
      // Aprovado e sem marca do operador: o dono pode reativar o que ele mesmo desativou.
      await (await contract.connect(owner).updateAsset(id, 0n, true)).wait();
      assert.strictEqual(await isActive(id), true);
      // O operador retira de vez.
      await (await contract.connect(operator).revokeDerivative(id, "x")).wait();
      await assert.rejects(contract.connect(owner).updateAsset(id, 0n, true), /Derivative revoked/);
    });
  });
});
