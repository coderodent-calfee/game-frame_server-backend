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

def get_player_ids_in_game_with_user_id(game_id, user_id):
    try:
        # Assuming game_id is a string and matches the gameId field
        game = Game.objects.get(gameId=game_id)  # Use gameId (CharField)
        logger.info(f"found  game {game_id}")  # Debugging log

        userId = UUID(user_id)  # Convert to UUID
        logger.info(f"userId {userId}")  # Debugging log
        
        # Filter players by userId
        players = game.players.filter(userId__userId=userId)
        logger.info(f"found {len(players)} players {user_id}")  # Debugging log

        # Prepare player data
        player_data = [
            {
                'playerId': player.playerId,
                'name': player.name,
                'game_identifier': player.game_identifier,
                'userId': player.userId.userId
            }
            for player in players
        ]
        logger.info(f"Prepared player data {user_id}")  # Debugging log

        return player_data
    except Game.DoesNotExist:
        return []  # Handle the case where the game does not exist
    except Exception as e:
        logger.info(f"Error: {e}")
        return []


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
        players = game.players.all()  # Fetch related players
        player_data = [
            {
                'playerId': player.playerId, 
                'name': player.name, 
                'game_identifier': player.game_identifier,
                'userId': str(player.userId.userId), # debugging
#                **({'userId': player.userId.userId} if player.userId.userId == user_id else {})
            } for player in players
        ]
        if not player_data:
            logger.info(f"*** GAME_INFO No players found for game {gameId}")  # Debugging log
        # else:
        #     for p in player_data:
        #         logger.info(f"*** GAME_INFO players in game {str(p['playerId'])[:6]}")  # Debugging log


        game_info_response = {
            'game':{
                'gameId': game.gameId,
                'status': game.status,
                'players': player_data,
            }
        }
        game_info_response['socketSession'] = socketSession # debugging
        return JsonResponse(game_info_response, status = 200)
    
    except Game.DoesNotExist:
        return Response({"error": "Game not found"}, status=404)

@api_view(['GET'])
def get_games(request):
    games = Game.objects.all()
    data = games.values('gameId', 'status')  # Fetch specific fields
    return Response(data, status=status.HTTP_200_OK)

@api_view(['POST'])
def name_player(request, gameId):
    logger.info(f"*** NAME_PLAYER ")  # Debugging log
    game = get_object_or_404(Game, gameId=gameId)

    try:
        body_data = json.loads(request.body)
        user_id = body_data.get('userId', None)
        logger.info(f"*** NAME_PLAYER user_id passed to name_player is {user_id[:6] if user_id else None}")  # Debugging log
        player_name = body_data.get('name', None)
        logger.info(f"*** NAME_PLAYER name passed to name_player is {player_name}")  # Debugging log
        playerId = body_data.get('playerId', None)
        logger.info(f"*** NAME_PLAYER playerId passed to name_player is {playerId}")  # Debugging log
        if not playerId or not user_id or not player_name:
            logger.info(f"*** NAME_PLAYER playerId, userId and name parameters are required")  # Debugging log
            return JsonResponse({'error': 'playerId, userId and name parameters are required'}, status=status.HTTP_400_BAD_REQUEST)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    logger.info(f"*** NAME_PLAYER 1")  # Debugging log
    players = game.players.all()  # Fetch related players
    player_data = [
        {
            'playerId': player.playerId,
            'name': player.name,
            'game_identifier': player.game_identifier,
            'userId': player.userId.userId,
        } for player in players
    ]
    logger.info(f"*** NAME_PLAYER 2")  # Debugging log
    if not player_data:
        logger.info(f"*** NAME_PLAYER No players found for game {gameId}")  # Debugging log
        return Response({"error": f"No players found for game {gameId}"}, status=404)

    logger.info(f"*** NAME_PLAYER 3")  # Debugging log
    player_rename_response  = {}

    selected_player_list = [person for person in player_data if str(person['playerId']) == playerId]
    logger.info(f"*** NAME_PLAYER 4")  # Debugging log

    if len(selected_player_list) > 0:
        selected_player = selected_player_list[0]
        if str(selected_player.get('userId', None)) != user_id:
            return Response({"error": f"You cannot rename a player that is not your own {playerId}"}, status=401)
        player_rename_response ['player'] = selected_player

    if player_rename_response.get('player',None) is not None:
        logger.info(f"*** NAME_PLAYER 5")  # Debugging log
        try:
            logger.info(f"*** NAME_PLAYER get player {playerId}")  # Debugging log
            player = Player.objects.get(playerId=uuid.UUID(playerId))
            logger.info(f"*** NAME_PLAYER current player name {player.name}")  # Debugging log
            original_name = player.name 
            player.name = player_name # the actual renaming
            player.save()
            logger.info(f"*** NAME_PLAYER new player name {player.name}")  # Debugging log
            player_announce = {
                'message': f"{original_name} renamed to {player_name}",
                'type' : 'name_player',
                'playerId': str(player.playerId),
                'name': player.name,
                'game_identifier': player.game_identifier,
            }
            GameConsumer.send_message_to_group(
                group_name= f"game_{game.gameId}",
                json_data = player_announce
            )

        except Player.DoesNotExist:
            return JsonResponse({'error': 'Player not found'}, status=404)

    if player_rename_response.get('player',None) is not None:
        player_rename_response['player']['name'] = player_name
        players = game.players.all()  # Fetch related players
        player_data = [
            {
                'playerId': player.playerId,
                'name': player.name,
                'game_identifier': player.game_identifier,
                'userId': player.userId.userId,
            } for player in players
        ]
        player_rename_response['game'] = {
            'gameId' : game.gameId,
            'status' : game.status,
            'players': player_data,
        }
        return JsonResponse(player_rename_response, status = 200)
    logger.info(f"*** NAME_PLAYER No player {playerId} to rename for game {gameId}")  # Debugging log
    player_rename_response['error'] = f"No player {playerId} to rename for game {gameId}"
    return JsonResponse(player_rename_response, status = 404)


