from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Hotel
import uuid

class HotelTests(APITestCase):

    def setUp(self):
        user = get_user_model()
        self.user = user.objects.create_user(
            email='admin@test.com',
            password='123456',
            first_name='Tester',
            username='Tester123',
            role='manager'
        )
        self.list_url = reverse('hotels:hotel-list')

    def test_list_hotels(self):
        Hotel.objects.create(
            name="Hotel A",
            address="St A",
            city="City A"
        )
        Hotel.objects.create(
            name="Hotel B",
            address="St B",
            city="City B"
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 2)

    def test_post_hotel(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'name': 'Hotel C',
            'address': 'St C',
            'city': 'City C'
        }

        response = self.client.post(
            self.list_url, data, format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Hotel.objects.count(), 1)
        self.assertEqual(response.data['name'], "Hotel C")

    def test_patch_hotel(self):
        hotel = Hotel.objects.create(
            name="Hotel D",
            address="St D",
            city="City D"
        )
        url = reverse('hotels:hotel-detail', kwargs={'pk': hotel.id})

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            url, {'name': 'Edited'}, format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        hotel.refresh_from_db()
        self.assertEqual(hotel.name, 'Edited')

    def test_delete_hotel(self):
        hotel = Hotel.objects.create(
            name="Hotel E",
            address="St E",
            city="City E"
        )
        url = reverse('hotels:hotel-detail', kwargs={'pk': hotel.id})

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(url, HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Hotel.objects.count(), 0)

    def test_without_login(self):
        data = {
            'name': 'Hotel F',
            'address': 'St F',
            'city': 'City F'
        }

        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_hotel_not_found(self):
        self.client.force_authenticate(user=self.user)

        url = reverse('hotels:hotel-detail', kwargs={'pk': uuid.uuid4()})

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_hotel_bad_request(self):
        data = {
            'address': 'St G',
            'city': 'City G'
        }

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.list_url, data, format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_hotel_by_city(self):
        Hotel.objects.create(name="Hotel G", address="St G", city="City G")
        Hotel.objects.create(name="Hotel H", address="St H", city="City H")

        url = self.list_url + '?city=City H'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['city'], 'City H')

    def test_search_hotel_by_name(self):
        Hotel.objects.create(name="Hotel I", address="St I", city="City I")
        Hotel.objects.create(name="Hotel J", address="St J", city="City J")

        url = self.list_url + '?search=Hotel I'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIn("Hotel I", response.data['results'][0]['name'])

    def test_search_hotel_by_address(self):
        Hotel.objects.create(name="Hotel K", address="St K", city="City K")
        Hotel.objects.create(name="Hotel L", address="St L", city="City L")

        url = self.list_url + '?search=K'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIn("K", response.data['results'][0]['address'])

    def test_search_no_results(self):
        url = self.list_url + '?search=non-existent'
        response = self.client.get(url)
        self.assertEqual(len(response.data['results']), 0)

    def test_order_hotels_by_name(self):
        Hotel.objects.create(name="Hotel M", address="St M", city="City M")

        url = self.list_url + '?ordering=name'
        response = self.client.get(url)

        self.assertEqual(response.data['results'][0]['name'], 'Hotel M')
