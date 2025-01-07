# game-frame/server_backend/server_backend/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt import views as jwt_views
from user.views import GoogleCallbackView


urlpatterns = [
    path('accounts/google/login/callback/', GoogleCallbackView.as_view(), name='google_callback'),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('auth/registration/', include('dj_rest_auth.registration.urls')),
    path('token/',
         jwt_views.TokenObtainPairView.as_view(),
         name ='token_obtain_pair'),
    path('token/refresh/',
         jwt_views.TokenRefreshView.as_view(),
         name ='token_refresh'),
    path('api/game/', include('game.urls')),
]
