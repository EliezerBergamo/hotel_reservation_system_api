import uuid
import time
from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase
from apps.hotels.models import Hotel
from apps.accounts.models import User
from apps.rooms.models import Room
from apps.reservations.models import Reservation
from unittest.mock import patch

class BaseModelTest(TestCase):
    def test_metadata_fields_automation(self):
        hotel = Hotel.objects.create(
            name="Base Test Hotel",
            address="Av Core, 0",
            city="Core City",
        )

        self.assertIsNotNone(hotel.date_creation)
        self.assertIsNotNone(hotel.date_update)

    def test_metadata_fields_update(self):
        hotel = Hotel.objects.create(
            name="Update Hotel",
            address="St Core, 1",
            city="Update City",
        )

        original_update = hotel.date_update

        time.sleep(0.01)

        hotel.name = "Updated Name Hotel"
        hotel.save()

        hotel.refresh_from_db()

        self.assertGreater(hotel.date_update, original_update)

class IdempotencyMiddlewareTests(APITestCase):
    def setUp(self):
        cache.clear()

        self.user = User.objects.create_user(
            username="idempotent_guest",
            email="idempotent@example.com",
            password="password123"
        )
        self.hotel = Hotel.objects.create(
            name="Idempotency Hotel",
            address="Redis Ave, 1",
            city="Cache City",
        )
        self.room = Room.objects.create(
            hotel=self.hotel,
            room_number='666',
            price=150.00,
            capacity=2
        )
        self.url = reverse('reservations:reservation-list')

    def test_missing_idempotency_header_returns_400(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'user': self.user.id,
            'room': self.room.id,
            'start_date': '2026-07-10',
            'end_date': '2026-07-12',
        }

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('X-Idempotency-key header missing', str(response.json()))

    @patch('apps.accounts.tasks.send_welcome_email_task.delay')
    def test_duplicate_request_returns_cached_response(self, mock_celery_task):
        self.client.force_authenticate(self.user)

        unique_key = str(uuid.uuid4())
        data = {
            'user': self.user.id,
            'room': self.room.id,
            'start_date': '2026-07-15',
            'end_date': '2026-07-17',
        }

        response_01 = self.client.post(
            self.url, data, HTTP_X_IDEMPOTENCY_KEY=unique_key
        )
        self.assertEqual(response_01.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reservation.objects.count(), 1)

        mock_celery_task.assert_called_once_with(self.user.email)
        mock_celery_data_id = response_01.data['id']
        mock_celery_task.reset_mock()

        response_02 = self.client.post(
            self.url, data, HTTP_X_IDEMPOTENCY_KEY=unique_key
        )

        self.assertEqual(response_02.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reservation.objects.count(), 1)
        mock_celery_task.assert_not_called()

        response_02_json = response_02.json()
        self.assertEqual(mock_celery_data_id, response_02_json['id'])
