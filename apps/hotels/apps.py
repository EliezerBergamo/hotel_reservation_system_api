"""
Hotels Application Configuration Module.
"""
from django.apps import AppConfig


class HotelsConfig(AppConfig):
    """
    Configuration class for the Hotels application.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.hotels'
