# users/views.py
from rest_framework import generics
from .models import User
from .serializers import UserSerializer

class UserListCreateView(generics.ListCreateAPIView):
    """
    View to list all users and create a new one.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer