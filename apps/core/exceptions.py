"""
Global Exception Handler Module.
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.db import DatabaseError, OperationalError

logger = logging.getLogger(__name__)

def global_exception_handler(exc, context):
    """
    Custom exception handler to intercept database errors, concurrency locks,
    and unhandled system exceptions to prevent stack trace leaks.
    """
    response =  exception_handler(exc, context)

    if response is not None:
        return response

    if isinstance(exc, (OperationalError, DatabaseError)):
        error_message = str(exc).lower()

        if 'could not obtain lock' in error_message or 'deadlock detected' in error_message:
            logger.warning(f'Conflict detected: {error_message} in the context {context.get('view')}')
            return Response(
                {'error': 'The selected room is currently undergoing maintenance. Please try again.'},
                status=status.HTTP_409_CONFLICT,
            )
        logger.error(f'Protected Database Error: {error_message}', exc_info=True)

        return Response(
            {'error': 'An internal secure data processing error has occurred.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    logger.error(f'Unhandled Error: {str(exc)}', exc_info=True)
    return Response(
        {'error': 'Internal Server Error'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )

