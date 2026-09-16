"""
Rooms Application Configuration Module.
"""
from django.apps import AppConfig


class RoomsConfig(AppConfig):
    """
    Configuration class for the Rooms application.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.rooms'
