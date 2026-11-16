require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

// `hardhat test`: as pastas temporárias dos testes (os.tmpdir(), que lê TMPDIR a cada chamada, e os
// processos filhos que herdam o ambiente) vão para uma pasta só desta execução, apagada no fim.
// Antes, cada execução da suíte deixava dezenas de /tmp/dnat-* (720 em 16/11).
if (process.argv.includes("test") && !process.env.DNAT_KEEP_TEST_TMP) {
  const fs = require("node:fs");
  const os = require("node:os");
  const path = require("node:path");
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "dnat-test-"));
  process.env.TMPDIR = root;
  process.on("exit", () => fs.rmSync(root, { recursive: true, force: true }));
}

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      viaIR: true,
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  networks: {
    hardhat: {
      chainId: 31337,
    },
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337,
    },
    // Add more networks as needed (e.g., sepolia, polygon, etc.)
    // sepolia: {
    //   url: process.env.SEPOLIA_RPC_URL || "",
    //   accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
    // },
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
};

