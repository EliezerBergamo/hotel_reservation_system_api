import uuid
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from apps.hotels.models import Hotel
from .models import Room

class RoomTest(APITestCase):
    def setUp(self):
        user = get_user_model()
        self.user = user.objects.create_user(
            email='admin@test.com',
            password='123456',
            first_name='Tester',
            username='Tester123',
            role='manager'
        )

        self.uuid = uuid
        self.hotel = Hotel.objects.create(name='Test Hotel', address='Rd Test', city='Testing')

        self.list_url = reverse('rooms:room-list')

    def test_post_room(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'hotel': self.hotel.id,
            'room_number': '101',
            'room_type': 'Single',
            'price': '150.00'
        }

        response = self.client.post(
            self.list_url, data, format='json', HTTP_X_IDEMPOTENCY_KEY=str(self.uuid.uuid4())
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Room.objects.count(), 1)

    def test_post_room_unauthorized(self):
        data = {
            'hotel': self.hotel.id,
            'room_number': '102',
            'price': '100.00'
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_filter_rooms_no_results(self):
        Room.objects.create(hotel=self.hotel, room_number='103', price=100)
        url = self.list_url + '?min_price=500'
        response = self.client.get(url)
        self.assertEqual(len(response.data['results']), 0)

    def test_update_room_price(self):
        room = Room.objects.create(hotel=self.hotel, room_number='104', price=100)
        url = reverse('rooms:room-detail', kwargs={'pk': room.id})
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            url, {'price': '250.00'}, format='json', HTTP_X_IDEMPOTENCY_KEY=str(self.uuid.uuid4())
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        room.refresh_from_db()
        self.assertEqual(float(room.price), 250.00)

    def test_filter_rooms_by_price_range(self):
        Room.objects.create(hotel=self.hotel, room_number='102', room_type='Single', price=100)
        Room.objects.create(hotel=self.hotel, room_number='103', room_type='Single', price=300)
        Room.objects.create(hotel=self.hotel, room_number='104', room_type='Single', price=500)

        url = self.list_url + '?min_price=200&max_price=400'
        response = self.client.get(url)

        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(float(response.data['results'][0]['price']), 300.00)

    def test_order_rooms_by_price_ascending(self):
        Room.objects.create(hotel=self.hotel, room_number='105', room_type='Single', price=500)
        Room.objects.create(hotel=self.hotel, room_number='106', room_type='Single', price=100)

        url = self.list_url + '?ordering=price'
        response = self.client.get(url)

        self.assertEqual(float(response.data['results'][0]['price']), 100.00)

    def test_delete_room(self):
        room = Room.objects.create(
            hotel=self.hotel,
            room_number='107',
            room_type='Deluxe',
            price=200
        )
        url = reverse('rooms:room-detail', kwargs={'pk': room.id})

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(url, HTTP_X_IDEMPOTENCY_KEY=str(self.uuid.uuid4()))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Room.objects.filter(id=room.id).exists())
        self.assertTrue(Hotel.objects.filter(id=self.hotel.id).exists())

    def test_filter_rooms_not_found_price(self):
        Room.objects.create(hotel=self.hotel, room_number='108', price=100)

        url = self.list_url + '?min_price=10000'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_cascade_delete_hotel_rooms(self):
        hotel_extra = Hotel.objects.create(name="Hotel A", address="St A", city="City A")
        Room.objects.create(hotel=hotel_extra, room_number='109', room_type='Single', price=100)

        self.client.force_authenticate(user=self.user)
        url = reverse('hotels:hotel-detail', kwargs={'pk': hotel_extra.id})

        response = self.client.delete(url, HTTP_X_IDEMPOTENCY_KEY=str(self.uuid.uuid4()))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Hotel.objects.filter(id=hotel_extra.id).exists())

        self.assertFalse(Room.objects.filter(room_number='109').exists())
