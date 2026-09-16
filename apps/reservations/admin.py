"""
Admin Interface Configurations for Reservations App.
"""

from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Reservation

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    """
    Admin configuration for displaying and managing reservations with direct voucher links.
    """
    list_display = ('id', 'user', 'room', 'status', 'payment_status', 'view_voucher_link')

    def view_voucher_link(self, obj):
        """
        Renders a link to open the PDF voucher if the reservation is confirmed and paid.
        """
        if obj.status == 'confirmed' and obj.payment_status == 'paid':
            html_link = f'<a href="/api/reservations/{obj.id}/download_voucher/" target="_blank" style="color: #264b5c; font-weight: bold;">Open Voucher</a>'
            return mark_safe(html_link)
        return "Pending"

    view_voucher_link.short_description = 'Voucher PDF'
