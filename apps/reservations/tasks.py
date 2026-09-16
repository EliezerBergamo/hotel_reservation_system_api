"""
Celery Asynchronous Tasks for Email Notifications and Voucher Generation.
"""

from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from io import BytesIO
from .models import Reservation

@shared_task
def send_reservation_voucher_task(reservation_id):
    """
    Generates a PDF voucher using xhtml2pdf and emails it as an attachment to the guest.
    """
    try:
        reservation = Reservation.objects.get(id=reservation_id)
        user_email = reservation.user.email

        context = {'reservation': reservation}
        html_string = render_to_string('reservations/voucher.html', context)

        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html_string, dest=pdf_buffer)

        if pisa_status.err:
            return f'Error generating PDF for reservation {reservation_id}'

        pdf_buffer.seek(0)
        pdf_data = pdf_buffer.getvalue()

        email = EmailMessage(
            subject=f'Your hotel reservation voucher | ID {reservation_id}',
            body=f'Hello {reservation.user.name.title()},\n\nThank you for choosing our hotel!'
                  f'Attached is your reservation voucher.\n\nEnjoy your stay!',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user_email],
        )

        filename = f'reservation_voucher_{reservation_id}.pdf'
        email.attach(filename, pdf_data, 'application/pdf')

        email.send(fail_silently=False)

        return f'Voucher email sent successfully to {user_email} for reservation {reservation_id}'

    except Reservation.DoesNotExist:
        return f'Reservation {reservation_id} not found.'

@shared_task
def send_cancellation_email_task(reservation_id):
    """
    Sends an HTML email notification confirming reservation cancellation.
    """
    try:
        reservation = Reservation.objects.get(id=reservation_id)
        user_email = reservation.user.email
        context = {'reservation': reservation}
        html_string = render_to_string('reservations/cancellation.html', context)

        email = EmailMessage(
            subject=f'Cancellation Confirmation | Reservation ID {reservation_id}',
            body=f'Hello {reservation.user.name.title()},\n\nYour reservation {reservation_id} has been cancelled.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user_email],
        )

        email.content_subtype = 'html'
        email.body = html_string
        email.send(fail_silently=False)
        return f'Cancellation email sent successfully to {user_email} for reservation {reservation_id}'

    except Reservation.DoesNotExist:
        return f'Reservation {reservation_id} not found.'
