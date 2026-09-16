"""
Unit and integration tests for Accounts endpoints, authentication, and background tasks.
"""

from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from apps.reservations.models import Reservation
from apps.hotels.models import Hotel
from apps.rooms.models import Room
from django.core import mail
from django.core.cache import cache
from apps.accounts.tasks import send_welcome_email_task
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.test import override_settings

User = get_user_model()

class AccountsTest(APITestCase):
    """
    Test suite covering accounts endpoints, security mechanisms, and user life cycle.
    """
    def setUp(self):
        """
        Set up baseline users and URL endpoints for tests.
        """
        self.manager_user = User.objects.create_user(
            username='manager',
            password='password123',
            email='manager@test.com',
            role='manager',
        )

        self.guest_user = User.objects.create_user(
            username='guest',
            password='password123',
            email='guest@test.com',
            role='guest',
        )

        self.login_url = reverse('token_obtain_pair')
        self.register_url = reverse('accounts:user-list')

    def tearDown(self):
        """
        Clear cache after each test execution.
        """
        cache.clear()

    def test_user_registration_success(self):
        """
        Verify successful user registration.
        """
        data = {
            'username': 'new_guest',
            'password': 'passwordGuest',
            'email': 'new@test.com',
            'role': 'guest',
            'name': 'New Guest',
            'phone': '11999999999',
        }
        response = self.client.post(self.register_url, data, format='json')

        if response.status_code != status.HTTP_201_CREATED:
            print(f'status code: {response.data}')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.filter(username='new_guest').count(), 1)

    def test_password_is_properly_hashed(self):
        """
        Ensure passwords are never stored in plain text.
        """
        user = User.objects.get(username='guest')
        self.assertNotEqual(user.password, 'password123')
        self.assertTrue(user.check_password('password123'))

    def test_jwt_login_obtains_tokens(self):
        """
        Ensure valid credentials obtain JWT access and refresh tokens.
        """
        data = {
            'username': 'manager',
            'password': 'password123',
        }
        response = self.client.post(self.login_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_guest_cannot_access_manager_actions(self):
        """
        Ensure role-based authorization blocks guest access to manager routes.
        """
        self.client.force_authenticate(user=self.guest_user)

        url = reverse('hotels:hotel-list')
        data = {
            'name': 'Hotel X',
            'address': 'St X',
            'city': 'X city',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_with_wrong_password_fails(self):
        """
        Verify login failure on invalid password.
        """
        data = {
            'username': 'manager',
            'password': 'wrongPassword',
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklist_token(self):
        """
        Ensure refresh token is blacklisted upon logging out.
        """
        login_res = self.client.post(self.login_url, {
            'username': 'guest',
            'password': 'password123',
        })
        refresh_token = login_res.data['refresh']

        logout_url = reverse('accounts:logout')
        self.client.force_authenticate(user=self.guest_user)
        response = self.client.post(reverse('accounts:logout'), {'refresh': refresh_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

    def test_access_with_invalid_token_fails(self):
        """
        Ensure invalid JWT tokens return unauthorized status.
        """
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')

        url = reverse('hotels:hotel-list')
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.client.credentials()

    def test_user_can_update_own_profile(self):
        """
        Verify users can patch their own profile.
        """
        self.client.force_authenticate(user=self.guest_user)

        url = reverse('accounts:user-detail', kwargs={'pk': self.guest_user.pk})
        data = {
            'name': 'Updated Name',
            'phone': '11988887777',
        }

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.guest_user.refresh_from_db()
        self.assertEqual(self.guest_user.name,'Updated Name')

    def test_user_cannot_update_others_profile(self):
        """
        Ensure users cannot modify other profiles.
        """
        self.client.force_authenticate(user=self.guest_user)

        url = reverse('accounts:user-detail', kwargs={'pk': self.manager_user.pk})
        data = {
            'name': 'Attempted Invasion',
        }

        response = self.client.patch(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_welcome_email_tasks_sends_email(self):
        """
        Verify welcome email task execution.
        """
        mail.outbox.clear()
        mail_test = self.guest_user.email

        send_welcome_email_task(mail_test)

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn(mail_test, sent.to)
        self.assertIn('Welcome', sent.subject)

    def test_user_cannot_escalate_privileges_on_registration(self):
        """
        Verify privilege escalation prevention on registration.
        """
        data = {
            'username': 'sneaky_user',
            'password': 'password123',
            'email': 'sneaky@test.com',
            'name': 'Sneaky Guest',
            'phone': '11999999999',
            'role': 'manager',
            'hotel': 1
        }
        response = self.client.post(self.register_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        created_user = User.objects.get(username='sneaky_user')
        self.assertEqual(created_user.role, 'guest')
        self.assertIsNone(created_user.hotel)

    def test_anon_rate_limiting_triggers_too_many_requests(self):
        """
        Test rate limiting mechanism against brute force registration requests.
        """
        data = {
            'username': 'brute_force_attempt',
            'password': 'password123',
        }

        for i in range(5):
            self.client.post(self.register_url, data, format='json')

        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('detail', response.data)

        cache.clear()

    def test_user_can_sof_delete_own_account(self):
        """
        Verify user soft account deletion mechanism.
        """
        self.client.force_authenticate(user=self.guest_user)
        url = reverse('accounts:user-detail', kwargs={'pk': self.guest_user.pk})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.guest_user.refresh_from_db()
        self.assertFalse(self.guest_user.is_active)

    def test_user_cannot_delete_account_with_active_reservations(self):
        """
        Ensure users with active reservations cannot delete their account.
        """
        hotel = Hotel.objects.create(
            name='Test Hotel',
            city='Test City',
            address='Test Address',
        )

        room = Room.objects.create(
            hotel=hotel,
            room_number=101,
            room_type='Standard',
            price=100.00,
            capacity=2
        )

        Reservation.objects.create(
            user=self.guest_user,
            room = room,
            start_date='2026-08-01',
            end_date='2026-08-05',
            status='confirmed'
        )

        self.client.force_authenticate(user=self.guest_user)
        url = reverse('accounts:user-detail', kwargs={'pk': self.guest_user.pk})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.guest_user.refresh_from_db()
        self.assertTrue(self.guest_user.is_active)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    )
    def test_password_reset_flow_success(self):
        """
        Verify complete password reset workflow.
        """
        mail.outbox.clear()

        reset_request_url = reverse('accounts:password_reset_request')
        response = self.client.post(reset_request_url, {'email': self.guest_user.email}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

        uid = urlsafe_base64_encode(force_bytes(self.guest_user.pk))
        token = default_token_generator.make_token(self.guest_user)

        reset_confirmation_url = reverse('accounts:password_reset_confirm')
        confirm_data = {
            'uid': uid,
            'token': token,
            'new_password': 'NewPassword123',
        }
        confirm_response = self.client.post(reset_confirmation_url, confirm_data, format='json')

        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)

        self.guest_user.refresh_from_db()
        self.assertTrue(self.guest_user.check_password('NewPassword123'))

    def test_password_reset_confirm_with_invalid_token_fails(self):
        """
        Ensure invalid tokens fail during password reset.
        """
        uid = urlsafe_base64_encode(force_bytes(self.guest_user.pk))
        invalid_token = 'invalid_token'

        url = reverse('accounts:password_reset_confirm')
        data = {
            'uid': uid,
            'token': invalid_token,
            'new_password': 'SomePassword123',
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_user_can_delete_account_with_past_or_cancelled_reservations(self):
        """
        Ensure users with past or cancelled reservations can delete their account.
        """
        hotel = Hotel.objects.create(
            name='Historical Hotel',
            city='Historical City',
            address='Historical Address',
        )
        room = Room.objects.create(
            hotel=hotel,
            room_number=202,
            room_type='Suite',
            price=250.00,
            capacity=2
        )

        Reservation.objects.create(
            user=self.guest_user,room=room,
            start_date='2026-01-01', end_date='2026-01-05',
            status='checked_out',
        )

        self.client.force_authenticate(user=self.guest_user)
        url = reverse('accounts:user-detail', kwargs={'pk': self.guest_user.pk})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.guest_user.refresh_from_db()
        self.assertFalse(self.guest_user.is_active)

    def test_user_cannot_delete_another_users_account(self):
        """
        Ensure cross-account deletion is blocked.
        """
        self.client.force_authenticate(user=self.guest_user)

        url = reverse('accounts:user-detail', kwargs={'pk': self.manager_user.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.manager_user.refresh_from_db()
        self.assertTrue(self.manager_user.is_active)
