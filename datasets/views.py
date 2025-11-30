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
            
            return Response({'error': 'Access denied: No active rental or ownership'}, status=status.HTTP_403_FORBIDDEN)

        except Exception as e:
            print(f"Blockchain Verification Error: {e}")
            return Response({'error': 'Verification failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _success_response(self, dataset):
        return Response({
            'success': True,
            'key': dataset.encryption_key.decode('utf-8'),
            'ipfs_cid': dataset.ipfs_cid
        })


class FinalizeUploadView(APIView):
    permission_classes = [permissions.AllowAny]  # Temporarily public for frontend testing

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