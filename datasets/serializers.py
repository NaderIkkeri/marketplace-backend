# datasets/serializers.py
from rest_framework import serializers
from .models import Dataset

class DatasetSerializer(serializers.ModelSerializer):
    # Display the owner's username instead of just their ID for better readability
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Dataset
        fields = ['id', 'owner', 'title', 'description', 'category', 'data_format', 'ipfs_cid', 'upload_timestamp']