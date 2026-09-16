"""
Custom Database Model Fields.
"""

from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet

class EncryptedTextField(models.TextField):
    """
    Custom Django TextField that transparently encrypts data before storing
    in the database and decrypts it when retrieved using Fernet symmetric encryption.
    """
    description = 'Stores encrypted text at rest'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
        if not key:
            key = b'd3ZpX2JsaW5kYWdlbV9kZV9jb2RpZ29fc2VndXJvXzE='
        self.fernet = Fernet(key)

    def get_prep_value(self, value):
        """
        Encrypts the plain text value prior to database write operations.
        """
        value = super().get_prep_value(value)
        if value is None:
            return value
        if isinstance(value, str):
            value = value.encode('utf-8')
        encrypted_value = self.fernet.encrypt(value)
        return encrypted_value.decode('utf-8')

    def from_db_value(self, value, expression, connection):
        """
        Decrypts the encrypted database string when fetching database records.
        """
        if value is None:
            return value
        try:
            decrypted_value = self.fernet.decrypt(value.encode('utf-8'))
            return decrypted_value.decode('utf-8')
        except Exception:
            return value

    def to_python(self, value):
        """
        Converts the database value into a Python object.
        """
        if value is None:
            return value
        return value
