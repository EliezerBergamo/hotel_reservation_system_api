"""
Database Models for the Hotels App.
"""

from django.db import models
from apps.core.models import BaseModel

class Hotel(BaseModel):
    """
    Represents a hotel entity stored in the database.
    Inherits primary key and metadata timestamps from BaseModel.
    """
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=255)

    class Meta:
        db_table = 'hotels'

    def __str__(self):
        return f"{self.name} - ({self.address} | {self.city})"
