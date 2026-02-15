from django.db import models
from apps.core.models import BaseModel

class Hotel(BaseModel):

    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=255)

    class Meta:
        db_table = 'hotels'

    def __str__(self):
        return f"{self.name} - ({self.address} | {self.city})"
