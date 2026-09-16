"""
API Serializers for Hotel Models.
"""

from rest_framework import serializers
from .models import Hotel

class HotelSerializer(serializers.ModelSerializer):
    """
    Serializer mapping all Hotel model fields for JSON representation.
    """
    class Meta:
        model = Hotel
        fields = '__all__'