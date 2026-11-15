/* Chave de acesso por ids (revisão de 15/11): com keccak256(abi.encodePacked(uriD, uriA, user)),
 * um par de ativos com URIs que se concatenam igual, ou com o mesmo URI da vítima, comprado a
 * preço zero, dava acesso ao par pago da vítima. */
const assert = require("node:assert");
const { ethers } = require("hardhat");

const AssetType = { Dataset: 0, Application: 1 };
const h = (s) => ethers.keccak256(ethers.toUtf8Bytes(s));

describe("DnatMarketplace: chave de acesso por ids", function () {
  let contract, victimOwner, attacker;
  const reg = async (who, type, uri, price) => {
    const r = await (await contract.connect(who).registerAsset(type, "t", "", uri, "m", h(uri), price, "0x")).wait();
    return r.logs.map((l) => contract.interface.parseLog(l)).find((e) => e && e.name === "AssetRegistered").args.id;
  };

  beforeEach(async function () {
    let admin, operator;
    [admin, operator, victimOwner, attacker] = await ethers.getSigners();
    contract = await ethers.deployContract("DnatMarketplace", [operator.address]);
  });

  it("URIs que se concatenam igual não dão acesso ao par da vítima", async function () {
    const D = await reg(victimOwner, AssetType.Dataset, "ipfs://QmD", ethers.parseEther("1"));
    const A = await reg(victimOwner, AssetType.Application, "ipfs://QmA", ethers.parseEther("1"));
    // "ipfs://QmDipfs://Qm" + "A" == "ipfs://QmD" + "ipfs://QmA" em encodePacked
    const D2 = await reg(attacker, AssetType.Dataset, "ipfs://QmDipfs://Qm", 0);
    const A2 = await reg(attacker, AssetType.Application, "A", 0);
    await (await contract.connect(attacker).purchaseAccess(D2, A2)).wait();
    assert.strictEqual(await contract.hasAccessByIds(attacker.address, D2, A2), true);
    assert.strictEqual(await contract.hasAccessByIds(attacker.address, D, A), false);
    assert.strictEqual(await contract.hasAccess(attacker.address, "ipfs://QmD", "ipfs://QmA"), false);
  });

  it("um URI de dataset ou aplicação só é registrado uma vez", async function () {
    await reg(victimOwner, AssetType.Dataset, "ipfs://QmD", 0);
    await assert.rejects(reg(attacker, AssetType.Dataset, "ipfs://QmD", 0), /URI already registered/);
    await assert.rejects(reg(attacker, AssetType.Application, "ipfs://QmD", 0), /URI already registered/);
  });

  it("a consulta por URI segue funcionando para quem comprou", async function () {
    const D = await reg(victimOwner, AssetType.Dataset, "ipfs://QmD", 0);
    const A = await reg(victimOwner, AssetType.Application, "ipfs://QmA", 0);
    await (await contract.connect(attacker).purchaseAccess(D, A)).wait();
    assert.strictEqual(await contract.hasAccess(attacker.address, "ipfs://QmD", "ipfs://QmA"), true);
    assert.strictEqual(await contract.hasAccess(attacker.address, "ipfs://QmD", "ipfs://nada"), false);
  });
});
