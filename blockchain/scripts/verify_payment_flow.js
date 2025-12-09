/**
 * Payment Flow Verification Script
 *
 * This script tests that payments from purchases and rentals
 * go directly to dataset owners, not stuck in the contract.
 *
 * Run: npx hardhat run scripts/verify_payment_flow.js --network sepolia
 */

const hre = require("hardhat");

async function main() {
  console.log("\n🔍 Payment Flow Verification\n");
  console.log("=".repeat(60));

  // Get signers
  const [deployer, owner, buyer, renter] = await hre.ethers.getSigners();

  console.log("\n📋 Accounts:");
  console.log("  Deployer:", deployer.address);
  console.log("  Owner:   ", owner.address);
  console.log("  Buyer:   ", buyer.address);
  console.log("  Renter:  ", renter.address);

  // Deploy contract
  console.log("\n📦 Deploying DatasetNFT contract...");
  const DatasetNFT = await hre.ethers.getContractFactory("DatasetNFT");
  const contract = await DatasetNFT.deploy();
  await contract.deployed();

  console.log("  ✅ Contract deployed at:", contract.address);

  // Create dataset as owner
  console.log("\n📝 Creating dataset...");
  const createTx = await contract.connect(owner).createDataset(
    "AI Training Dataset",
    "High-quality labeled data for ML training",
    "AI/ML",
    "CSV",
    "QmTestCID123456789",
    hre.ethers.utils.parseEther("0.1") // 0.1 ETH price
  );
  await createTx.wait();

  const tokenId = 1;
  console.log("  ✅ Dataset created with Token ID:", tokenId);
  console.log("  Price: 0.1 ETH");

  // Check initial balances
  console.log("\n💰 Initial Balances:");
  const ownerBalanceInitial = await hre.ethers.provider.getBalance(owner.address);
  const contractBalanceInitial = await hre.ethers.provider.getBalance(contract.address);
  console.log("  Owner:   ", hre.ethers.utils.formatEther(ownerBalanceInitial), "ETH");
  console.log("  Contract:", hre.ethers.utils.formatEther(contractBalanceInitial), "ETH");

  // === TEST 1: Purchase ===
  console.log("\n" + "=".repeat(60));
  console.log("TEST 1: Purchase Dataset");
  console.log("=".repeat(60));

  const ownerBalanceBeforePurchase = await hre.ethers.provider.getBalance(owner.address);

  console.log("\n🛒 Buyer purchasing dataset...");
  const purchaseTx = await contract.connect(buyer).purchaseDataset(tokenId, {
    value: hre.ethers.utils.parseEther("0.1")
  });
  const purchaseReceipt = await purchaseTx.wait();

  console.log("  ✅ Purchase transaction confirmed");
  console.log("  Transaction hash:", purchaseReceipt.transactionHash);

  // Check balances after purchase
  const ownerBalanceAfterPurchase = await hre.ethers.provider.getBalance(owner.address);
  const contractBalanceAfterPurchase = await hre.ethers.provider.getBalance(contract.address);

  const ownerPaymentReceived = ownerBalanceAfterPurchase.sub(ownerBalanceBeforePurchase);

  console.log("\n💰 Balances After Purchase:");
  console.log("  Owner:   ", hre.ethers.utils.formatEther(ownerBalanceAfterPurchase), "ETH");
  console.log("  Contract:", hre.ethers.utils.formatEther(contractBalanceAfterPurchase), "ETH");
  console.log("\n💸 Owner Received:", hre.ethers.utils.formatEther(ownerPaymentReceived), "ETH");

  // Verification
  console.log("\n✅ VERIFICATION:");
  if (ownerPaymentReceived.eq(hre.ethers.utils.parseEther("0.1"))) {
    console.log("  ✅ PASS: Owner received exactly 0.1 ETH");
  } else {
    console.log("  ❌ FAIL: Owner should have received 0.1 ETH, got", hre.ethers.utils.formatEther(ownerPaymentReceived));
  }

  if (contractBalanceAfterPurchase.eq(0)) {
    console.log("  ✅ PASS: Contract balance is 0 ETH (no funds trapped)");
  } else {
    console.log("  ⚠️  WARNING: Contract has", hre.ethers.utils.formatEther(contractBalanceAfterPurchase), "ETH");
  }

  // Check events
  const purchaseEvent = purchaseReceipt.events?.find(e => e.event === 'DatasetPurchased');
  if (purchaseEvent) {
    console.log("\n📡 DatasetPurchased Event:");
    console.log("  Token ID:", purchaseEvent.args.tokenId.toString());
    console.log("  Buyer:   ", purchaseEvent.args.buyer);
    console.log("  Seller:  ", purchaseEvent.args.seller);
    console.log("  Price:   ", hre.ethers.utils.formatEther(purchaseEvent.args.price), "ETH");

    if (purchaseEvent.args.seller === owner.address) {
      console.log("  ✅ PASS: Event shows correct seller (owner)");
    } else {
      console.log("  ❌ FAIL: Event seller doesn't match owner");
    }
  }

  // === TEST 2: Rental ===
  console.log("\n" + "=".repeat(60));
  console.log("TEST 2: Rent Dataset");
  console.log("=".repeat(60));

  // Set rental price
  console.log("\n⚙️  Setting rental price...");
  const setRentalTx = await contract.connect(owner).setRentalPrice(
    tokenId,
    hre.ethers.utils.parseEther("0.001") // 0.001 ETH per day
  );
  await setRentalTx.wait();
  console.log("  ✅ Rental price set to 0.001 ETH/day");

  const ownerBalanceBeforeRental = await hre.ethers.provider.getBalance(owner.address);

  console.log("\n🏠 Renter renting dataset for 7 days...");
  const rentTx = await contract.connect(renter).rentDataset(tokenId, 7, {
    value: hre.ethers.utils.parseEther("0.007") // 7 days * 0.001 ETH
  });
  const rentReceipt = await rentTx.wait();

  console.log("  ✅ Rental transaction confirmed");
  console.log("  Transaction hash:", rentReceipt.transactionHash);

  // Check balances after rental
  const ownerBalanceAfterRental = await hre.ethers.provider.getBalance(owner.address);
  const contractBalanceAfterRental = await hre.ethers.provider.getBalance(contract.address);

  const rentalPaymentReceived = ownerBalanceAfterRental.sub(ownerBalanceBeforeRental);

  console.log("\n💰 Balances After Rental:");
  console.log("  Owner:   ", hre.ethers.utils.formatEther(ownerBalanceAfterRental), "ETH");
  console.log("  Contract:", hre.ethers.utils.formatEther(contractBalanceAfterRental), "ETH");
  console.log("\n💸 Owner Received:", hre.ethers.utils.formatEther(rentalPaymentReceived), "ETH");

  // Verification
  console.log("\n✅ VERIFICATION:");
  if (rentalPaymentReceived.eq(hre.ethers.utils.parseEther("0.007"))) {
    console.log("  ✅ PASS: Owner received exactly 0.007 ETH");
  } else {
    console.log("  ❌ FAIL: Owner should have received 0.007 ETH, got", hre.ethers.utils.formatEther(rentalPaymentReceived));
  }

  if (contractBalanceAfterRental.eq(0)) {
    console.log("  ✅ PASS: Contract balance is still 0 ETH");
  } else {
    console.log("  ⚠️  WARNING: Contract has", hre.ethers.utils.formatEther(contractBalanceAfterRental), "ETH");
  }

  // Check rental event
  const rentalEvent = rentReceipt.events?.find(e => e.event === 'DatasetRented');
  if (rentalEvent) {
    console.log("\n📡 DatasetRented Event:");
    console.log("  Token ID:    ", rentalEvent.args.tokenId.toString());
    console.log("  Renter:      ", rentalEvent.args.renter);
    console.log("  Owner:       ", rentalEvent.args.owner);
    console.log("  Amount Paid: ", hre.ethers.utils.formatEther(rentalEvent.args.amountPaid), "ETH");
    console.log("  Expires At:  ", new Date(rentalEvent.args.expiresAt.toNumber() * 1000).toISOString());

    if (rentalEvent.args.owner === owner.address) {
      console.log("  ✅ PASS: Event shows correct owner");
    } else {
      console.log("  ❌ FAIL: Event owner doesn't match dataset owner");
    }
  }

  // === FINAL SUMMARY ===
  console.log("\n" + "=".repeat(60));
  console.log("FINAL SUMMARY");
  console.log("=".repeat(60));

  const totalOwnerReceived = ownerPaymentReceived.add(rentalPaymentReceived);
  const finalContractBalance = await hre.ethers.provider.getBalance(contract.address);

  console.log("\n💰 Total Payments:");
  console.log("  Purchase:       0.1 ETH");
  console.log("  Rental (7 days): 0.007 ETH");
  console.log("  Total Expected:  0.107 ETH");
  console.log("\n💸 Owner Received: ", hre.ethers.utils.formatEther(totalOwnerReceived), "ETH");
  console.log("📦 Contract Balance:", hre.ethers.utils.formatEther(finalContractBalance), "ETH");

  console.log("\n" + "=".repeat(60));
  if (totalOwnerReceived.eq(hre.ethers.utils.parseEther("0.107")) && finalContractBalance.eq(0)) {
    console.log("✅ ALL TESTS PASSED!");
    console.log("✅ Payments go directly to dataset owners");
    console.log("✅ No funds trapped in contract");
  } else {
    console.log("⚠️  WARNINGS DETECTED - See details above");
  }
  console.log("=".repeat(60) + "\n");

  // Additional check: hasAccess
  console.log("🔐 Access Control Verification:");
  const buyerHasAccess = await contract.hasAccess(tokenId, buyer.address);
  const renterHasAccess = await contract.hasAccess(tokenId, renter.address);
  const randomHasAccess = await contract.hasAccess(tokenId, deployer.address);

  console.log("  Buyer has access:  ", buyerHasAccess ? "✅ Yes" : "❌ No");
  console.log("  Renter has access: ", renterHasAccess ? "✅ Yes" : "❌ No");
  console.log("  Random has access: ", randomHasAccess ? "❌ No" : "✅ No (correct)");

  if (buyerHasAccess && renterHasAccess && !randomHasAccess) {
    console.log("  ✅ Access control working correctly");
  }

  console.log("\n");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
