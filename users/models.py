# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom user model for the marketplace.
    """
    ROLE_CHOICES = (
        ('PROVIDER', 'Data Provider'),
        ('CONSUMER', 'Data Consumer'),
        ('ADMIN', 'Administrator'),
    )

    # Wallet address for blockchain transactions
    wallet_address = models.CharField(max_length=42, unique=True, null=True, blank=True)
    
    # Role-based access control
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='CONSUMER')
    
    # Reputation score based on marketplace activity
    reputation_score = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)

    def __str__(self):
        return self.username