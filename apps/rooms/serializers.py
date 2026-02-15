from rest_framework import serializers
from .models import Room

class RoomSerializer(serializers.ModelSerializer):
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
