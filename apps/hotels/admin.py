"""
Admin Interface Configurations for Hotels App.
"""

from django.contrib import admin
from .models import Hotel

@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    """
    Admin configuration for managing Hotel entity records.
    """
    list_display = ('id', 'name', 'city')
