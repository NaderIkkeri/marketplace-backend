# How to Update Contract ABI

**CRITICAL**: This must be done before the extension can unlock datasets!

---

## ⚠️ The Problem

**File**: `marketplace-backend/datasets/blockchain_service.py`

**Current (Lines 7-970)**:
```python
CONTRACT_ABI = """
"abi": [
    # ... ABI content wrapped in string ...
]
"""
```

**Issue**:
- ABI is a string (wrapped in `"""`)
- Has `"abi":` prefix
- This will cause errors when views.py tries to use it

**What views.py expects**:
```python
contract = w3.eth.contract(address=checksum_contract, abi=blockchain_service.CONTRACT_ABI)
```
Views.py needs `CONTRACT_ABI` to be a **Python list**, not a string!

---

## ✅ The Solution

### Step 1: Get Correct ABI from Etherscan

1. **Go to your contract on Etherscan**:
   ```
   https://sepolia.etherscan.io/address/0xA7b2faCfE7a041870f54c8C74C3E89B826316e91#code
   ```

2. **Find the Contract ABI section**:
   - Scroll down past the contract code
   - Look for section titled "Contract ABI"
   - You'll see a large JSON array

3. **Copy the ABI**:
   - Click the **copy icon** (📋) next to "Contract ABI"
   - This copies the entire ABI array to your clipboard

---

### Step 2: Update blockchain_service.py

**Open**: `marketplace-backend/datasets/blockchain_service.py`

**Find** (Lines 7-970):
```python
CONTRACT_ABI = """
"abi": [
    # ... old ABI ...
]
"""
```

**Replace with**:
```python
CONTRACT_ABI = [
    # Paste the ABI JSON array here
]
```

**Important**:
- ✅ Remove the `"""` quotes (no string wrapping!)
- ✅ Remove the `"abi":` prefix if present
- ✅ Should start with `[` and end with `]`
- ✅ Should be indented normally (no extra indentation)
- ✅ Should be valid JSON array format

---

### Step 3: Verify the Format

**Correct Format**:
```python
# datasets/blockchain_service.py
import json
from web3 import Web3

CONTRACT_ADDRESS = "0xA7b2faCfE7a041870f54c8C74C3E89B826316e91"
CONTRACT_ABI = [
    {
        "inputs": [],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "sender",
                "type": "address"
            },
            # ... more items ...
        ],
        "name": "ERC721IncorrectOwner",
        "type": "error"
    },
    # ... hundreds more items ...
]
```

**Check**:
- Line 7 should be: `CONTRACT_ABI = [`
- Last line should be: `]`
- No `"""` quotes anywhere
- No `"abi":` prefix
- Should be valid Python list syntax

---

## 🧪 Test the Update

### After updating, test if it works:

```bash
cd "C:\Users\nader\major project\marketplace-backend"
python manage.py shell
```

```python
# In Django shell:
from datasets import blockchain_service
from web3 import Web3

# Check if CONTRACT_ABI is a list (should be True)
print(f"Is list: {isinstance(blockchain_service.CONTRACT_ABI, list)}")

# Check length (should be ~50-100 items)
print(f"ABI items: {len(blockchain_service.CONTRACT_ABI)}")

# Try to create contract instance
rpc_url = "https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY"  # Use your RPC
w3 = Web3(Web3.HTTPProvider(rpc_url))
contract_address = Web3.to_checksum_address(blockchain_service.CONTRACT_ADDRESS)

try:
    contract = w3.eth.contract(address=contract_address, abi=blockchain_service.CONTRACT_ABI)
    print("✅ SUCCESS: Contract instance created!")
    print(f"Contract address: {contract.address}")
except Exception as e:
    print(f"❌ ERROR: {e}")
```

**Expected Output**:
```
Is list: True
ABI items: 67
✅ SUCCESS: Contract instance created!
Contract address: 0xA7b2faCfE7a041870f54c8C74C3E89B826316e91
```

---

## 🎯 Quick Visual Guide

### What You'll See on Etherscan

1. **Contract Tab**:
   ```
   [Code] [Read Contract] [Write Contract]
   ```

2. **Scroll Down** to find:
   ```
   Contract ABI  [📋 Copy]
   ```

3. **The ABI looks like**:
   ```json
   [{"inputs":[],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[{"internalType":"address","name":"sender"...
   ```

4. **Copy it** (click the 📋 icon)

---

## 📝 Common Mistakes to Avoid

❌ **Wrong - Keeping quotes**:
```python
CONTRACT_ABI = """
[
    # ABI here
]
"""
```

❌ **Wrong - With "abi:" prefix**:
```python
CONTRACT_ABI = "abi": [
    # ABI here
]
```

❌ **Wrong - As string**:
```python
CONTRACT_ABI = "[{...}]"  # This is a string!
```

✅ **Correct - Direct list**:
```python
CONTRACT_ABI = [
    # ABI here
]
```

---

## 🔍 Why This Matters

**Current Flow (BROKEN)**:
```
Extension → Backend SecureAccessView
    ↓
Backend tries to verify on blockchain
    ↓
❌ Error: CONTRACT_ABI is string, not list
    ↓
Verification fails
    ↓
Extension shows "Access denied"
```

**After Fix (WORKING)**:
```
Extension → Backend SecureAccessView
    ↓
Backend verifies ownership on blockchain
    ↓
✅ CONTRACT_ABI used correctly
    ↓
Returns decryption key
    ↓
Extension unlocks dataset
```

---

## 🚀 After Updating

Once you've updated the ABI:

1. **Restart Django** (if it's running):
   ```bash
   # Stop: Ctrl+C
   # Start:
   python manage.py runserver
   ```

2. **Test Upload Flow**:
   - Start frontend: `npm run dev`
   - Go to: http://localhost:3000/create
   - Upload a file
   - Should see IPFS CID

3. **Test Extension**:
   - Open extension in VS Code
   - Try to unlock a dataset
   - Should work now!

4. **Follow Full Testing Guide**:
   - `STEP_BY_STEP_TESTING_GUIDE.md`

---

## 📞 Need Help?

**If you get errors after updating**:

1. **Check syntax**: Make sure it's valid Python list syntax
2. **Check type**: Run the test in Django shell (see above)
3. **Check file**: Make sure you saved the file
4. **Restart Django**: Django needs restart to reload the module

**Common error messages**:

```
TypeError: contract_abi is expected to be of type `list`
```
**Fix**: Remove the `"""` quotes, make it a list

```
JSONDecodeError: ...
```
**Fix**: Check for syntax errors in the ABI (missing commas, brackets, etc.)

```
ValidationError: ...
```
**Fix**: The ABI format might be wrong - re-copy from Etherscan

---

## ✅ Checklist

Before moving on:
- [ ] Opened Etherscan contract page
- [ ] Found "Contract ABI" section
- [ ] Clicked copy button
- [ ] Opened `blockchain_service.py`
- [ ] Replaced lines 7-970 with new ABI
- [ ] Removed `"""` quotes
- [ ] Removed `"abi":` prefix
- [ ] Saved file
- [ ] Tested in Django shell (optional but recommended)
- [ ] Restarted Django server

---

**This is the ONLY remaining blocker!** Once this is done, your entire system will work end-to-end! 🎉

---

**Created**: 2025-11-30
**Priority**: CRITICAL
**Time Required**: 5 minutes
