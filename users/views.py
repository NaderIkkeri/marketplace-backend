# users/views.py
from rest_framework import generics
from .models import User
from rest_framework.permissions import AllowAny
from .serializers import UserSerializer, UserRegistrationSerializer

class UserListCreateView(generics.ListCreateAPIView):
    """
    View to list all users and create a new one.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny] # Allow any user (even unauthenticated) to access this endpoint