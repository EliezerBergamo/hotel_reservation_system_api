from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, permissions
from rest_framework.permissions import BasePermission

from .models import Hotel
from .serializers import HotelSerializer

class IsManagerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == 'manager'

class HotelViewSet(viewsets.ModelViewSet):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = ['city']

    search_fields = ['name', 'address']

    ordering_fields = ['name', 'city']
    ordering = ['name']

    permission_classes = [IsManagerOrReadOnly]
