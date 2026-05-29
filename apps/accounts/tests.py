from django.core import mail
from apps.accounts.tasks import send_welcome_email_task
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.test import override_settings

User = get_user_model()

class AccountsTest(APITestCase):
    def setUp(self):
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

    def test_user_registration_success(self):
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
        user = User.objects.get(username='guest')
        self.assertNotEqual(user.password, 'password123')
        self.assertTrue(user.check_password('password123'))

    def test_jwt_login_obtains_tokens(self):
        data = {
            'username': 'manager',
            'password': 'password123',
        }
        response = self.client.post(self.login_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_guest_cannot_access_manager_actions(self):
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
        data = {
            'username': 'manager',
            'password': 'wrongPassword',
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklist_token(self):
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
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')

        url = reverse('hotels:hotel-list')
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.client.credentials()

    def test_user_can_update_own_profile(self):
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
        self.client.force_authenticate(user=self.guest_user)

        url = reverse('accounts:user-detail', kwargs={'pk': self.manager_user.pk})
        data = {
            'name': 'Attempted Invasion',
        }

        response = self.client.patch(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_welcome_email_tasks_sends_email(self):
        mail.outbox.clear()
        mail_test = self.guest_user.email

        send_welcome_email_task(mail_test)

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn(mail_test, sent.to)
        self.assertIn('Welcome', sent.subject)
