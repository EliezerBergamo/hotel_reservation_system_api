"""
Filter Sets for Room Queries and Availability Filtering.
"""

from django_filters import rest_framework as filters
from .models import Room
from apps.reservations.models import Reservation
from django.db.models import Q

class RoomFilter(filters.FilterSet):
    """
    FilterSet for searching and filtering rooms by price, capacity, hotel location, and availability dates.
    """
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    min_capacity = filters.NumberFilter(field_name='capacity', lookup_expr='gte')
    available_from = filters.DateFilter(method='filter_availability')
    available_to = filters.DateFilter(method='filter_availability')
    room_type = filters.CharFilter(field_name='room_type', lookup_expr='iexact')
    city = filters.CharFilter(field_name='hotel__city', lookup_expr='iexact')

    class Meta:
        model = Room
        fields = ['hotel', 'city','capacity', 'min_capacity', 'min_price', 'max_price', 'room_type']

    def filter_availability(self, queryset, name, value):
        """
        Excludes rooms that have overlapping confirmed reservations within the specified date range.
        """
        start_date = self.data.get('available_from')
        end_date = self.data.get('available_to')

        if start_date and end_date:
            conflicting_reservations = Reservation.objects.filter(
                status='confirmed',
            ).filter(
                Q(start_date__lte=end_date, end_date__gte=start_date)
            ).values_list('room_id', flat=True)

            return queryset.exclude(id__in=conflicting_reservations)

        return queryset