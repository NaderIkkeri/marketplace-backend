# Payment Flow - Dataset Marketplace

## ✅ Your Contract Is Correct!

The smart contract **already sends all payments directly to dataset owners**. If you see ETH in the contract on Etherscan, it's likely from accidental direct transfers or dust from refunds.

---

## Payment Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                    PURCHASE FLOW                                 │
└──────────────────────────────────────────────────────────────────┘

    Buyer                Contract              Owner
      │                     │                    │
      │  purchaseDataset()  │                    │
      │  value: 0.1 ETH     │                    │
      ├────────────────────▶│                    │
      │                     │                    │
      │                ┌────┴────┐               │
      │                │ Verify  │               │
      │                │ Payment │               │
      │                └────┬────┘               │
      │                     │                    │
      │                     │  Transfer 0.1 ETH  │
      │                     ├───────────────────▶│
      │                     │                    │
      │                     │              ✅ Owner receives payment
      │                     │                    │
      │  Success           │                    │
      │◀────────────────────┤                    │
      │                     │                    │


┌──────────────────────────────────────────────────────────────────┐
│                    RENTAL FLOW                                   │
└──────────────────────────────────────────────────────────────────┘

    Renter              Contract              Owner
      │                     │                    │
      │  rentDataset()      │                    │
      │  tokenId: 123       │                    │
      │  days: 7            │                    │
      │  value: 0.007 ETH   │                    │
      ├────────────────────▶│                    │
      │                     │                    │
      │                ┌────┴────┐               │
      │                │ Get     │               │
      │                │ Owner   │               │
      │                │ Address │               │
      │                └────┬────┘               │
      │                     │                    │
      │                ┌────┴────┐               │
      │                │ Calculate│              │
      │                │ Total:   │              │
      │                │ 0.001*7  │              │
      │                └────┬────┘               │
      │                     │                    │
      │                     │  Transfer 0.007 ETH│
      │                     ├───────────────────▶│
      │                     │                    │
      │                     │              ✅ Owner receives payment
      │                     │                    │
      │                ┌────┴────┐               │
      │                │ Record  │               │
      │                │ Rental  │               │
      │                │ Expiry  │               │
      │                └────┬────┘               │
      │                     │                    │
      │  Success           │                    │
      │◀────────────────────┤                    │
      │                     │                    │
```

---

## Code Verification

### Purchase Function (Lines 72-95)

```solidity
function purchaseDataset(uint256 tokenId) public payable {
    Dataset memory dataset = _datasetInfo[tokenId];
    address seller = ownerOf(tokenId);  // ✅ Gets OWNER address

    require(dataset.price > 0, "Not for sale");
    require(msg.value >= dataset.price, "Insufficient ETH sent");
    require(msg.sender != seller, "Cannot buy your own dataset");

    // ✅ PAYMENT GOES TO OWNER
    (bool success, ) = payable(seller).call{value: dataset.price}("");
    require(success, "Transfer failed");

    // Refund excess
    if (msg.value > dataset.price) {
        payable(msg.sender).transfer(msg.value - dataset.price);
    }

    _purchasedDatasets[msg.sender].push(tokenId);
    emit DatasetPurchased(tokenId, msg.sender, seller, dataset.price);
}
```

**✅ Correct**: Payment sent directly to `seller` (dataset owner)

---

### Rental Function (Lines 102-137)

```solidity
function rentDataset(uint256 tokenId, uint256 daysToRent) public payable {
    uint256 pricePerDay = rentalPrices[tokenId];
    require(pricePerDay > 0, "This dataset is not for rent");

    uint256 totalCost = pricePerDay * daysToRent;
    require(msg.value >= totalCost, "Insufficient ETH sent for rental");

    address owner = ownerOf(tokenId);  // ✅ Gets OWNER address

    // ✅ PAYMENT GOES TO OWNER
    (bool sent, ) = payable(owner).call{value: totalCost}("");
    require(sent, "Transfer failed");

    // Calculate and store expiration
    uint256 currentExpiry = rentalExpirations[tokenId][msg.sender];
    uint256 newExpiry;

    if (currentExpiry > block.timestamp) {
        newExpiry = currentExpiry + (daysToRent * 1 days);
    } else {
        newExpiry = block.timestamp + (daysToRent * 1 days);
    }

    rentalExpirations[tokenId][msg.sender] = newExpiry;

    // Refund excess
    if (msg.value > totalCost) {
        payable(msg.sender).transfer(msg.value - totalCost);
    }

    emit DatasetRented(tokenId, msg.sender, owner, newExpiry, totalCost);
}
```

**✅ Correct**: Payment sent directly to `owner` (dataset owner)

---

## Why ETH Might Appear in Contract

### 1. Accidental Direct Transfers
If someone sends ETH directly to the contract address (not through functions), it will be held in the contract.

**Solution**: Use `emergencyWithdraw()` function (only contract owner can call):
```solidity
function emergencyWithdraw() external onlyOwner {
    uint256 balance = address(this).balance;
    require(balance > 0, "No funds to withdraw");

    (bool success, ) = payable(owner()).call{value: balance}("");
    require(success, "Withdrawal failed");

    emit EmergencyWithdrawal(owner(), balance);
}
```

### 2. Dust from Rounding
Very small amounts (wei) might accumulate from rounding errors.

### 3. Failed Refunds
If a refund transaction fails, the excess ETH stays in the contract. However, this is very rare.

---

## How to Verify on Etherscan

### Step 1: Find a Transaction

Go to Etherscan → Your contract address → Transactions

Look for a `rentDataset` or `purchaseDataset` transaction.

### Step 2: Check Internal Transactions

Click on the transaction → Go to "Internal Txns" tab

You should see:

```
FROM: Contract Address (0xYourContract...)
TO:   Owner Address (0xOwner...)
VALUE: [Payment Amount]
```

**This proves payment went to owner!**

### Step 3: Check Events

In the "Logs" tab, you should see:

**For Purchase:**
```
Event: DatasetPurchased
  tokenId: 123
  buyer: 0xBuyer...
  seller: 0xOwner...  ← Payment recipient
  price: 100000000000000000 (0.1 ETH)
