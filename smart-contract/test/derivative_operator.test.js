/* T-703: papel de operador (executor) e registerDerivative só por ele (R10, T-105). */
const assert = require("node:assert");
const { ethers } = require("hardhat");

const AssetType = { Dataset: 0, Application: 1, Model: 2, Derivative: 3 };
const Verdict = { Pending: 0, Approved: 1, Rejected: 2, Inconclusive: 3 };
const h = (s) => ethers.keccak256(ethers.toUtf8Bytes(s));

function parsed(contract, receipt, name) {
  return receipt.logs.map((l) => contract.interface.parseLog(l)).find((e) => e && e.name === name);
}

async function register(contract, signer, assetType, title) {
  const tx = await contract
    .connect(signer)
    .registerAsset(assetType, title, "", `ipfs://${title}`, `ipfs://${title}-m`, h(title), 0n, "0x");
  return parsed(contract, await tx.wait(), "AssetRegistered").args.id;
}

function derivativeInfo(parentId, verdict = Verdict.Approved) {
  return {
    parentId,
    parentReferenceHash: h("referencia"),
    derivativeHash: h("derivado"),
    judgeHash: h("juiz"),
    batteryCommitment: h("bateria"),
    preregHash: h("prereg"),
    datasetHash: h("dataset"),
    verdictHash: h("verdict.json"),
    identityId: h("identidade"),
    verdict,
    decidedAt: 1_700_000_000n,
  };
}

describe("DnatMarketplace: operador e registerDerivative (T-703)", function () {
  let contract;
  let admin;
  let operator;
  let parentOwner;
  let user;
  let third;
  let parentId;

  beforeEach(async function () {
    [admin, operator, parentOwner, user, third] = await ethers.getSigners();
    contract = await ethers.deployContract("DnatMarketplace", [operator.address]);
    parentId = await register(contract, parentOwner, AssetType.Model, "base");
  });

  it("o construtor fixa o operador; quem implanta é o admin; operador zero é recusado", async function () {
    assert.strictEqual(await contract.operator(), operator.address);
    assert.strictEqual(await contract.admin(), admin.address);
    const factory = await ethers.getContractFactory("DnatMarketplace");
    await assert.rejects(factory.deploy(ethers.ZeroAddress), /Operator required/);
  });

  it("só o operador registra derivado: dono do pai, usuário, terceiro e admin revertem", async function () {
    const info = derivativeInfo(parentId);
    for (const signer of [parentOwner, user, third, admin]) {
      await assert.rejects(
        contract.connect(signer).registerDerivative(info, user.address, "derivado", "ipfs://d"),
        /Only operator/,
        `chamada de ${signer.address} deveria reverter`,
      );
    }
    assert.strictEqual(await contract.nextAssetId(), parentId);
  });

  it("o operador registra: Asset e DerivativeInfo gravados batem com a chamada, e os eventos saem", async function () {
    const info = derivativeInfo(parentId);
    const receipt = await (
      await contract.connect(operator).registerDerivative(info, user.address, "derivado aprovado", "ipfs://cifrado")
    ).wait();
    const ev = parsed(contract, receipt, "DerivativeRegistered");
    const id = ev.args.id;
    assert.strictEqual(id, parentId + 1n);
    assert.strictEqual(ev.args.parentId, parentId);
    const reg = parsed(contract, receipt, "AssetRegistered");
    assert.strictEqual(reg.args.id, id);
    assert.strictEqual(Number(reg.args.assetType), AssetType.Derivative);
    assert.strictEqual(reg.args.owner, user.address);

    const got = await contract.getDerivative(id);
    for (const [k, v] of Object.entries(info)) {
      assert.strictEqual(got[k].toString(), v.toString(), `campo ${k}`);
      assert.strictEqual(ev.args.info[k].toString(), v.toString(), `evento ${k}`);
    }

    const a = await contract.getAsset(id);
    assert.strictEqual(Number(a.assetType), AssetType.Derivative);
    assert.strictEqual(a.owner, user.address);
    assert.strictEqual(a.title, "derivado aprovado");
    assert.strictEqual(a.encryptedUri, "ipfs://cifrado");
    assert.strictEqual(a.contentHash, info.derivativeHash);
    assert.strictEqual(a.price, 0n);
    assert.strictEqual(a.active, true);
  });

  it("só o aprovado nasce ativo: reprovado, inconclusivo e pendente nascem inativos", async function () {
    for (const verdict of [Verdict.Rejected, Verdict.Inconclusive, Verdict.Pending]) {
      const receipt = await (
        await contract.connect(operator).registerDerivative(derivativeInfo(parentId, verdict), user.address, "d", "ipfs://d")
      ).wait();
      const id = parsed(contract, receipt, "DerivativeRegistered").args.id;
      assert.strictEqual((await contract.getAsset(id)).active, false, `veredito ${verdict}`);
      assert.strictEqual(Number((await contract.getDerivative(id)).verdict), verdict);
    }
  });

  it("o pai tem de ser um Model existente e ativo; derivado de derivado não entra", async function () {
    const reg = (info) => contract.connect(operator).registerDerivative(info, user.address, "d", "ipfs://d");
    await assert.rejects(reg(derivativeInfo(999n)), /Parent not found/);

    const dataset = await register(contract, parentOwner, AssetType.Dataset, "dados");
    await assert.rejects(reg(derivativeInfo(dataset)), /Parent is not a model/);

    const receipt = await (await reg(derivativeInfo(parentId))).wait();
    const derivativeId = parsed(contract, receipt, "DerivativeRegistered").args.id;
    await assert.rejects(reg(derivativeInfo(derivativeId)), /Parent is not a model/);

    await (await contract.connect(parentOwner).revokeAsset(parentId)).wait();
    await assert.rejects(reg(derivativeInfo(parentId)), /Parent inactive/);
  });

  it("dono zero, título vazio e hash do derivado zero são recusados", async function () {
    const info = derivativeInfo(parentId);
    const op = contract.connect(operator);
    await assert.rejects(op.registerDerivative(info, ethers.ZeroAddress, "d", "ipfs://d"), /Owner required/);
    await assert.rejects(op.registerDerivative(info, user.address, "", "ipfs://d"), /Title required/);
    await assert.rejects(
      op.registerDerivative({ ...info, derivativeHash: ethers.ZeroHash }, user.address, "d", "ipfs://d"),
      /Derivative hash required/,
    );
  });

  it("só o admin troca o operador; o antigo perde o papel e o novo passa a registrar", async function () {
    await assert.rejects(contract.connect(operator).setOperator(third.address), /Only admin/);
    await assert.rejects(contract.connect(third).setOperator(third.address), /Only admin/);
    await assert.rejects(contract.connect(admin).setOperator(ethers.ZeroAddress), /Operator required/);

    const receipt = await (await contract.connect(admin).setOperator(third.address)).wait();
    const ev = parsed(contract, receipt, "OperatorChanged");
    assert.strictEqual(ev.args.previousOperator, operator.address);
    assert.strictEqual(ev.args.newOperator, third.address);
    assert.strictEqual(await contract.operator(), third.address);

    const info = derivativeInfo(parentId);
    await assert.rejects(
      contract.connect(operator).registerDerivative(info, user.address, "d", "ipfs://d"),
      /Only operator/,
    );
    await (await contract.connect(third).registerDerivative(info, user.address, "d", "ipfs://d")).wait();
  });
});
