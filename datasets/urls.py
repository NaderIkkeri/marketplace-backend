# datasets/urls.py
from django.urls import path
from .views import DatasetListCreateView

urlpatterns = [
    path('', DatasetListCreateView.as_view(), name='dataset-list-create'),
]