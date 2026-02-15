from django.db import models
from apps.core.models import BaseModel


class Reservation(BaseModel):
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='reservations',
    )

    room = models.ForeignKey(
        'rooms.Room',
        on_delete=models.CASCADE,
        related_name='reservations',
    )

    start_date = models.DateField()
    end_date = models.DateField()

    STATUS_CHOICES = (
        ('confirmed', 'Confirmed'),
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    payment_status = models.CharField(max_length=50, default='pending')
    payment_details = models.CharField(blank=True, null=True, max_length=500)

    class Meta:
        db_table = 'reservations'

    def __str__(self):
        return f"Reservation: {self.id} - {self.user.name}|{self.start_date} - {self.end_date}"