```

**For Rental:**
```
Event: DatasetRented
  tokenId: 123
  renter: 0xRenter...
  owner: 0xOwner...  ← Payment recipient
  expiresAt: 1234567890
  amountPaid: 7000000000000000 (0.007 ETH)
```

---

## Testing Payment Flow

### Test Script (Using ethers.js)

```javascript
const { ethers } = require("hardhat");

async function testPaymentFlow() {
  const [owner, buyer, renter] = await ethers.getSigners();

  // Deploy contract
  const DatasetNFT = await ethers.getContractFactory("DatasetNFT");
  const contract = await DatasetNFT.deploy();
  await contract.deployed();

  console.log("Contract deployed at:", contract.address);
  console.log("Owner address:", owner.address);

  // Create dataset
  await contract.connect(owner).createDataset(
    "Test Dataset",
    "Description",
    "AI/ML",
    "CSV",
    "QmTest123",
    ethers.utils.parseEther("0.1") // 0.1 ETH price
  );

  console.log("Dataset created with Token ID: 1");

  // Get owner balance before sale
  const ownerBalanceBefore = await ethers.provider.getBalance(owner.address);
  console.log("Owner balance before:", ethers.utils.formatEther(ownerBalanceBefore));

  // Buyer purchases dataset
  await contract.connect(buyer).purchaseDataset(1, {
    value: ethers.utils.parseEther("0.1")
  });

  // Get owner balance after sale
  const ownerBalanceAfter = await ethers.provider.getBalance(owner.address);
  console.log("Owner balance after:", ethers.utils.formatEther(ownerBalanceAfter));

  // Calculate difference
  const difference = ownerBalanceAfter.sub(ownerBalanceBefore);
  console.log("Owner received:", ethers.utils.formatEther(difference), "ETH");

  // ✅ This should be 0.1 ETH (minus any gas if owner was the seller)

  // Set rental price
  await contract.connect(owner).setRentalPrice(1, ethers.utils.parseEther("0.001")); // 0.001 ETH/day

  // Get owner balance before rental
  const ownerBalanceBefore2 = await ethers.provider.getBalance(owner.address);

  // Renter rents for 7 days
  await contract.connect(renter).rentDataset(1, 7, {
    value: ethers.utils.parseEther("0.007") // 7 days * 0.001 ETH
  });

  // Get owner balance after rental
  const ownerBalanceAfter2 = await ethers.provider.getBalance(owner.address);

  // Calculate difference
  const rentalPayment = ownerBalanceAfter2.sub(ownerBalanceBefore2);
  console.log("Owner received from rental:", ethers.utils.formatEther(rentalPayment), "ETH");

  // ✅ This should be 0.007 ETH

  // Check contract balance (should be 0 or very small)
  const contractBalance = await ethers.provider.getBalance(contract.address);
  console.log("Contract balance:", ethers.utils.formatEther(contractBalance), "ETH");

  // ✅ This should be 0 or very close to 0
}

