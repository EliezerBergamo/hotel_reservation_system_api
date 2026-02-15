from rest_framework import serializers
from .models import Reservation
from apps.accounts.serializers import UserSerializer
from apps.rooms.serializers import RoomSerializer

class ReservationSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user' ,read_only=True)
    room_details = RoomSerializer(source='room' ,read_only=True)

    class Meta:
        model = Reservation
        fields = [
            'id',
            'user',
            'user_details',
            'room',
            'room_details',
            'start_date',
            'end_date',
            'status',
            'total_price',
            'payment_method',
            'payment_status',
            'date_creation'
        ]