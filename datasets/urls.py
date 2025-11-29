# datasets/urls.py
from django.urls import path
from .views import (
    DatasetListCreateView,
    FinalizeUploadView,
    SecureUploadView,
    SecureAccessView,
    DownloadEncryptedFileView
)

urlpatterns = [
    path('', DatasetListCreateView.as_view(), name='dataset-list-create'),
    path('secure-upload/', SecureUploadView.as_view(), name='secure-upload'),
    path('access/<int:dataset_id>/', SecureAccessView.as_view(), name='secure-access'),
    path('finalize/', FinalizeUploadView.as_view(), name='finalize-upload'),
    path('download-encrypted/<str:ipfs_cid>/', DownloadEncryptedFileView.as_view(), name='download-encrypted'),
]