# datasets/views.py
from rest_framework import generics, permissions
from .models import Dataset
from .serializers import DatasetSerializer
from . import blockchain_service
class DatasetListCreateView(generics.ListCreateAPIView):
    """
    View to list all datasets and create a new one.
    """
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        # 2. First, save the dataset to the Django database
        dataset_instance = serializer.save(owner=self.request.user)
        
        # 3. Then, call the function to mint the NFT
        # We need a wallet_address on the user model for this to work
        if self.request.user.wallet_address:
            mint_successful = blockchain_service.mint_dataset_nft(
                owner_address=self.request.user.wallet_address,
                metadata_uri=dataset_instance.ipfs_cid
            )
            
            if not mint_successful:
                # Here you might want to handle the case where the blockchain transaction fails
                # For now, we'll just print a message
                print(f"Warning: Dataset {dataset_instance.id} created in DB, but NFT minting failed.")
        else:
            print(f"Warning: User {self.request.user.username} has no wallet address. Cannot mint NFT.")

