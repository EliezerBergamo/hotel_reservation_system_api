"""
API Serializers for Room Models.
"""

from rest_framework import serializers
from .models import Room

class RoomSerializer(serializers.ModelSerializer):
    """
    Serializer handling serialization and deserialization of Room model instances.
    """
    class Meta:
        model = Room
        fields = [
            'id',
            'hotel',
            'room_number',
            'room_type',
            'price',
            'capacity',
            'date_creation'
        ]
