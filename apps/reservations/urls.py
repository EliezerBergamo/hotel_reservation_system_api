"""
URL Routing Configuration for Reservations API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReservationViewSet

router = DefaultRouter()
router.register(r'', ReservationViewSet, basename='reservation')

urlpatterns = [
    path('', include(router.urls)),
]