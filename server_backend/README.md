This backend handles access to the database and sockets
users (with a user Id) are given a session Id when they connect with a device
users with a session ID are given a player Id when they join a game
It should be legal to have one user, using two devices to be in two games, 
or even join as two different players in one game

API:

accounts/
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
body
{
  "username" : string
  "password" : string
}
response
{
    "refresh": string,
    "access": string,
    "userId": uuid like string
}




    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', register, name='register'),
    path('protected/', protected_view, name='protected_view'), # test token protection
    path('', get_accounts, name='get_accounts'),

game/
    path('new/', views.create_game, name='create_game'),
    path('<str:gameId>/info/', views.get_game_info, name='get_game_info'),
    path('<str:gameId>/add/', views.add_player, name='add_player'),
    path('<str:gameId>/claim/', views.claim_player, name='claim_player'),
    path('<str:gameId>/name/', views.name_player, name='name_player'),
    path('', views.get_games, name='get_games'),
#    path('<str:gameId>/echo/', views.echo_body, name='echo'),

use /server/start.bat to launch server