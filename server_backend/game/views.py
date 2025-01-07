# game/views.py
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Game, Player
from .serializers import GameSerializer, PlayerSerializer
from django.http import JsonResponse
@api_view(['GET'])
def get_game_info(request, gameId):
    try:
        game = Game.objects.get(gameId)
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
def add_player(request, gameId):
    try:
        game = Game.objects.get(gameId=gameId)
        player_data = request.data
        player = Player.objects.create(game=game, **player_data)
        
        serializer = PlayerSerializer(player)
        game_serializer = GameSerializer(game)
        
        return JsonResponse({
            "message": f"{player.name} added to the game",
            'game':game_serializer.data,
            "player": serializer.data,
        }, status=201)
    except Game.DoesNotExist:
        return Response({"error": "Game not found"}, status=404)

@api_view(['POST'])
def create_game(request):
    game_data = request.data
    game = Game.objects.create(**game_data)
    serializer = GameSerializer(game)
    return JsonResponse({
        'message': f"Game created successfully",
        'game':serializer.data,
    }, status=201)
