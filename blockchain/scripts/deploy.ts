import { network } from "hardhat";

async function main() {
  console.log("Connecting to the network to get ethers...");
  
  // This is the pattern from your sample script.
  // We connect to the network to get an instance of the ethers object.
  const { ethers } = await network.connect();

  console.log("Deploying DatasetNFT contract...");
  
  const datasetNFT = await ethers.deployContract("DatasetNFT");

  await datasetNFT.waitForDeployment();

  console.log(
    `DatasetNFT contract deployed to: ${await datasetNFT.getAddress()}`
  );
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});