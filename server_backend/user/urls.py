# game-frame/user/urls.py
from django.urls import path, include
from .views import CustomGoogleLogin
# from .views import google_callback

urlpatterns = [
    # Authentication URLs (login, logout, password reset)
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/social/google/', CustomGoogleLogin.as_view(), name='google_login'),
    # Registration and social authentication URLs (signup and social logins)
    path('auth/registration/', include('dj_rest_auth.registration.urls')),
]
