import os
import json
import requests
from io import BytesIO
from cryptography.fernet import Fernet
from web3 import Web3
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from .models import Dataset, EncryptedDataset
from .serializers import DatasetSerializer
# Ensure blockchain_service has CONTRACT_ADDRESS and CONTRACT_ABI defined
from . import blockchain_service 

class DatasetListCreateView(generics.ListCreateAPIView):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class SecureUploadView(APIView):
    """
    Handles secure upload: Encrypts file -> Uploads to Pinata -> Saves Key DB
    """
    permission_classes = [permissions.AllowAny]  # Temporarily public for frontend testing
    parser_classes = (MultiPartParser, FormParser) # Allow file uploads

    def post(self, request):
        if 'file' not in request.FILES:
            return Response({'success': False, 'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        owner_address = request.data.get('owner_address')
        if not owner_address:
            return Response({'success': False, 'error': 'owner_address required'}, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = request.FILES['file']
        dataset_name = request.data.get('name', uploaded_file.name)

        try:
            # 1. Generate Key & Encrypt
            # Fernet.generate_key() returns URL-safe base64-encoded bytes
            key = Fernet.generate_key() 
            cipher = Fernet(key)
            
            file_data = uploaded_file.read()
            encrypted_data = cipher.encrypt(file_data)

            # 2. Upload to Pinata
            pinata_jwt = os.getenv('PINATA_JWT')
            if not pinata_jwt:
                return Response({'success': False, 'error': 'Server config error: Missing Pinata JWT'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            files = {
                'file': (uploaded_file.name + ".enc", BytesIO(encrypted_data))
            }
            headers = {'Authorization': f'Bearer {pinata_jwt}'}
            
            # Using pinFileToIPFS endpoint
            pinata_res = requests.post(
                'https://api.pinata.cloud/pinning/pinFileToIPFS',
                files=files,
                headers=headers
            )

            if pinata_res.status_code != 200:
                return Response({'success': False, 'error': f'Pinata Error: {pinata_res.text}'}, status=status.HTTP_502_BAD_GATEWAY)

            ipfs_cid = pinata_res.json().get('IpfsHash')

            # 3. Save to DB
            # Get or create a default user for unauthenticated uploads (temporary)
            from users.models import User
            default_user, _ = User.objects.get_or_create(
                username='system',
                defaults={'email': 'system@marketplace.local'}
            )

            EncryptedDataset.objects.create(
                name=dataset_name,
                ipfs_cid=ipfs_cid,
                encryption_key=key, # Store raw bytes
                owner_address=owner_address,
                owner=request.user if request.user.is_authenticated else default_user
            )

            # 4. Respond
            # Key needs to be string for JSON response. It's already base64 bytes.
            return Response({
                'success': True,
                'ipfs_cid': ipfs_cid,
                'encryption_key': key.decode('utf-8'), # Decode bytes to string
                'name': dataset_name
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"Upload Error: {e}")
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SecureAccessView(APIView):
    """
    Verifies on-chain access rights and returns the encryption key.
    """
    permission_classes = [permissions.AllowAny] # Public endpoint, security via Blockchain

    def get(self, request, dataset_id):
        wallet_address = request.query_params.get('wallet_address')
        if not wallet_address:
            return Response({'error': 'wallet_address required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get local record
            # Note: dataset_id here refers to the Token ID we linked in Finalize
            dataset = EncryptedDataset.objects.get(dataset_id=dataset_id)
        except EncryptedDataset.DoesNotExist:
            return Response({'error': 'Dataset key not found'}, status=status.HTTP_404_NOT_FOUND)

        # --- Blockchain Verification ---
        try:
            rpc_url = os.getenv('SEPOLIA_RPC_URL')
            if not rpc_url:
                 return Response({'error': 'Server config error: Missing RPC URL'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            # Ensure checksum address
            checksum_wallet = Web3.to_checksum_address(wallet_address)
            checksum_contract = Web3.to_checksum_address(blockchain_service.CONTRACT_ADDRESS)
            
            contract = w3.eth.contract(address=checksum_contract, abi=blockchain_service.CONTRACT_ABI)

            # Check 1: Ownership
            try:
                owner = contract.functions.ownerOf(int(dataset_id)).call()
                if owner == checksum_wallet:
                     return self._success_response(dataset)
            except Exception:
                pass # Token might not exist yet or error

            # Check 2: Rental (Using our custom hasAccess function)
            # Ensure your contract ABI includes hasAccess
            has_access = contract.functions.hasAccess(int(dataset_id), checksum_wallet).call()

            if has_access:
                return self._success_response(dataset)

            # If we get here, access is denied
            return Response({'error': 'Access denied: No ownership or active rental found'}, status=status.HTTP_403_FORBIDDEN)

        except Exception as e:
            return Response({'error': f'Blockchain verification failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _success_response(self, dataset):
        """Helper to return success response with decryption key"""
        return Response({
            'success': True,
            'key': dataset.encryption_key.decode('utf-8') if isinstance(dataset.encryption_key, bytes) else dataset.encryption_key,
            'ipfs_cid': dataset.ipfs_cid,
            'name': dataset.name
        })

    def post(self, request):
        ipfs_cid = request.data.get('ipfs_cid')
        token_id = request.data.get('token_id')
        owner_address = request.data.get('owner_address')

        if not ipfs_cid or not token_id:
            return Response({'error': 'Missing fields'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            dataset = EncryptedDataset.objects.get(ipfs_cid=ipfs_cid)

            # Security: Verify owner_address matches (temporary, until we add proper auth)
            if owner_address and dataset.owner_address.lower() != owner_address.lower():
                return Response({'error': 'Unauthorized: wallet address mismatch'}, status=status.HTTP_403_FORBIDDEN)

            dataset.dataset_id = token_id
            dataset.save()

            return Response({'success': True})
        except EncryptedDataset.DoesNotExist:
            return Response({'error': 'Dataset not found'}, status=status.HTTP_404_NOT_FOUND)


class DownloadEncryptedFileView(APIView):
    """
    Download encrypted file from IPFS.
    This endpoint fetches the encrypted data from IPFS and returns it to the VS Code extension.
    The extension will then decrypt it using the key from SecureAccessView.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, ipfs_cid):
        try:
            # Fetch from Pinata IPFS gateway
            ipfs_url = f'https://gateway.pinata.cloud/ipfs/{ipfs_cid}'

            response = requests.get(ipfs_url, timeout=30)

            if response.status_code != 200:
                return Response(
                    {'error': f'IPFS fetch failed: {response.status_code}'},
                    status=status.HTTP_502_BAD_GATEWAY
                )

            # Return encrypted file as binary response
            from django.http import HttpResponse
            return HttpResponse(
                response.content,
                content_type='application/octet-stream',
                headers={
                    'Content-Disposition': f'attachment; filename="{ipfs_cid}.enc"',
                    'Access-Control-Allow-Origin': '*',
                }
            )

        except requests.RequestException as e:
            return Response(
                {'error': f'Failed to fetch from IPFS: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            return Response(
                {'error': f'Server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserDatasetsView(APIView):
    """
    Fetches all datasets owned, purchased, or rented by a specific wallet address.
    This is used by the VS Code extension to auto-fetch accessible datasets.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, wallet_address):
        try:
            # Connect to blockchain
            rpc_url = os.getenv('SEPOLIA_RPC_URL')
            if not rpc_url:
                return Response({'error': 'Server config error: Missing RPC URL'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            w3 = Web3(Web3.HTTPProvider(rpc_url))
            checksum_wallet = Web3.to_checksum_address(wallet_address)
            checksum_contract = Web3.to_checksum_address(blockchain_service.CONTRACT_ADDRESS)
            contract = w3.eth.contract(address=checksum_contract, abi=blockchain_service.CONTRACT_ABI)

            # Fetch owned datasets (minted by user)
            owned_datasets = []
            try:
                owned_data = contract.functions.getDatasetsByOwner(checksum_wallet).call()
                for ds in owned_data:
                    owned_datasets.append({
                        'token_id': ds[0],
                        'name': ds[1],
                        'description': ds[2],
                        'category': ds[3],
                        'format': ds[4],
                        'ipfs_cid': ds[5],
                        'price': str(ds[6]),
                        'owner': ds[7]
                    })
            except Exception as e:
                print(f"Error fetching owned datasets: {e}")

            # Fetch purchased datasets
            purchased_datasets = []
            try:
                purchased_token_ids = contract.functions.getMyPurchasedDatasets().call({'from': checksum_wallet})
                for token_id in purchased_token_ids:
                    ds = contract.functions.getDatasetById(token_id).call()
                    purchased_datasets.append({
                        'token_id': ds[0],
                        'name': ds[1],
                        'description': ds[2],
                        'category': ds[3],
                        'format': ds[4],
                        'ipfs_cid': ds[5],
                        'price': str(ds[6]),
                        'owner': ds[7]
                    })
            except Exception as e:
                print(f"Error fetching purchased datasets: {e}")

            # Fetch rented datasets (datasets with active rental)
            rented_datasets = []
            try:
                # Get all datasets and check which ones the user has rental access to
                all_datasets = contract.functions.getAllDatasets().call()
                for ds in all_datasets:
                    token_id = ds[0]
                    # Skip if already owned or purchased
                    if any(d['token_id'] == token_id for d in owned_datasets + purchased_datasets):
                        continue

                    # Check if user has active rental
                    try:
                        has_access = contract.functions.hasAccess(token_id, checksum_wallet).call()
                        if has_access:
                            rented_datasets.append({
                                'token_id': ds[0],
                                'name': ds[1],
                                'description': ds[2],
                                'category': ds[3],
                                'format': ds[4],
                                'ipfs_cid': ds[5],
                                'price': str(ds[6]),
                                'owner': ds[7]
                            })
                    except Exception:
                        pass
            except Exception as e:
                print(f"Error fetching rented datasets: {e}")

            # Note: "owned" includes datasets created by the user (they are minted to their address)
            # So created datasets are already in the "owned" list
            return Response({
                'success': True,
                'owned': owned_datasets,  # Includes created/minted datasets
                'purchased': purchased_datasets,
                'rented': rented_datasets,
                'total_count': len(owned_datasets) + len(purchased_datasets) + len(rented_datasets)
            })

        except Exception as e:
            print(f"User datasets fetch error: {e}")
            return Response(
                {'error': f'Failed to fetch user datasets: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )