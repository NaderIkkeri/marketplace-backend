# users/urls.py
from django.urls import path
from .views import UserListCreateView, UserRegistrationView

urlpatterns = [
    path('', UserListCreateView.as_view(), name='user-list'),
    path('register/', UserRegistrationView.as_view(), name='user-register'),
]