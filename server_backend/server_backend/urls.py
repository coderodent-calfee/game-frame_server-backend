# game-frame/server_backend/server_backend/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt import views as jwt_views
from django.views.generic import RedirectView

urlpatterns = [
    path('accounts/', include('accounts.urls')),
    # database
    path('dbadmin/', admin.site.urls),
    path('token/',
         jwt_views.TokenObtainPairView.as_view(),
         name ='token_obtain_pair'),
    path('token/refresh/',
         jwt_views.TokenRefreshView.as_view(),
         name ='token_refresh'),
    path('api/game/', include('game.urls')),
    path('', RedirectView.as_view(url='/accounts/home/')),
]
