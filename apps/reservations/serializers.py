from rest_framework import serializers
from .models import Reservation
from apps.accounts.serializers import UserSerializer
from apps.rooms.serializers import RoomSerializer

class ReservationSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user' ,read_only=True)
    room_details = RoomSerializer(source='room' ,read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

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

    def validate(self, data):
        start_date = data.get('start_date') or (self.instance.start_date if self.instance else None)
        end_date = data.get('end_date') or (self.instance.end_date if self.instance else None)
        room = data.get('room') or (self.instance.room if self.instance else None)

        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError({'end_date': 'End date must be after start date'})

        if room and start_date and end_date:
            overlapping = Reservation.objects.filter(
                room=room,
                status='confirmed'
            ).filter(
                start_date__lte=start_date,
                end_date__gte=end_date
            )

            if self.instance:
                overlapping = overlapping.exclude(pk=self.instance.pk)

            if overlapping.exists():
                raise serializers.ValidationError('Reservation already exists')

        return data

    def create(self, validated_data):
        room = validated_data['room']
        delta = validated_data['end_date'] - validated_data['start_date']
        days = max(delta.days, 1)
        validated_data['total_price'] = room.price * days

        return super().create(validated_data)