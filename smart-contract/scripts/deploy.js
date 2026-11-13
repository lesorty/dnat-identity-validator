const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);
  console.log("Account balance:", (await hre.ethers.provider.getBalance(deployer.address)).toString());

  // Operador (executor, T-703): o único que registra derivados. Vem de DNAT_OPERATOR_ADDRESS; sem
  // ela, é quem implanta, que é a mesma conta do PRIVATE_KEY padrão do api-server (CVM1).
  const operator = hre.ethers.getAddress(process.env.DNAT_OPERATOR_ADDRESS || deployer.address);
  console.log("Operator (executor):", operator);

  // Deploy the contract
  const DnatMarketplace = await hre.ethers.getContractFactory("DnatMarketplace");
  const marketplace = await DnatMarketplace.deploy(operator);

  await marketplace.waitForDeployment();
  const address = await marketplace.getAddress();

  console.log("DnatMarketplace deployed to:", address);

  // Save deployment info
  const deploymentInfo = {
    network: hre.network.name,
    chainId: hre.network.config.chainId,
    contractAddress: address,
    deployer: deployer.address,
    admin: deployer.address,
    operator,
    deployedAt: new Date().toISOString(),
  };

  // Create deployments directory if it doesn't exist
  const deploymentsDir = path.join(__dirname, "..", "deployments");
  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir, { recursive: true });
  }

  // Save deployment info to file
  const deploymentFile = path.join(deploymentsDir, `${hre.network.name}.json`);
  fs.writeFileSync(deploymentFile, JSON.stringify(deploymentInfo, null, 2));

  // Also save ABI for client use
  const contractArtifact = await hre.artifacts.readArtifact("DnatMarketplace");
  const abiFile = path.join(deploymentsDir, "DnatMarketplace.abi.json");
  fs.writeFileSync(abiFile, JSON.stringify(contractArtifact.abi, null, 2));

  console.log("Deployment info saved to:", deploymentFile);
  console.log("ABI saved to:", abiFile);
  console.log("\nContract address:", address);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });

