"""
API Serializers for Reservation Models.
"""

from rest_framework import serializers
from django.db import transaction
from .models import Reservation
from apps.accounts.serializers import UserSerializer
from apps.rooms.serializers import RoomSerializer
from apps.rooms.models import Room

class ReservationSerializer(serializers.ModelSerializer):
    """
    Serializer handling reservation creation, updates, validation, and price calculation
    with concurrency locking for overlapping dates.
    """
    user_details = UserSerializer(source='user' ,read_only=True)
    room_details = RoomSerializer(source='room' ,read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Reservation
        fields = [
            'id', 'user', 'user_details', 'room', 'room_details',
            'start_date', 'end_date', 'status', 'total_price',
            'payment_method', 'payment_status', 'date_creation'
        ]

    def validate(self, data):
        """
        Validates date ranges ensuring end date is logically after start date.
        """
        start_date = data.get('start_date') or (self.instance.start_date if self.instance else None)
        end_date = data.get('end_date') or (self.instance.end_date if self.instance else None)
        room = data.get('room') or (self.instance.room if self.instance else None)

        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError({'end_date': 'End date must be after start date'})

        return data

    def create(self, validated_data):
        """
        Creates a new reservation within an atomic transaction using database row locks
        to prevent double booking on overlapping dates.
        """
        room = validated_data['room']
        start_date = validated_data['start_date']
        end_date = validated_data['end_date']

        with transaction.atomic():
            locked_room = Room.objects.select_for_update().get(pk=room.pk)

            overlapping = Reservation.objects.filter(
                room=locked_room,
                status='confirmed',
            ).filter(
                start_date__lte=end_date,
                end_date__gte=start_date
            )

            if overlapping.exists():
                raise serializers.ValidationError(
                    {'end_date': 'This room already has a confirmed reservation for the selected period.'}
                )

            delta = end_date - start_date
            days = max(delta.days, 1)
            validated_data['total_price'] = locked_room.price * days

            return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Updates reservation dates or room details ensuring locking and schedule overlap checks.
        """
        room = validated_data.get('room', instance.room)
        start_date = validated_data.get('start_date', instance.start_date)
        end_date = validated_data.get('end_date', instance.end_date)

        with transaction.atomic():
            locked_room = Room.objects.select_for_update().get(pk=room.pk)

            overlapping = Reservation.objects.filter(
                room=locked_room,
                status='confirmed',
            ).filter(
                start_date__lte=end_date,
                end_date__gte=start_date
            ).exclude(pk=instance.pk)

            if overlapping.exists():
                raise serializers.ValidationError(
                    {'error': 'It is not possible to change the dates. The room has already been reserved.'}
                )

            delta = end_date - start_date
            days = max(delta.days, 1)
            validated_data['total_price'] = locked_room.price * days

            return super().update(instance, validated_data)
