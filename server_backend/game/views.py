# game/views.py
import json

from .serializers import GameSerializer, PlayerSerializer
from django.http import JsonResponse

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Game, Player
from accounts.models import Account
from rest_framework import status
from uuid import UUID
from .consumers import socketSession, get_player_sessions_from_room, get_sessions_from_user, get_user_from_session
import logging

logger = logging.getLogger(__name__)

def loggering(message):
    print(message)
    logger.info(message)  # Debugging log
    

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
def crumpet(request, gameId):
    logger.info(f"*** CLAIM_PLAYER ")  # Debugging log
    session_id = request.query_params.get('sessionId')
    user_id = request.query_params.get('userId')
    if not user_id:
        user_id = get_user_from_session(session_id)

    try:
        game = Game.objects.get(gameId=gameId)
        players = game.players.all()  # Fetch related players
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
        # if we were given the session_id it means we really want the player we were/are attached to if possible
        if session_id is not None:
            player_sessions = get_player_sessions_from_room(gameId)
            logger.info(f"*** CLAIM_PLAYER get_player_sessions_from_room {player_sessions}")  # Debugging log
            if player_sessions:
                for p, s in player_sessions.items():
                    # output[player_id] = session_id  
                    logger.info(f"*** CLAIM_PLAYER players in game {p[:6]} = {s}")  # Debugging log
                    if s == session_id:
                        claimed_player = p
                        logger.info(f"*** CLAIM_PLAYER player session {session_id[:6]} claims {claimed_player[:6]}")  # Debugging log
            logger.info(f"*** CLAIM_PLAYER get_player_sessions_from_room")  # Debugging log
            if not claimed_player:
                disconnected_players = []
                users_players = []
                # ok, no session, so maybe there was a dc
                for p in player_data:
                    player_id = str(p['playerId'])
                    player_user_id = str(p['userId'])
                    if player_id not in player_sessions:
                        disconnected_players.append(player_id)
                    if player_user_id == user_id:
                        users_players.append(player_id)
                    if player_id not in player_sessions and player_user_id == user_id:
                        claimed_player = player_id
                        logger.info(f"*** CLAIM_PLAYER player without session {str(user_id)[:6]} claims {claimed_player[:6]}")  # Debugging log

            logger.info(f"*** CLAIM_PLAYER claimed_player {claimed_player}")  # Debugging log
            for person in player_data:
                logger.info(f"*** CLAIM_PLAYER person {person}")  # Debugging log
                logger.info(f"*** CLAIM_PLAYER person['playerId'] {person['playerId']}")  # Debugging log
                logger.info(f"*** CLAIM_PLAYER person['playerId'] == claimed_player {str(person['playerId']) == claimed_player}")  # Debugging log

            claimed_player_list = [person for person in player_data if str(person['playerId']) == claimed_player]
            if len(claimed_player_list) > 0:
                player_info_response['player'] = claimed_player_list[0]

        logger.info(f"*** CLAIM_PLAYER player_info_response {player_info_response}")  # Debugging log
        logger.info(f"*** CLAIM_PLAYER player_info_response['player'] {player_info_response['player']}")  # Debugging log

        player_info_response['socketSession'] = socketSession # debugging

        logger.info(f"*** CLAIM_PLAYER len(player_info_response['player']) {len(player_info_response['player'])}")  # Debugging log

        if player_info_response['player'] is not None:
            return JsonResponse(player_info_response, status = 200)
        player_info_response['error'] = f"No available players found for game {gameId}"
        return JsonResponse(player_info_response, status = 404)

    except Game.DoesNotExist:
        return JsonResponse({"error": "Game not found"}, status = 404)


# add player just adds a new player and hands it back
@api_view(['POST'])
def add_player(request, gameId):
    game = get_object_or_404(Game, gameId=gameId)

    try:
        body_data = json.loads(request.body)
        user_id = body_data.get('userId', None)
        player_name = body_data.get('name', None)
        if not user_id:
            return JsonResponse({'error': 'userId parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    try:
        user_account = Account.objects.get(userId=user_id)
    except Account.DoesNotExist:
        return JsonResponse({'error': 'Account not found for the given userId'}, status=status.HTTP_404_NOT_FOUND)

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

    players = game.players.all()  # Fetch related players
    player_data = [{
        'playerId': player.playerId,
        'name': player.name,
        'game_identifier': player.game_identifier,
        'userId': str(player.userId.userId),  # debugging
        #                **({'userId': player.userId.userId} if player.userId.userId == user_id else {})
    } for player in players]

    # Prepare the response
    response_data = {'message': f"{player.name} added to the game", 'game': {
        'gameId': game.gameId,
        'status': game.status,
        'players': player_data,
    }, 'player': {
        'playerId': player.playerId,
        'name': player.name,
        'game_identifier': player.game_identifier,
        'userId': str(player.userId.userId),  # debugging
        #                **({'userId': player.userId.userId} if player.userId.userId == user_id else {})
    }, 'socketSession': socketSession}

    return JsonResponse(response_data, status=status.HTTP_201_CREATED)
