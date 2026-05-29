import uuid
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User
from apps.hotels.models import Hotel
from apps.rooms.models import Room
from apps.reservations.models import Reservation
from unittest.mock import patch

class ReservationTests(APITestCase):

    def setUp(self):
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

    @patch('apps.accounts.tasks.send_welcome_email_task.delay')
    def test_create_reservation_success(self, mock_celery_task):
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

    def test_user_can_only_see_own_reservations(self):
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

    def test_user_can_cancel_own_reservations(self):
        reservation = Reservation.objects.create(
            user=self.user, room=self.room,
            start_date="2026-07-01", end_date="2026-07-05",
            status="confirmed"
        )
        detail_url = reverse('reservations:reservation-detail', kwargs={'pk': reservation.pk})

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            detail_url, {'status': 'cancelled'}, HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'cancelled')

    def test_user_cannot_modify_others_reservations(self):
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