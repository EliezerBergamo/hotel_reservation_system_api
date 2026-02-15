from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.core.models import BaseModel

class User(AbstractUser, BaseModel):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)

    ROLE_CHOICES = (
        ('guest', 'Guest'),
        ('employee', 'Employee'),
        ('manager', 'Manager'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='guest')

    hotel = models.ForeignKey(
        'hotels.Hotel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff',
    )

    REQUIRED_FIELDS = ['name', 'email']

    class Meta:
        db_table = 'accounts_user'

    def __str__(self):
        return f"{self.name} ({self.email})"
