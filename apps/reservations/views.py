"""
API Views, Permissions, and Custom Actions for Reservations App.
"""

import io
from django.template.loader import render_to_string
from django.http import HttpResponse, StreamingHttpResponse
from xhtml2pdf import pisa
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Reservation
from .serializers import ReservationSerializer
from apps.accounts.tasks import send_welcome_email_task
from apps.reservations.tasks import send_reservation_voucher_task, send_cancellation_email_task

class IsOwnerStaff(permissions.BasePermission):
    """
    Object-level permission allowing staff/managers full access or restricting regular users to their own resources.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or getattr(request.user, 'role', None) == 'manager':
            return True
        return obj.user == request.user

class ReservationViewSet(viewsets.ModelViewSet):
    """
    ViewSet handling CRUD operations, voucher downloads, payments, and background email tasks for reservations.
    """
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerStaff]

    def get_queryset(self):
        """
        Filters reservation records according to user roles (staff/managers see all, guests see their own).
        """
        user = self.request.user

        if user.is_anonymous:
            return Reservation.objects.none()

        if user.is_staff or getattr(user, 'role', None) == 'manager':
            return Reservation.objects.select_related('user', 'room').all()

        return Reservation.objects.select_related('user', 'room').filter(user=user)

    def perform_create(self, serializer):
        """
        Saves a pending reservation and triggers welcome email Celery task.
        """
        reservation = serializer.save(status='pending', payment_status='pending')
        send_welcome_email_task.delay(self.request.user.email)

    def perform_update(self, serializer):
        """
        Updates reservation details and triggers cancellation email Celery task if status changes to cancelled.
        """
        old_status = serializer.instance.status
        reservation = serializer.save()

        if old_status != 'cancelled' and reservation.status == 'cancelled':
            send_cancellation_email_task.delay(str(reservation.id))

    # @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerStaff])
    # def pay(self, request, pk=None):
    #     reservation = self.get_object()
    #
    #     if reservation.payment_status == 'paid':
    #         return Response(
    #             {'error': 'This reservation has already been paid'},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
    #
    #     payment_method = request.data.get('payment_method')
    #     if not payment_method:
    #         return Response(
    #             {'error': 'Please provide a payment method'},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
    #
    #     reservation.payment_method = payment_method
    #     reservation.payment_status = 'paid'
    #     reservation.status = 'confirmed'
    #     reservation.save()
    #
    #     serializer = self.get_serializer(reservation)
    #     return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsOwnerStaff])
    def download_voucher(self, request, pk=None):
        """
        Custom action generating and serving an inline PDF reservation voucher.
        """
        reservation = self.get_object()

        if reservation.user != self.request.user:
            return Response(
                {'error': 'You do not have permission to download this voucher.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if reservation.status not in ['confirmed'] and reservation.payment_status != 'paid':
            return Response(
                {'error': 'Voucher is only available for confirmed and paid reservations.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        context = {'reservation': reservation}
        html_string = render_to_string('reservations/voucher.html', context)

        pdf_buffer = io.BytesIO()

        pisa_status = pisa.CreatePDF(html_string, dest=pdf_buffer)

        if pisa_status.err:
            return Response(
                {'error': 'Failed to generate PDF voucher.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        pdf_buffer.seek(0)

        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')

        filename = f'voucher_reservation_{reservation.id}.pdf'
        response['Content-Disposition'] = f'inline; filename="reservation_voucher_{reservation.id}.pdf"'

        return response


    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerStaff])
    def pay(self, request, pk=None):
        """
        Custom action processing reservation payment, confirming status, and queuing voucher delivery.
        """
        reservation = self.get_object()

        if reservation.payment_status == 'paid':
            return Response(
                {'error': 'This reservation has already been paid'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_method = request.data.get('payment_method')
        if not payment_method:
            return Response(
                {'error': 'Please provide a payment method'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reservation.payment_method = payment_method
        reservation.payment_status = 'paid'
        reservation.status = 'confirmed'
        reservation.save()

        send_reservation_voucher_task.delay(str(reservation.id))

        serializer = self.get_serializer(reservation)
        return Response(serializer.data, status=status.HTTP_200_OK)
