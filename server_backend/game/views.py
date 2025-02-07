# game/views.py
import json
import uuid

from .serializers import GameSerializer, PlayerSerializer
from django.http import JsonResponse

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Game, Player
from accounts.models import Account
from rest_framework import status
from uuid import UUID
from .consumers import socketSession, get_player_sessions_from_room, get_session_players_from_user, get_user_from_session, \
    GameConsumer
import logging

logger = logging.getLogger(__name__)

def loggering(message):
    print(message)
    logger.info(message)  # Debugging log


def string_keys_values(in_data):
    if type(in_data) is dict:
        out = {}
        for k, v in in_data.items():
            key = string_keys_values(k)
            value = string_keys_values(v)
            out[key] = value
    elif type(in_data) is list:
        out = []
        for v in in_data:
            value = string_keys_values(v)
            out.append(value)
    else:
        out = str(in_data)
    return out

def jd(arg):
    return json.dumps(string_keys_values(arg), indent=4, sort_keys=True)


def prepare_player_data(players, user_id=None):
    active_sessions = get_player_sessions_from_room(players[0].game_identifier) if players else {}
    return [
        {
            'playerId': str(player.playerId),
            'name': player.name,
            'game_identifier': player.game_identifier,
            'userId': str(player.userId.userId),  # Debugging: show all user IDs in the game
            # **({'userId': str(player.userId.userId)} if str(player.userId.userId) == str(user_id) else {}) # no debug: only include owners user Id
            'isActive': str(player.playerId) in active_sessions  # Check if player is active
        }
        for player in players
    ]

def prepare_game_data(game, players=None):
    if players is None:
        players = game.players.select_related('userId').all()
    player_data = prepare_player_data(players)

    if not player_data:
        logger.info(f"*** GAME_INFO No players found for game {game.gameId}")

    return {
        'gameId': game.gameId,
        'status': game.status,
        'players': player_data,
    }


@api_view(['POST'])
def create_game(request):
    user_id = request.query_params.get('userId')
    logger.info(f"user_id passed to create_game is {user_id}")  # Debugging log
    #todo: save creator id too
    game_data = request.data
    game = Game.objects.create(**game_data)
    serializer = GameSerializer(game)
    return JsonResponse({
        'message': f"Game created successfully",
        'game':serializer.data,
    }, status=201)

@api_view(['GET'])
def get_game_info(request, gameId):
    user_id = request.query_params.get('userId')
    logger.info(f"*** GAME_INFO user_id passed to get_game_info is {user_id[:6] if user_id else None}")  # Debugging log

    session_id = request.query_params.get('sessionId')
    logger.info(f"*** GAME_INFO session_id passed to get_game_info is {session_id[:6] if session_id else None}")  # Debugging log

    try:
        game = Game.objects.get(gameId=gameId)
        game_info_response = {
            'game': prepare_game_data(game),
            'socketSession': socketSession
        }
        return JsonResponse(game_info_response, status=200)

    except Game.DoesNotExist:
        return Response({"error": "Game not found"}, status=404)


@api_view(['GET'])
def get_games(request):
    games = Game.objects.all()
    data = games.values('gameId', 'status')  # Fetch specific fields
    return Response(data, status=status.HTTP_200_OK)

