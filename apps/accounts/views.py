"""
API Views and ViewSets for account authentication, user management, and password recovery.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from .models import User
from .serializers import UserSerializer
from apps.accounts.tasks import send_password_reset_email_task
from apps.reservations.models import Reservation

User = get_user_model()

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission allowing owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj == request.user

class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Users, profile updates, and soft account deletions.
    """
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer

    def get_permissions(self):
        """
        Dynamically assigns permissions based on action.
        """
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """
        Retrieves current authenticated user profile.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Validates account deletion preventing soft-delete if active reservations exist.
        """
        instance = self.get_object()

        has_active_reservations = Reservation.objects.filter(
            user=instance,
            status__in=['pending', 'confirmed']
        ).exists()

        if has_active_reservations:
            return Response(
                {'error': 'Cannot delete account with active or pending hotel reservations.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().destroy(request, *args, **kwargs)

    def perform_destroy(self, instance):
        """
        Executes soft-deletion by setting is_active to False instead of removing record.
        """
        instance.is_active = False
        instance.save()

class LogoutView(APIView):
    """
    Endpoint to invalidate JWT refresh tokens.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'detail': 'Successfully logged out'}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetRequestView(APIView):
    """
    Endpoint requesting a password reset email token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Please provide an email address'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            send_password_reset_email_task.delay(user.id, uid, token)
        except User.DoesNotExist:
            pass

        return Response(
            {'detail': 'If the email matches an active account, a reset token has been sent.'},
            status=status.HTTP_200_OK
        )

class PasswordResetConfirmView(APIView):
    """
    Endpoint confirming password reset via UID and token validation.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        uuid64 = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not all([uuid64, token, new_password]):
            return Response(
                {'error': 'All fields (uid, token, new_password) are required.'}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            uid = force_str(urlsafe_base64_decode(uuid64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'error': 'Invalid user ID reference.'}, status=status.HTTP_400_BAD_REQUEST
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {'error': 'Invalid or expired password reset token.'}, status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.is_active = True
        user.save()

        return Response(
            {'detail': 'Password has been successfully reset.'}, status=status.HTTP_200_OK
        )
