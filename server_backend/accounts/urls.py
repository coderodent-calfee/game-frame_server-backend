# accounts/urls.py
from django.urls import path
from .views import register, protected_view
from rest_framework_simplejwt.views import TokenRefreshView
from .views import CustomTokenObtainPairView
from .views import get_accounts

urlpatterns = [
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', register, name='register'),
    path('protected/', protected_view, name='protected_view'), # test token protection
    path('', get_accounts, name='get_accounts'),
]
