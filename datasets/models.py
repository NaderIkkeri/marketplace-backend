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