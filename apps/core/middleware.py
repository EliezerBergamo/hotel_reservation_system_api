"""
Custom System Middleware Components.
"""

import json
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework import status

class IdempotencyMiddleware:
    """
    Middleware ensuring idempotency for POST requests on reservation endpoints
    using Redis cache and custom X-Idempotency-key header checking.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST' and 'api/reservations/' in request.path:

            if 'text/html' in request.META.get('HTTP_ACCEPT', ''):
                return self.get_response(request)

            idempotency_key = request.headers.get('X-Idempotency-key')

            if not idempotency_key:
                return JsonResponse(
                    {"error": "X-Idempotency-key header missing"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user_id = request.user.id if request.user.is_authenticated else 'anonymous'
            redis_key = f'idempotency:{user_id}:{idempotency_key}'
            cached_response = cache.get(redis_key)

            if cached_response is not None:
                return JsonResponse(
                    cached_response['data'],
                    status=cached_response['status']
                )

            response = self.get_response(request)

            if 200 <= response.status_code < 500:
                try:
                    if hasattr(response, 'render') and callable(response.render):
                        response.render()

                    response_data = json.loads(response.content.decode('utf-8'))

                    cache_data = {
                        'data': response_data,
                        'status': response.status_code
                    }
                    cache.set(redis_key, cache_data, timeout=7200)
                except (json.JSONDecodeError, AttributeError, ValueError):
                    pass

            return response

        return self.get_response(request)