"""
Unit and Concurrency Tests for Reservation API and Background Tasks.
"""

import uuid
import threading
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from apps.accounts.models import User
from apps.hotels.models import Hotel
from apps.rooms.models import Room
from apps.reservations.models import Reservation
from unittest.mock import patch
from apps.reservations.tasks import send_reservation_voucher_task, send_cancellation_email_task
from django.core import mail
from django.db import connection, DatabaseError

class ReservationTests(APITransactionTestCase):
    """
    Integration and concurrency test suite for testing reservations, multi-threading double-booking,
    database-level encryption, permissions, and email background tasks.
    """
    def setUp(self):
        """
        Initializes test users, hotel, room instance, and base API endpoint URL.
        """
        self.user = User.objects.create_user(
            username="guest", email="guest@example.com", password="password123", name="Guest User"
        )

        self.other_user = User.objects.create_user(
            username="other", email="other@example.com", password="password123", name="Other User"
        )

        self.staff_user = User.objects.create_user(
            username="staff", email="staff@example.com", password="password123", is_staff=True, name="Staff User"
        )

        self.hotel = Hotel.objects.create(
            name="Hotel Transylvania", address="St Castle, 666", city="Brasov"
        )
        self.room = Room.objects.create(
            hotel=self.hotel,
            room_number="101",
            price=200.00,
            capacity=2
        )

        self.url = reverse('reservations:reservation-list')

    @patch('apps.reservations.views.send_welcome_email_task.delay')
    def test_create_reservation_success(self, mock_celery_task):
        """
        Verify successful reservation creation calculates total price and triggers welcome email task.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            "user": self.user.id,
            "room": self.room.id,
            "start_date": "2026-05-10",
            "end_date": "2026-05-15",
            "status": "confirmed"
        }

        response = self.client.post(
            self.url, data, HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(float(response.data['total_price']), 1000.00)
        mock_celery_task.assert_called_once_with(self.user.email)

    def test_prevent_overlapping_reservations(self):
        """
        Verify API rejects requests attempting to book dates overlapping with an existing confirmed reservation.
        """
        Reservation.objects.create(
            user=self.user, room=self.room,
            start_date="2026-05-10", end_date="2026-05-15",
            status="confirmed", total_price=1000.00
        )

        self.client.force_authenticate(user=self.user)

        data = {
            "user": self.user.id,
            "room": self.room.id,
            "start_date": "2026-05-10",
            "end_date": "2026-05-15"
        }

        response = self.client.post(
            self.url, data, HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(len(response.data) > 0)

    def test_concurrent_reservations_prevent_overbooking(self):
        """
        Verify atomic transaction row-locking prevents race conditions during simultaneous reservation requests.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'user': self.user.id,
            'room': self.room.id,
            'start_date': '2026-11-20',
            'end_date': '2026-11-25',
            'status': 'confirmed'
        }

        results = []

        def make_request():
            connection.close()
            response = self.client.post(
                self.url,
                data=data,
                format='json',
                HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
            )
            results.append(response)

        thread_01 = threading.Thread(target=make_request)
        thread_02 = threading.Thread(target=make_request)

        thread_01.start()
        thread_02.start()

        thread_01.join()
        thread_02.join()

        # for i, resp in enumerate(results):
        #     if resp.status_code == 400:
        #         print(f'\n[THREAD {i+1} ERROR 400]: {resp.data}')

        status_codes = [r.status_code for r in results]

        self.assertIn(status.HTTP_201_CREATED, status_codes)
        self.assertTrue(
            status.HTTP_201_CREATED in status_codes or status.HTTP_409_CONFLICT in status_codes
        )

        created_reservations = Reservation.objects.filter(room=self.room, start_date="2026-11-20")
        self.assertEqual(created_reservations.count(), 1)

    @patch('apps.reservations.views.ReservationViewSet.get_queryset')
    def test_custom_exception_handler_shields_database_error(self, mock_queryset):
        """
        Verify database exceptions are masked into a secure HTTP 500 JSON response.
        """
        self.client.force_authenticate(user=self.user)
        mock_queryset.side_effect = DatabaseError('Simulated critical database crash')

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data['error'], 'An internal secure data processing error has occurred.')

    def test_user_can_only_see_own_reservations(self):
        """
        Verify standard users cannot access or list reservations belonging to other users.
        """
        Reservation.objects.create(
            user=self.other_user, room=self.room,
            start_date="2026-06-01", end_date="2026-06-05",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        if isinstance(response.data, dict) and 'results' in response.data:
            results = response.data['results']
        else:
            results = response.data

        self.assertEqual(len(results), 0)

    def test_invalid_date_range_fails(self):
        """
        Verify creating a reservation with an end date earlier than start date returns HTTP 400.
        """
        self.client.force_authenticate(user=self.user)
        data = {
            "user": self.user.id,
            "room": self.room.id,
            "start_date": "2026-05-20",
            "end_date": "2026-05-15",
        }

        response = self.client.post(
            self.url, data, HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_user_can_see_all_reservations(self):
        """
        Verify staff members can view reservation records across all users.
        """
        Reservation.objects.create(
            user=self.other_user, room=self.room,
            start_date="2026-06-01", end_date="2026-06-05",
        )

        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.url)

        if isinstance(response.data, dict) and 'results' in response.data:
            results =  response.data['results']
        else:
            results = response.data

        self.assertEqual(len(results), 1)

    @patch('apps.reservations.tasks.send_cancellation_email_task.delay')
    def test_user_can_cancel_own_reservations(self, mock_cancellation_task):
        """
        Verify users can update their reservation status to cancelled and dispatch confirmation emails.
        """
        reservation = Reservation.objects.create(
            user=self.user, room=self.room,
            start_date="2026-07-01", end_date="2026-07-05",
            status="confirmed"
        )
        detail_url = reverse('reservations:reservation-detail', kwargs={'pk': reservation.pk})

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            detail_url, {'status': 'cancelled'}, format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'cancelled')

        mock_cancellation_task.assert_called_once_with(str(reservation.id))

    def test_send_cancellation_email_task_execution(self):
        """
        Verify execution of cancellation task renders email content and delivers message to mail outbox.
        """
        reservation = Reservation.objects.create(
            user=self.user, room=self.room,
            start_date="2026-07-10", end_date="2026-07-15",
            status="cancelled"
        )

        result = send_cancellation_email_task.apply(args=[str(reservation.id)])
        expected_msg = f'Cancellation email sent successfully to {self.user.email} for reservation {reservation.id}'
        self.assertEqual(result.result, expected_msg)

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]

        self.assertIn('Cancellation Confirmation', sent_email.subject)
        self.assertEqual(sent_email.to, [self.user.email])
        self.assertIn('RESERVATION CANCELLED', sent_email.body)

    def test_user_cannot_modify_others_reservations(self):
        """
        Verify users are blocked from updating or cancelling reservations belonging to other users.
        """
        reservation = Reservation.objects.create(
            user=self.other_user, room=self.room,
            start_date="2026-07-01", end_date="2026-07-05",
            status="confirmed"
        )
        detail_url = reverse('reservations:reservation-detail', kwargs={'pk': reservation.pk})

        self.client.logout()
        self.client.credentials()

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            detail_url, {'status': 'cancelled'}, HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )

        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    @patch('apps.reservations.tasks.send_reservation_voucher_task.delay')
    def test_user_can_pay_own_reservation_success(self, mock_voucher_task):
        """
        Verify payment endpoint confirms reservation and queues voucher delivery email task.
        """
        reservation = Reservation.objects.create(
            user=self.user, room=self.room,
            start_date="2026-08-01", end_date="2026-08-05",
            status="pending", payment_status="pending"
        )
        pay_url = reverse('reservations:reservation-pay', kwargs={'pk': reservation.pk})

        self.client.force_authenticate(user=self.user)
        data = {'payment_method': 'credit_card'}

        response = self.client.post(
            pay_url, data, format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reservation.refresh_from_db()
        self.assertEqual(reservation.payment_status, 'paid')
        self.assertEqual(reservation.status, 'confirmed')
        self.assertEqual(reservation.payment_method, 'credit_card')

        mock_voucher_task.assert_called_once_with(str(reservation.id))

    def test_user_cannot_pay_other_reservations(self):
        """
        Verify payment calls against other users' reservations are rejected.
        """
        reservation = Reservation.objects.create(
            user=self.other_user, room=self.room,
            start_date="2026-08-01", end_date="2026-08-05",
            status="pending", payment_status="pending"
        )
        pay_url = reverse('reservations:reservation-pay', kwargs={'pk': reservation.pk})

        self.client.force_authenticate(user=self.user)
        data = {'payment_method': 'credit card'}

        response = self.client.post(
            pay_url, data, HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )

        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_cannot_pay_already_paid_reservations(self):
        """
        Verify payment endpoint returns HTTP 400 if reservation status is already paid.
        """
        reservation = Reservation.objects.create(
            user=self.user, room=self.room,
            start_date="2026-08-01", end_date="2026-08-05",
            status="pending", payment_status="pending"
        )

        reservation.payment_status = 'paid'
        reservation.save()

        pay_url = reverse('reservations:reservation-pay', kwargs={'pk': reservation.pk})

        self.client.force_authenticate(user=self.user)
        data = {'payment_method': 'credit card'}

        response = self.client.post(
            pay_url, data, HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'],'This reservation has already been paid')

    def test_download_voucher_success(self):
        """
        Verify downloading PDF voucher for confirmed and paid reservation returns application/pdf stream.
        """
        reservation = Reservation.objects.create(
            user=self.user, room=self.room,
            start_date="2026-09-01", end_date="2026-09-05",
            status="confirmed", payment_status="paid", payment_method="credit card"
        )

        url = reverse('reservations:reservation-download-voucher', kwargs={'pk': reservation.pk})

        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['content-type'], 'application/pdf')
        self.assertIn('inline; filename=', response['Content-Disposition'])
        self.assertTrue(len(response.content) > 0)


    def test_cannot_download_voucher_if_not_paid(self):
        """
        Verify voucher downloading fails if payment status is pending.
        """
        reservation = Reservation.objects.create(
            user=self.user, room=self.room,
            start_date="2026-09-01", end_date="2026-09-05",
            status="pending", payment_status="pending"
        )
        url = reverse('reservations:reservation-download-voucher', kwargs={'pk': reservation.pk})

        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Voucher is only available for confirmed and paid reservations.')

    def test_user_cannot_download_others_voucher(self):
        """
        Verify users cannot download PDF vouchers for reservations held by other users.
        """
        reservation = Reservation.objects.create(
            user=self.other_user, room=self.room,
            start_date="2026-09-01", end_date="2026-09-05",
            status="confirmed", payment_status="paid", payment_method="credit card"
        )
        url = reverse('reservations:reservation-download-voucher', kwargs={'pk': reservation.pk})

        # print(f'\n--- SECURITY DEBUG ---')
        # print(f'Reservation holder (ID): {reservation.user.id}')
        # print(f'User logged in for the test (ID): {self.user.id}')
        # print(f'-------------------------')


        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)

        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_send_reservation_voucher_task_execution(self):
        """
        Verify execution of voucher task generates PDF payload and attaches it to outbound email.
        """
        reservation = Reservation.objects.create(
            user=self.user, room=self.room,
            start_date="2026-08-10", end_date="2026-08-15",
            status="confirmed", payment_status="paid"
        )

        result = send_reservation_voucher_task.apply(args=[str(reservation.id)])

        expected_msg = f'Voucher email sent successfully to {self.user.email} for reservation {reservation.id}'
        self.assertEqual(result.result, expected_msg)

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]

        self.assertIn('Your hotel reservation voucher', sent_email.subject)
        self.assertEqual(sent_email.to, [self.user.email])
        self.assertEqual(len(sent_email.attachments), 1)

        filename, pdf_data, mimetype = sent_email.attachments[0]
        self.assertEqual(filename, f'reservation_voucher_{reservation.id}.pdf')
        self.assertEqual(mimetype, 'application/pdf')
        self.assertTrue(len(pdf_data) > 0)

    def test_payment_details_is_encrypted_in_database(self):
        """
        Verify sensitive payment data is stored encrypted in raw database queries while decrypted via ORM.
        """
        sensitive_data = 'Card: 1234-5678-9012-3456; CVV: 999'

        reservation = Reservation.objects.create(
            user=self.user, room=self.room,
            start_date="2026-12-01", end_date="2026-12-05",
            status="confirmed", payment_details=sensitive_data,
            payment_method="credit card"
        )

        reservation_refresh = Reservation.objects.get(pk=reservation.pk)
        self.assertEqual(reservation_refresh.payment_details, sensitive_data)

        with connection.cursor() as cursor:
            cursor.execute('SELECT payment_details FROM reservations WHERE id = %s', [reservation.id])
            raw_value = cursor.fetchone()[0]

            self.assertNotEqual('1234-5678', raw_value)
            self.assertNotIn('CVV', raw_value)
