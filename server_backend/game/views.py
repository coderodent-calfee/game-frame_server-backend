# game/views.py
from .serializers import GameSerializer, PlayerSerializer
from django.http import JsonResponse

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Game, Player
from accounts.models import Account
from rest_framework import status
from uuid import UUID
from .consumers import get_player_sessions_from_room, get_sessions_from_user, get_user_from_session
import logging

logger = logging.getLogger(__name__)

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

@api_view(['GET'])
def get_game_info(request, gameId):
    user_id = request.query_params.get('userId')
    logger.info(f"*** GAME_INFO user_id passed to get_game_info is {user_id}")  # Debugging log
    session_id = request.query_params.get('sessionId')
    logger.info(f"*** GAME_INFO session_id passed to get_game_info is {session_id}")  # Debugging log
    try:

        game = Game.objects.get(gameId=gameId)
        players = game.players.all()  # Fetch related players
        player_data = [
            {
                'playerId': player.playerId, 
                'name': player.name, 
                'game_identifier': player.game_identifier,
                **({'userId': player.userId.userId} if player.userId.userId == user_id else {})
            } for player in players
        ]

        if not player_data:
            logger.info(f"*** GAME_INFO No players found for game {gameId}")  # Debugging log

        game_info_response = {
            'game':{
                'gameId': game.gameId,
                'status': game.status,
                'players': player_data,
            }
        }

        # if we were given the session_id it means we really want the player we are
        # attached to:
        # possible
        if session_id is not None:
            user_id = get_user_from_session(session_id)
            logger.info(f"*** GAME_INFO user_id = get_user_from_session(session_id) {user_id}")
            user_sessions = get_sessions_from_user(user_id, gameId)
            logger.info(f"*** GAME_INFO user_sessions = get_sessions_from_user {'\n\t'.join(user_sessions)}")
            player_sessions = get_player_sessions_from_room(gameId)
            logger.info(f"*** GAME_INFO player_sessions = get_player_sessions_from_room {'\n\t'.join(player_sessions)}")
            session_id_player = None
            for user_session_id, user_player_id in user_sessions.items():
                player_id_session = player_sessions.get(user_player_id)
                if user_session_id == player_id_session:
                    session_id_player = user_player_id
                    break
            # session missing a player
            if session_id_player is None:
                for player in player_data:
                    if player['playerId'] not in player_sessions:
                        # player missing a sessionId; session missing a player
                        # user must have disconnected
                        session_id_player = player['playerId']
                        break
            logger.info(f"*** GAME_INFO session_id {session_id} matched to player_id {session_id_player}")
            game_info_response['player'] = [person for person in player_data if person["playerId"] == session_id_player]
        elif user_id is not None:
            game_info_response['player'] = get_player_ids_in_game_with_user_id(gameId, user_id)
            
        return JsonResponse(game_info_response, status = 200)
    
    except Game.DoesNotExist:
        return Response({"error": "Game not found"}, status=404)

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

@api_view(['POST'])
def add_player(request, gameId):
    logger.info(f"add_player {gameId}")  # Debugging log

    # Retrieve the game object
    game = get_object_or_404(Game, gameId=gameId)

    logger.info(f"add_player game {game.gameId}")  # Debugging log
    # Extract userId from query parameters
    user_id = request.query_params.get('userId')
    logger.info(f"add_player user_id {user_id}")  # Debugging log

    if not user_id:
        return Response({'error': 'userId parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

    logger.info(f"Get the Account object related to the userId")  # Debugging log
    # Get the Account object related to the userId
    try:
        user_account = Account.objects.get(userId=user_id)
    except Account.DoesNotExist:
        return Response({'error': 'Account not found for the given userId'}, status=status.HTTP_404_NOT_FOUND)

    logger.info(f"# Prepare player data")  # Debugging log
    # Prepare player data
    player_data = {
        'game': game,
        'name': request.data.get('name', str(user_account)),  # Assume name is passed in the request body
        'userId': user_account,
    }
    logger.info(f"player data : {player_data}")  # Debugging log

    # Create the player
    player = Player.objects.create(**player_data)
    logger.info(f"# Created the player!!")  # Debugging log


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
    logger.info(f"response_data : {response_data}")  # Debugging log

    # Return a response indicating success
    return Response(response_data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def get_games(request):
    if request.method == 'GET':
        accounts = Game.objects.all()
        data = accounts.values('gameId', 'status')  # Fetch specific fields
        return Response(data, status=status.HTTP_200_OK)