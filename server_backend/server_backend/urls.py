# game-frame/server_backend/server_backend/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('api/game/', include('game.urls')),
    path('api/accounts/', include('accounts.urls')),
]
