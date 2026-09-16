"""
Reservations Application Configuration Module.
"""

from django.apps import AppConfig


class ReservationsConfig(AppConfig):
    """
    Configuration class for the Reservations application.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reservations'
