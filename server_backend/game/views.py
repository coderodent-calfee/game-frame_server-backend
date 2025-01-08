# game/views.py
from .serializers import GameSerializer, PlayerSerializer
from django.http import JsonResponse

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Game, Player
from accounts.models import Account
from rest_framework import status

@api_view(['GET'])
def get_game_info(request, gameId):
    try:
        game = Game.objects.get(gameId=gameId)
        players = game.players.all()  # Fetch related players
        player_data = [{'playerId': player.playerId, 'name': player.name, 'game_identifier': player.game_identifier} for player in players]

        if not player_data:
            print(f"No players found for game {gameId}")  # Debugging log

        return JsonResponse({
            'game':{
                'gameId': game.gameId,
                'status': game.status,
                'players': player_data,
            }
        })
    except Game.DoesNotExist:
        return Response({"error": "Game not found"}, status=404)

@api_view(['POST'])
def create_game(request):
    user_id = request.query_params.get('userId')
    print(f"user_id passed to create_game is {user_id}")  # Debugging log
    #todo: save creator id too
    game_data = request.data
    game = Game.objects.create(**game_data)
    serializer = GameSerializer(game)
    return JsonResponse({
        'message': f"Game created successfully",
        'game':serializer.data,
    }, status=201)




@api_view(['POST'])
def add_player(request, gameId):

    print(f"add_player {gameId}")  # Debugging log

    # Retrieve the game object
    game = get_object_or_404(Game, gameId=gameId)

    print(f"add_player game {game.gameId}")  # Debugging log
    # Extract userId from query parameters
    user_id = request.query_params.get('userId')
    print(f"add_player user_id {user_id}")  # Debugging log

    if not user_id:
        return Response({'error': 'userId parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

    print(f"Get the Account object related to the userId")  # Debugging log
    # Get the Account object related to the userId
    try:
        user_account = Account.objects.get(userId=user_id)
    except Account.DoesNotExist:
        return Response({'error': 'Account not found for the given userId'}, status=status.HTTP_404_NOT_FOUND)

    print(f"# Prepare player data")  # Debugging log
    # Prepare player data
    player_data = {
        'game': game,
        'name': request.data.get('name', str(user_account)),  # Assume name is passed in the request body
        'userId': user_account,
    }
    print(f"player data : {player_data}")  # Debugging log

    # Create the player
    player = Player.objects.create(**player_data)
    print(f"# Created the player!!")  # Debugging log


    players = game.players.all()  # Fetch related players
    player_data = [{
        'playerId': player.playerId, 
        'name': player.name, 
        'game_identifier': player.game_identifier,
        'userId': str(player.userId.userId),
    } for player in players]

    # Prepare the response
    response_data = {
        'message': f"{player.name} added to the game",
        'game':{
            'gameId': game.gameId,
            'status': game.status,
            'players': player_data,
        },
        'player': {
            'playerId': player.playerId,
            'name': player.name,
            'game_identifier': player.game_identifier,
            'userId': str(player.userId.userId), 
        }
    }
    print(f"response_data : {response_data}")  # Debugging log

    # Return a response indicating success
    return Response(response_data, status=status.HTTP_201_CREATED)
