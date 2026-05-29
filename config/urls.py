from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api-auth/', include('rest_framework.urls')),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('api/accounts/', include(('apps.accounts.urls', 'accounts'), namespace='accounts')),
    path('api/hotels/', include(('apps.hotels.urls', 'hotels'), namespace='hotels')),
    path('api/rooms/', include(('apps.rooms.urls', 'rooms'), namespace='rooms')),
    path('api/reservations/', include(('apps.reservations.urls', 'reservations'), namespace='reservations')),
]
