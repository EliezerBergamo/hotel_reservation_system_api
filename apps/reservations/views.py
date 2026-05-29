from rest_framework import viewsets, permissions
from .models import Reservation
from .serializers import ReservationSerializer
from apps.accounts.tasks import send_welcome_email_task


class IsOwnerStaff(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or getattr(request.user, 'role', None) == 'manager':
            return True
        return obj.user == request.user

class ReservationViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerStaff]

    def get_queryset(self):
        user = self.request.user

        if user.is_anonymous:
            return Reservation.objects.none()

        if user.is_staff or getattr(user, 'role', None) == 'manager':
            return Reservation.objects.select_related('user', 'room').all()

        return Reservation.objects.select_related('user', 'room').filter(user=user)

    def perform_create(self, serializer):
        reservation = serializer.save()
        send_welcome_email_task.delay(self.request.user.email)
