import asyncio
import json
import os
import uuid

from django.test import Client, RequestFactory, TestCase
from channels.layers import get_channel_layer
from asgiref.testing import ApplicationCommunicator
from channels.testing import WebsocketCommunicator
from game.consumers import GameConsumer, socket_session_connect, get_user_from_session, get_socket_from_session, \
    get_sessions_from_user
from channels.routing import  URLRouter
from game.models import Game
from accounts.models import Account
from django.urls import path

from game.routing import websocket_urlpatterns


class Utility():

    def __init__(self):
        self.factory = RequestFactory()
        self.client = Client()
        self.game_ids = None
        self.user_ids = None

    def create_game_post(self):
        jsonResponse = self.client.post('/api/game/new/')
        new_game_response = json.loads(jsonResponse.getvalue())
        return new_game_response

    def create_account(self, username, password, email):
        user_ids = self.user_ids if self.user_ids else []
        Account.objects.create()
        users = Account.objects.all()
        for user in users:
            if user.userId not in user_ids:
                new_user_id = user.userId
                user_ids.append(user.userId)
        self.user_ids = user_ids
        return new_user_id


    def create_game(self):
        game_ids = self.game_ids if self.game_ids else []
        Game.objects.create()
        games = Game.objects.all()
        for game in games:
            if game.gameId not in game_ids:
                new_game_id = game.gameId
                game_ids.append(game.gameId)
        self.game_ids = game_ids
        return new_game_id

    def list_games(self):
        response = self.client.get('/api/game/')
        response.render()
        return json.loads(response.getvalue())

    def get_game_info(self, game_id):
        jsonResponse = self.client.get(f"/api/game/{game_id}/info/")
        new_game_response = json.loads(jsonResponse.getvalue())
        return new_game_response

    def add_player(self, game_id, user_id ):
        response = self.client.post(
            f"/api/game/{game_id}/add/",
            data={'userId' : user_id},
            content_type="application/json"
        )
        return json.loads(response.getvalue())

    def generate_session_id(self) -> str:
        array = os.urandom(16)  # Generate 16 random bytes
        return ''.join(f'{byte:02x}' for byte in array)  # Convert to a hexadecimal string



class GameViewTestCase(TestCase):
    def __init__(self, methodName: str = "runTest"):
        super().__init__(methodName)

    def setUp(self):
        pass

    def test_create_game(self):
        utility = Utility()
        game_list = utility.list_games()
        self.assertEqual(game_list, [])

        new_game_response = utility.create_game_post()

        self.assertIsNotNone(new_game_response)
        self.assertIsNotNone(new_game_response['game'])
        self.assertIsNotNone(new_game_response['game']['gameId'])
        self.assertEqual(len(new_game_response['game']['gameId']), 6)

        game_list = utility.list_games()
        expected = [{'status': 'waiting'}]
        expected[0]['gameId'] = new_game_response['game']['gameId']

        self.assertEqual(game_list, expected)

        next_game = utility.create_game_post()
        next_game_expected = {
            'status' : 'waiting',
            'gameId' : next_game['game']['gameId']
        }
        expected.append(next_game_expected)
        game_list = utility.list_games()
        self.assertEqual(game_list, expected)

    def test_get_game_info(self):
        utility = Utility()
        new_game_response = utility.create_game_post()
        game_id = new_game_response['game']['gameId']
        body = utility.get_game_info(game_id)
        self.assertEqual(body['game']['gameId'], game_id)

    def test_add_player_no_game_404(self):
        utility = Utility()
        game_id = '567890'
        response = utility.client.post(
            f"/api/game/{game_id}/add/",
            data={'userId' : '1234'},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)


    def test_add_player_no_user_id_400(self):
        utility = Utility()
        new_game_id = utility.create_game()

        response = utility.client.post(
            f"/api/game/{new_game_id}/add/",
            data={'hello' : '1234'},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_add_player_no_user_acct(self):
        utility = Utility()

        new_game_id = utility.create_game()

        new_user = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )

        response = utility.client.post(
            f"/api/game/{new_game_id}/add/",
            data={'userId' : '937ea451-3db3-4af2-9d93-ee8d4cae4b2c',
                  'name' : 'player name'},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)


    def test_add_player(self):
        utility = Utility()

        new_game_id = utility.create_game()

        new_user = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )

        response = utility.client.post(
            f"/api/game/{new_game_id}/add/",
            data={'userId' : new_user},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)

        json_data = json.loads(response.getvalue())
        self.assertEqual(json_data.get('message', None), 'Player 1 added to the game')

        player = json_data.get('player', None)
        self.assertIsNotNone(player)
        self.assertEqual(player.get('name', None), 'Player 1')
        self.assertEqual(player.get('game_identifier', None), new_game_id)
        self.assertEqual(player.get('userId', None), str(new_user))

        player_id = player.get('playerId', None)
        game = json_data.get('game', None)
        self.assertEqual(game.get('gameId', None), new_game_id)
        self.assertEqual(len(game.get('players', [])), 1)

        game_player = game.get('players')[0]
        self.assertEqual(game_player.get('playerId', None), player_id)
        self.assertEqual(game_player, player)

    def test_socket_session_connect(self):
        utility = Utility()

        game_id = utility.create_game()

        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        
        response = utility.add_player(game_id, user_id)
        session_id = 'session-12345'
        socket_id = 'socket-12345'
        
        test_user_id = get_user_from_session(session_id)
        self.assertEqual(test_user_id, None)
        test_socket_id = get_socket_from_session(session_id)
        self.assertEqual(test_socket_id, None)
        sessions_in_room = get_sessions_from_user(user_id, game_id)
        self.assertEqual(sessions_in_room, None)
        
        # this is called when we arrive in the lobby
        socket_session_connect(session_id, user_id, socket_id, game_id)

        test_user_id = get_user_from_session(session_id)
        self.assertEqual(test_user_id, user_id)
        test_socket_id = get_socket_from_session(session_id)
        self.assertEqual(test_socket_id, socket_id)

        sessions_in_room = get_sessions_from_user(user_id, game_id)
        self.assertEqual(len(sessions_in_room), 1)
        self.assertEqual(sessions_in_room[0], session_id)
        
        
