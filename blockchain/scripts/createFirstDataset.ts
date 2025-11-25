import { network } from "hardhat";

async function main() {
  console.log("Connecting to the network to get ethers...");
  
  // 1. Get the ethers object using your suggested method
  const { ethers } = await network.connect();

  const contractAddress = process.env.CONTRACT_ADDRESS!; 
  
  console.log(`Connecting to contract at: ${contractAddress}`);

  const DatasetNFT = await ethers.getContractFactory("DatasetNFT");
  const contract = DatasetNFT.attach(contractAddress);

  console.log("Creating a new dataset...");

  const tx = await contract.createDataset(
    "Global Climate Indicators",
    "A dataset tracking key climate trends from 1958.",
    "Environment",
    "CSV",
    "ipfs://bafybeigdyrzt5sfp7udm7hu76uh7y26...", // Example IPFS CID
    ethers.parseEther("0.1") // Price in ETH (0.1 ETH)
  );

  console.log("Transaction sent, waiting for confirmation...");
  
  await tx.wait();

  console.log("✅ First dataset created successfully!");
  console.log("Transaction hash:", tx.hash);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});