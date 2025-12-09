# datasets/urls.py
# datasets/urls.py
from django.urls import path
from .views import (
    DatasetListCreateView,
    SecureUploadView,
    SecureAccessView,
    DownloadEncryptedFileView,
    UserDatasetsView
)

urlpatterns = [
    path('', DatasetListCreateView.as_view(), name='dataset-list-create'),
    path('secure-upload/', SecureUploadView.as_view(), name='secure-upload'),
    path('access/<int:dataset_id>/', SecureAccessView.as_view(), name='secure-access'),
    path('finalize/', SecureAccessView.as_view(), name='finalize-upload'),  # POST method handles finalization
    path('download-encrypted/<str:ipfs_cid>/', DownloadEncryptedFileView.as_view(), name='download-encrypted'),
    path('user-datasets/<str:wallet_address>/', UserDatasetsView.as_view(), name='user-datasets'),
]