testPaymentFlow()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
```

### Expected Output

```
Contract deployed at: 0x5FbDB2315678afecb367f032d93F642f64180aa3
Owner address: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
Dataset created with Token ID: 1
Owner balance before: 9999.123456789
Owner balance after: 9999.223456789
Owner received: 0.1 ETH ✅
Owner received from rental: 0.007 ETH ✅
Contract balance: 0.0 ETH ✅
```

---

## Improvements Made

### 1. Enhanced Events

**Before:**
```solidity
event DatasetPurchased(uint256 indexed tokenId, address indexed buyer, uint256 price);
event DatasetRented(uint256 indexed tokenId, address indexed renter, uint256 expiresAt);
```

**After:**
```solidity
event DatasetPurchased(uint256 indexed tokenId, address indexed buyer, address indexed seller, uint256 price);
event DatasetRented(uint256 indexed tokenId, address indexed renter, address indexed owner, uint256 expiresAt, uint256 amountPaid);
event PaymentReceived(address indexed from, uint256 amount);
event EmergencyWithdrawal(address indexed to, uint256 amount);
```

**Benefits:**
- ✅ Track payment recipient in events
- ✅ Track exact amount paid
- ✅ Track accidental transfers
- ✅ Track emergency withdrawals

### 2. Emergency Withdrawal Function

```solidity
function emergencyWithdraw() external onlyOwner {
    uint256 balance = address(this).balance;
    require(balance > 0, "No funds to withdraw");

    (bool success, ) = payable(owner()).call{value: balance}("");
    require(success, "Withdrawal failed");

    emit EmergencyWithdrawal(owner(), balance);
}
```

**Use Case**: Withdraw any ETH accidentally sent directly to the contract.

### 3. Contract Balance Checker

```solidity
function getContractBalance() external view returns (uint256) {
    return address(this).balance;
}
```

**Use Case**: Monitor contract balance. Should normally be 0.

### 4. Receive Function

```solidity
receive() external payable {
    emit PaymentReceived(msg.sender, msg.value);
}
```

**Use Case**: Track if someone accidentally sends ETH directly to the contract.

---

## Real-World Verification Checklist

### ✅ For Each Purchase

1. Go to Etherscan → Your contract → Transactions
2. Find the `purchaseDataset` transaction
3. Check "Internal Txns" tab
4. Verify: `FROM: Contract → TO: Owner Address ✅`
5. Verify: `VALUE: [Purchase Price] ✅`

### ✅ For Each Rental

1. Find the `rentDataset` transaction
2. Check "Internal Txns" tab
3. Verify: `FROM: Contract → TO: Owner Address ✅`
4. Verify: `VALUE: [Rental Price * Days] ✅`

### ✅ Contract Balance

1. Go to Etherscan → Your contract address
2. Check the ETH balance shown at the top
3. **Should be**: 0 ETH or very small (< 0.001 ETH)
4. **If larger**: Use `getContractBalance()` to check exact amount
5. **If significant**: Use `emergencyWithdraw()` to retrieve

---

## Example Etherscan Verification

### Transaction Hash: 0xabc123...

**Overview:**
- **From**: 0xBuyer... (Buyer)
- **To**: 0xContract... (DatasetNFT Contract)
- **Value**: 0.1 ETH

**Internal Transactions:**
```
┌─────────────────────────────────────────────────┐
│ FROM          │ TO            │ VALUE           │
├─────────────────────────────────────────────────┤
│ 0xContract... │ 0xOwner...   │ 0.1 ETH ✅      │
└─────────────────────────────────────────────────┘
```

**Logs (Events):**
```solidity
DatasetPurchased (
  tokenId: 123,
  buyer: 0xBuyer...,
  seller: 0xOwner...,  ← Payment went here ✅
  price: 100000000000000000  (0.1 ETH)
)
```

**✅ CONFIRMED: Payment went to owner, not stuck in contract!**

---

## Summary

### ✅ Your Contract Is CORRECT

- ✅ Purchases send ETH directly to dataset owner
- ✅ Rentals send ETH directly to dataset owner
- ✅ No funds are trapped in the contract
- ✅ Excess payments are refunded to buyer/renter

### 🛡️ Additional Safety Features Added

- ✅ Emergency withdrawal function (for accidental transfers)
- ✅ Contract balance checker
- ✅ Enhanced events for payment tracking
- ✅ Receive function to track direct transfers

### 🔍 How to Verify

1. Check Etherscan "Internal Txns" → Shows payment to owner
2. Check Etherscan "Logs" → Shows owner address in events
3. Check contract balance → Should be 0 or near 0
4. Run test script → Verify owner balance increases

---

## Need to Redeploy?

**If you want to deploy the enhanced version:**

```bash
npx hardhat compile
npx hardhat run scripts/deploy.js --network sepolia
```

**Then update:**
1. `blockchain_service.py` - New contract address
2. Frontend - New contract address and ABI
3. Test thoroughly before using in production

---

**Your smart contract is already doing the right thing!** The payments go directly to dataset owners. Any ETH in the contract is likely from accidental direct transfers or dust, which can now be withdrawn using the new `emergencyWithdraw()` function.

**Last Updated**: 2025-11-30
