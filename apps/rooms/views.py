from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters as drf_filters
from .models import Room
from .serializers import RoomSerializer
from .filters import RoomFilter

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]

    filterset_class = RoomFilter

    search_fields = ['room_type', 'hotel__name', 'hotel__city']
    ordering_fields = ['price', 'room_number']
    ordering = ['price']
