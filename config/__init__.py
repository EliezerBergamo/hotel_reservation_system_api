"""
Config Package Initializer.
Loads the Celery app on Django startup to ensure task discovery works properly.
"""

from .celery import app as celery_app

__all__ = ('celery_app',)