# datasets/models.py
from django.db import models
from users.models import User # Or your configured user model path

class Dataset(models.Model):
    """
    Represents a dataset's metadata in the marketplace.
    """
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='datasets')
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100)
    data_format = models.CharField(max_length=50)

    # The unique Content Identifier (CID) from IPFS
    ipfs_cid = models.CharField(max_length=255, unique=True)

    upload_timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class EncryptedDataset(models.Model):
    """
    Stores encrypted dataset information with the encryption key.
    This keeps the actual data secure on IPFS while maintaining the encryption key.
    Links to the on-chain NFT via dataset_id (Token ID).
    """
    name = models.CharField(max_length=255)
    ipfs_cid = models.CharField(max_length=255, unique=True, help_text="IPFS CID of the encrypted file")
    encryption_key = models.BinaryField(help_text="Fernet encryption key for this dataset")
    dataset_id = models.IntegerField(unique=True, help_text="On-chain Token ID from smart contract", null=True, blank=True)
    owner_address = models.CharField(max_length=42, help_text="Ethereum wallet address of the owner")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='encrypted_datasets')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (ID: {self.dataset_id}, CID: {self.ipfs_cid})"