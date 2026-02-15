from django.db import models
from apps.core.models import BaseModel

class Room(BaseModel):

    hotel = models.ForeignKey(
        'hotels.Hotel',
        on_delete=models.CASCADE,
        related_name='rooms',
    )

    room_number = models.IntegerField(default=0)
    room_type = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    capacity = models.IntegerField(default=1)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rooms'

    def __str__(self):
        return f"Room {self.room_number} - {self.hotel.name})"