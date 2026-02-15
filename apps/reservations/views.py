from rest_framework import viewsets
from .models import Reservation
from .serializers import ReservationSerializer

class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.select_related('user', 'room').all()
    serializer_class = ReservationSerializer
