#!/usr/bin/env python
"""
Quick script to manually link Token ID to existing dataset.
Run this to fix the "Kevin Cookie Company Financials" dataset.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
django.setup()

from datasets.models import EncryptedDataset

# The dataset from your screenshot
IPFS_CID = "QmVuXphhwiyrBpXhyMyKk964tphcgZV24kZqGumYgzjLeX"
TOKEN_ID = 14  # From your MetaMask screenshot

try:
    # Find the dataset
    dataset = EncryptedDataset.objects.get(ipfs_cid=IPFS_CID)

    print(f"Found dataset: {dataset.name}")
    print(f"Current Token ID: {dataset.dataset_id}")

    # Link to Token ID
    dataset.dataset_id = TOKEN_ID
    dataset.save()

    print(f"✅ Successfully linked Token ID {TOKEN_ID} to dataset!")
    print(f"\nDataset details:")
    print(f"  Name: {dataset.name}")
    print(f"  Token ID: {dataset.dataset_id}")
    print(f"  IPFS CID: {dataset.ipfs_cid}")
    print(f"  Owner: {dataset.owner_address}")
    print(f"\nYou can now unlock this dataset in the VS Code extension using Token ID: {TOKEN_ID}")

except EncryptedDataset.DoesNotExist:
    print(f"❌ Error: No dataset found with CID {IPFS_CID}")
    print("\nAvailable datasets:")
    for d in EncryptedDataset.objects.all():
        print(f"  - {d.name} (CID: {d.ipfs_cid}, Token ID: {d.dataset_id})")

except Exception as e:
    print(f"❌ Error: {e}")
