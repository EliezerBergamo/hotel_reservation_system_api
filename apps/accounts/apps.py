"""
AppConfig for the Accounts module.
"""

from django.apps import AppConfig


class AuthConfig(AppConfig):
    """
    Configuration class for the Accounts application.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
