"""
Celery asynchronous background tasks for user operations and notifications.
"""

from celery import shared_task
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model

@shared_task
def send_welcome_email_task(user_email):
    """
    Asynchronous task to dispatch a welcome email upon successful user registration.
    """
    send_mail(
        subject='Welcome to Hotel Reservation System',
        message='Your account has been successfully created. Enjoy your stay!',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        fail_silently=False,
    )
    return f'Real email sent to {user_email}'

@shared_task
def send_password_reset_email_task(user_id, uid, token):
    """
    Asynchronous task to send an HTML-formatted password reset email with secure tokens.
    """
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)

        context = {
            'user': user,
            'uid': uid,
            'token': token,
        }
        html_string = render_to_string('accounts/password_reset.html', context)

        email = EmailMessage(
            subject='Reset your password',
            body=f'Use UID: {uid} and Token: {token} to reset your password',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.content_subtype = 'html'
        email.body = html_string
        email.send(fail_silently=False)

        return f'Reset email sent to {user.email}'
    except User.DoesNotExist:
        return f'User with UID {uid} does not exist'
