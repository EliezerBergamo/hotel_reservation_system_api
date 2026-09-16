"""
Django Admin configuration for the Accounts application.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class UserAdmin(UserAdmin):
    """
    Customized UserAdmin to display custom fields in the Django Admin interface.
    """
    list_display = ('id', 'username', 'email', 'name', 'is_staff')