@api_view(['POST'])
def claim_player(request, gameId):

    body_data = json.loads(request.body)
    session_id = body_data.get('sessionId', None)

    if not session_id:
        return JsonResponse({"error": f"No session id"}, status = 400)
    user_id = get_user_from_session(session_id)

    if not user_id:
        return JsonResponse({"error": f"No user id for session id {session_id}"}, status = 400)

    try:
        game = Game.objects.get(gameId=gameId)
        players = game.players.all()  # Fetch related players
        # player_data contains UUID objects for player Id and user Id
        player_data = [
            {
                'playerId': player.playerId,
                'name': player.name,
                'game_identifier': player.game_identifier,
                'userId': player.userId.userId,
            } for player in players
        ]
        if not player_data:
            return Response({"error": f"No players found for game {gameId}"}, status=404)

        player_info_response = {
            'game' : {
                'gameId' : game.gameId,
                'status' : game.status,
                'players': player_data,
            },
        }

        claimed_player = None
        player_sessions = get_player_sessions_from_room(gameId)
        if player_sessions:
            for p, s in player_sessions.items():
                if str(s) == session_id:
                    claimed_player = p

        if not claimed_player:
            # ok, no session, so maybe there was a dc
            for p in player_data:
                player_id = str(p['playerId'])
                p_user_id = p['userId']
                if player_id not in player_sessions and p_user_id == user_id:
                    claimed_player = player_id

        claimed_player_list = [person for person in player_data if str(person['playerId']) == claimed_player]
        if len(claimed_player_list) > 0:
            player_info_response['player'] = claimed_player_list[0]

        if player_info_response.get('player',None) is not None:
            return JsonResponse(player_info_response, status = 200)
        return JsonResponse({"error": f"No available players found for game {gameId}"}, status = 404)

    except Game.DoesNotExist:
        return JsonResponse({"error": "Game not found"}, status = 404)

@api_view(['POST'])
def add_player(request, gameId):
    logger.info(f"*** ADD_PLAYER ")  # Debugging log
    game = get_object_or_404(Game, gameId=gameId)
    logger.info(f"*** ADD_PLAYER {gameId}")  # Debugging log

    try:
        body_data = json.loads(request.body)
        logger.info(f"*** ADD_PLAYER {body_data}")  # Debugging log
        user_id = body_data.get('userId', None)
        player_name = body_data.get('name', None)
        if not user_id:
            return JsonResponse({'error': 'userId parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    logger.info(f"*** ADD_PLAYER {str(user_id)[:6]} {player_name}")  # Debugging log

    try:
        user_account = Account.objects.get(userId=user_id)
    except Account.DoesNotExist:
        return JsonResponse({'error': 'Account not found for the given userId'}, status=status.HTTP_404_NOT_FOUND)

    logger.info(f"*** ADD_PLAYER {user_account}")  # Debugging log

    players = game.players.all()  # Fetch related players
    player_data = [
        {
            'playerId': player.playerId,
            'name': player.name,
            'game_identifier': player.game_identifier,
            'userId': str(player.userId.userId),
        } for player in players
    ]

    if not player_name:
        player_name = f"Player {1 + len(player_data)}"

    # Prepare player data
    player_init = {
        'game': game,
        'name': player_name,
        'userId': user_account,
    }

    # Create the player
    player = Player.objects.create(**player_init)

    player_announce = {
        'message': f"{player.name} added to the game",
        'type' : 'add_player', 
        'playerId': str(player.playerId),
        'name': player.name,
        'game_identifier': player.game_identifier,
    }
    logger.info(f"*** ADD_PLAYER announce {player_announce['message']}")  # Debugging log
    GameConsumer.send_message_to_group(
        group_name= f"game_{game.gameId}",
        json_data = player_announce
    )    
    players = game.players.all()  # Fetch related players
    player_data = [{
        'playerId': player.playerId,
        'name': player.name,
        'game_identifier': player.game_identifier,
        'userId': str(player.userId.userId),  # debugging
        #                **({'userId': player.userId.userId} if player.userId.userId == user_id else {}) # debugging
    } for player in players]
    
    response_data = {
        'message': f"{player.name} added to the game", 
        'game': {
            'gameId': game.gameId,
            'status': game.status,
            'players': player_data,
        }, 
        'player': {
            'playerId': player.playerId,
            'name': player.name,
            'game_identifier': player.game_identifier,
            'userId': str(player.userId.userId),  # debugging
            #                **({'userId': player.userId.userId} if player.userId.userId == user_id else {}) # debugging
        }, 
        'socketSession': socketSession # debugging
    }
    logger.info(f"*** ADD_PLAYER response {player_announce['message']}")  # Debugging log

    return JsonResponse(response_data, status=status.HTTP_201_CREATED)
