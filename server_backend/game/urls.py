# game/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('newGame/', views.create_game, name='create_game'),
    path('<str:gameId>/info/', views.get_game_info, name='get_game_info'),
    path('<str:gameId>/join/', views.add_player, name='add_player'),
    path('', views.get_games, name='get_games'),

]
