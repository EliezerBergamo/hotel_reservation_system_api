"""
Serializers for User authentication, registration, and profile management.
"""

from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model handles password hashing and prevents field privilege escalation.
    """

    password = serializers.CharField(write_only=True)
    role = serializers.CharField(read_only=True)
    hotel = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'name',
            'email',
            'phone',
            'role',
            'hotel',
            'password',
            'date_creation',
        ]

    def create(self, validated_data):
        """
        Creates a new User instance using Django's helper method to ensure password hashing.
        """
        user = User.objects.create_user(**validated_data)
        return user