@api_view(['POST'])
def name_player(request, gameId):
    game = get_object_or_404(Game, gameId=gameId)
    if game.players.count() < 1:
        return JsonResponse({'error': f"No players found for game {gameId}"}, status=404)

    try:
        body_data = json.loads(request.body)
        user_id_str = body_data.get('userId')
        new_player_name = body_data.get('name')
        player_id_str = body_data.get('playerId')

        if not all([user_id_str, new_player_name, player_id_str]):
            return JsonResponse({'error': 'playerId, userId and name parameters are required'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    try:
        player = Player.objects.select_related('userId').get(playerId=uuid.UUID(player_id_str), game=game)
    except Player.DoesNotExist:
        return JsonResponse({'error': f"No player {player_id_str} to rename for game {gameId}"}, status=404)
    except ValueError:
        return JsonResponse({'error': f"Invalid player id {player_id_str} to rename for game {gameId}"}, status=400)

    if str(player.userId.userId) != user_id_str:
        return JsonResponse({'error': f"You cannot rename a player that is not your own. player:{player_id_str}"}, status=401)

    original_name = player.name
    player.name = new_player_name
    player.save()

    # Notify via WebSocket
    player_announce = {
        'message': f"{original_name} renamed to {new_player_name}",
        'type': 'name_player',
        'playerId': str(player.playerId),
        'name': player.name,
        'game_identifier': player.game_identifier,
    }
    GameConsumer.send_message_to_group(
        group_name=f"game_{game.gameId}",
        json_data=player_announce
    )

    # Prepare response
    response_data = {
        'player': prepare_player_data([player])[0],
        'game': prepare_game_data(game)
    }

    return JsonResponse(response_data, status=200)


@api_view(['POST'])
def claim_player(request, gameId):
    body_data = json.loads(request.body)
    session_id_str = body_data.get('sessionId', None)

    if not session_id_str:
        return JsonResponse({"error": f"No session id"}, status = 400)
    user_id = get_user_from_session(session_id_str)
    if not user_id:
        return JsonResponse({"error": f"No user id for session id {session_id_str}"}, status = 400)

    user_id_str = str(user_id)

    try:
        game = Game.objects.get(gameId=gameId)

        player_info_response = prepare_game_data(game)
        player_data = player_info_response['players']

        if not player_data:
            return JsonResponse({"error": f"No players found for game {gameId}"}, status=404)

        claimed_player = None
        player_sessions = get_player_sessions_from_room(gameId)
        if player_sessions:
            for p, s in player_sessions.items():
                if s == session_id_str:
                    claimed_player = p

        if not claimed_player:
            # ok, no session, so maybe there was a dc
            for p in player_data:
                player_id_str = p['playerId']
                p_user_id_str = p['userId']

                if player_id_str not in player_sessions and p_user_id_str == user_id_str:
                    claimed_player = player_id_str

        claimed_player_list = [person for person in player_data if person['playerId'] == claimed_player]
        if len(claimed_player_list) > 0:
            player_info_response['player'] = claimed_player_list[0]

        if player_info_response.get('player',None) is not None:
            return JsonResponse(player_info_response, status = 200)
        return JsonResponse({"error": f"No available players found for game {gameId}"}, status = 404)
    except Game.DoesNotExist:
        return JsonResponse({"error": "Game not found"}, status = 404)

@api_view(['POST'])
def add_player(request, gameId):
    game = get_object_or_404(Game, gameId=gameId)
    body_data = request.data  # Use DRF's request parser

    user_id = body_data.get('userId')
    player_name = body_data.get('name')

    if not user_id:
        return JsonResponse({'error': 'userId parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user_account = Account.objects.get(userId=user_id)
    except Account.DoesNotExist:
        return JsonResponse({'error': 'Account not found for the given userId'}, status=status.HTTP_404_NOT_FOUND)

    if not player_name:
        player_count = game.players.count()  # Efficient player count
        player_name = f"Player {player_count + 1}"

    player = Player.objects.create(game=game, name=player_name, userId=user_account)

    player_announce = {
        'message': f"{player.name} added to the game",
        'type': 'add_player',
        'playerId': str(player.playerId),
        'name': player.name,
        'game_identifier': player.game_identifier,
    }
    GameConsumer.send_message_to_group(
        group_name=f"game_{game.gameId}",
        json_data=player_announce
    )
    # Fetch updated players list after player creation
    players = game.players.select_related('userId').all()
    player_data = [
        {
            'playerId': player.playerId,
            'name': player.name,
            'game_identifier': player.game_identifier,
            'userId': str(player.userId.userId),
        }
        for player in players
    ]

    response_data = {
        'message': player_announce['message'],
        'game': {
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
    return JsonResponse(response_data, status=status.HTTP_201_CREATED)
