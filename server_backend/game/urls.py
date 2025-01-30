# game/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('new/', views.create_game, name='create_game'),
    path('<str:gameId>/info/', views.get_game_info, name='get_game_info'),
    path('<str:gameId>/add/', views.add_player, name='add_player'),
    path('<str:gameId>/claim/', views.claim_player, name='claim_player'),
    path('<str:gameId>/name/', views.name_player, name='name_player'),
    path('', views.get_games, name='get_games'),
#    path('<str:gameId>/echo/', views.echo_body, name='echo'),
]
