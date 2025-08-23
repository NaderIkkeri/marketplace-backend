# datasets/views.py
from rest_framework import generics, permissions
from .models import Dataset
from .serializers import DatasetSerializer

class DatasetListCreateView(generics.ListCreateAPIView):
    """
    View to list all datasets and create a new one.
    """
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)