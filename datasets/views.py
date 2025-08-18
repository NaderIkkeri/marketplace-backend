# datasets/views.py
from rest_framework import generics
from .models import Dataset
from .serializers import DatasetSerializer

class DatasetListCreateView(generics.ListCreateAPIView):
    """
    View to list all datasets and create a new one.
    """
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer