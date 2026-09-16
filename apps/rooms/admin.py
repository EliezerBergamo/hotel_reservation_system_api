"""
Admin Interface Configurations for Rooms App.
"""

from django.contrib import admin
from .models import Room

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    """
    Admin interface configuration for managing hotel rooms.
    """
    list_display = ('id', 'room_number', 'hotel', 'price', 'capacity')
