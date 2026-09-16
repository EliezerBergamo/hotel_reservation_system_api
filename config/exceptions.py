"""
Global Exception Handlers for Django REST Framework.
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for Django REST Framework to standardize error responses
    and prevent raw 500 server stack traces from exposing sensitive internal details.
    """
    # Call DRF's default exception handler first to get the standard error response
    response = exception_handler(exc, context)

    if response is not None:
        # Standardize expected DRF errors (400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, etc.)
        custom_data = {
            "status_code": response.status_code,
            "error": "Validation Error" if response.status_code == 400 else "API Error",
            "details": response.data
        }

        # If response.data contains a direct 'detail' string, extract it to top-level
        if isinstance(response.data, dict) and "detail" in response.data:
            custom_data["error"] = response.data["detail"]
            del custom_data["details"]

        response.data = custom_data
    else:
        # Handle unhandled Python/Django exceptions (HTTP 500)
        view = context.get('view')
        request = context.get('request')

        logger.error(
            f"Unhandled Exception at {request.path if request else 'Unknown Path'} "
            f"in {view.__class__.__name__ if view else 'Unknown View'}: {str(exc)}",
            exc_info=True
        )

        response = Response(
            {
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "error": "Internal Server Error",
                "details": "An unexpected error occurred on the server. Please contact support if the issue persists."
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response
