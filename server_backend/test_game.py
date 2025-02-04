
import django
django.setup()

import asyncio
import json
import os
import uuid
from collections import defaultdict

from django.test import Client, RequestFactory, TestCase
from channels.layers import get_channel_layer
from asgiref.testing import ApplicationCommunicator
from channels.testing import WebsocketCommunicator
from game.consumers import GameConsumer, socket_session_connect, get_user_from_session, get_socket_from_session, \
    get_session_players_from_user, socketSession, socket_session_player, reset_socket_session, socket_session_disconnect, \
    get_session_from_player, get_socket_from_player, get_player_sessions_from_room
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
        user = Account.objects.create(username=username, password=password, email=email)
        if not hasattr(self, 'user_ids') or self.user_ids is None:
            self.user_ids = []
        self.user_ids.append(user.userId)
        return user.userId

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
            data={'userId' : str(user_id)},
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())
        player = json_data.get('player', None)
        return player.get('playerId', None)

    def generate_session_id(self) -> str:
        array = os.urandom(16)  # Generate 16 random bytes
        return ''.join(f'{byte:02x}' for byte in array)  # Convert to a hexadecimal string

    def string_keys_values(self, in_data):
        if type(in_data) is dict:
            out = {}
            for k, v in in_data.items():
                key = self.string_keys_values(k)
                value = self.string_keys_values(v)
                out[key] = value
        elif type(in_data) is list:
            out = []
            for v in in_data:
                value = self.string_keys_values(v)
                out.append(value)
        else:
            out = str(in_data)
        return out


class GameViewTestCase(TestCase):
    def __init__(self, methodName: str = "runTest"):
        super().__init__(methodName)

    def setUp(self):
        reset_socket_session()

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

    def test_add_player_w_name(self):
        utility = Utility()

        new_game_id = utility.create_game()

        new_user = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        player_name = "Player Name"
        response = utility.client.post(
            f"/api/game/{new_game_id}/add/",
            data={
                'userId' : new_user,
                'name' : player_name
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)

        json_data = json.loads(response.getvalue())
        self.assertEqual(json_data.get('message', None), f"{player_name} added to the game")

        player = json_data.get('player', None)
        self.assertIsNotNone(player)
        self.assertEqual(player.get('name', None), player_name)
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
        session_id = 'session-12345'
        socket_id = 'socket-12345'

    #        print(f"socket_session:", json.dumps(utility.string_keys_values(socketSession, {}), indent=4))

        self.assertEqual(get_user_from_session(session_id), None)
        self.assertEqual(get_socket_from_session(session_id), None)
        self.assertEqual(get_session_players_from_user(user_id, game_id), {})

        # this is called when we arrive in the lobby
        socket_session_connect(session_id, user_id, socket_id, game_id)

        self.assertEqual(get_user_from_session(session_id), user_id)
        self.assertEqual(get_socket_from_session(session_id), socket_id)
        self.assertEqual(get_session_players_from_user(user_id, game_id), {})



    def test_socket_session_player(self):
        utility = Utility()

        game_id = utility.create_game()

        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )

        response = utility.client.post(
            f"/api/game/{game_id}/add/",
            data={'userId' : user_id},
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())

        player = json_data.get('player', None)

        player_id = player.get('playerId', None)
        session_id = 'session-12345'
        socket_id = 'socket-12345'

        socket_session_connect(session_id, user_id, socket_id, game_id)

        # this is called when the player is added to the game
        socket_session_player(player_id, socket_id, game_id)

#        print(f"socket_session:", json.dumps(utility.string_keys_values(socketSession, {}), indent=4))

        session_players_in_room = get_session_players_from_user(user_id, game_id)
        self.assertEqual(len(session_players_in_room), 1)
        self.assertEqual(session_players_in_room[session_id], player_id)


    def test_socket_session_disconnect(self):
        utility = Utility()
        game_id = utility.create_game()
    
        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        player_id_1 = utility.add_player(game_id,user_id)
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

#        print(f"socket_session:", json.dumps(utility.string_keys_values(socketSession, {}), indent=4))

        
        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

        session_players_in_room = get_session_players_from_user(user_id, game_id)
        self.assertEqual(len(session_players_in_room), 1)
        self.assertEqual(session_players_in_room[session_id_1], player_id_1)

 
        socket_session_disconnect(socket_id_1, game_id)

 
        self.assertEqual(get_user_from_session(session_id_1), None)
        self.assertEqual(get_socket_from_session(session_id_1), None)
        self.assertEqual(get_session_players_from_user(user_id, game_id), {})

    def test_socket_session_multiple_players(self):
        utility = Utility()
        game_id = utility.create_game()

        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        player_id_1 = utility.add_player(game_id,user_id)
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        player_id_2 = utility.add_player(game_id,user_id)
        session_id_2 = 'session-67890'
        socket_id_2 = 'socket-67890'

        # print(f"player_id_1:", player_id_1)
        # print(f"player_id_2:", player_id_2)

        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

        socket_session_connect(session_id_2, user_id, socket_id_2, game_id)
        socket_session_player(player_id_2, socket_id_2, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg, {}), indent=4, sort_keys=True)

        # print(f"socket_session:", jd(socketSession))
        # print(f"get_player_sessions_from_room({game_id}) {jd(get_player_sessions_from_room(game_id))}")
        # print(f"get_session_players_from_user({user_id}, {game_id})) {jd(get_session_players_from_user(user_id, game_id))}")

        player_sessions_from_room = get_player_sessions_from_room(game_id)
        self.assertEqual(len(player_sessions_from_room), 2)
        self.assertEqual(player_sessions_from_room[player_id_1], session_id_1)
        self.assertEqual(player_sessions_from_room[player_id_2], session_id_2)

        session_players_from_user = get_session_players_from_user(user_id, game_id)
        self.assertEqual(len(session_players_from_user), 2)
        self.assertEqual(session_players_from_user[session_id_1], player_id_1)
        self.assertEqual(session_players_from_user[session_id_2], player_id_2)

        # print(f"get_session_from_player({player_id_1}, {game_id})) {get_session_from_player(player_id_1, game_id)}")
        # print(f"get_socket_from_player({player_id_1}, {game_id})) {get_socket_from_player(player_id_1, game_id)}")

        self.assertEqual(get_session_from_player(player_id_1, game_id), session_id_1)
        self.assertEqual(get_socket_from_player(player_id_1, game_id), socket_id_1)
        self.assertEqual(get_session_from_player(player_id_2, game_id), session_id_2)
        self.assertEqual(get_socket_from_player(player_id_2, game_id), socket_id_2)


    def test_socket_session_players_disconnect(self):
        utility = Utility()
        game_id = utility.create_game()

        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        player_id_1 = utility.add_player(game_id,user_id)
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        player_id_2 = utility.add_player(game_id,user_id)
        session_id_2 = 'session-67890'
        socket_id_2 = 'socket-67890'


        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

        socket_session_connect(session_id_2, user_id, socket_id_2, game_id)
        socket_session_player(player_id_2, socket_id_2, game_id)

        socket_session_disconnect(socket_id_1, game_id)

        session_players_in_room = get_session_players_from_user(user_id, game_id)
        self.assertEqual(len(session_players_in_room), 1)
        self.assertEqual(session_players_in_room[session_id_2], player_id_2)

        self.assertEqual(get_session_from_player(player_id_1, game_id), None)
        self.assertEqual(get_socket_from_player(player_id_1, game_id), None)
        self.assertEqual(get_session_from_player(player_id_2, game_id), session_id_2)
        self.assertEqual(get_socket_from_player(player_id_2, game_id), socket_id_2)

        player_sessions_from_room = get_player_sessions_from_room(game_id)
        self.assertEqual(len(player_sessions_from_room), 1)
        self.assertEqual(player_sessions_from_room[player_id_2], session_id_2)

        session_players_from_user = get_session_players_from_user(user_id, game_id)
        self.assertEqual(len(session_players_from_user), 1)
        self.assertEqual(session_players_from_user[session_id_2], player_id_2)
        

    def test_socket_session_multiple_players_multiple_games(self):
        utility = Utility()
        game_id_1 = utility.create_game()
        game_id_2 = utility.create_game()
        
        user_id_1 = utility.create_account(
            'username_1',
            'password_1',
            'email_1@email.com'
        )

        user_id_2 = utility.create_account(
            'username_2',
            'password_2',
            'email_2@email2.com'
        )

        player_id_user1_game1 = utility.add_player(game_id_1,user_id_1)
        session_id_user1_game1 = 'session-user1_game1'
        socket_id_user1_game1 = 'socket-user1_game1'
        player_id_user2_game1 = utility.add_player(game_id_1,user_id_2)
        session_id_user2_game1 = 'session-user2_game1'
        socket_id_user2_game1 = 'socket-user2_game1'

        player_id_user1_game2 = utility.add_player(game_id_2,user_id_1)
        session_id_user1_game2  = 'session-user1_game2'
        socket_id_user1_game2 = 'socket-user1_game2'
        player_id_user2_game2 = utility.add_player(game_id_2,user_id_2)
        session_id_user2_game2 = 'session-user2_game2'
        socket_id_user2_game2 = 'socket-user2_game2'


        socket_session_connect(session_id_user1_game1, user_id_1, socket_id_user1_game1, game_id_1)
        socket_session_player(player_id_user1_game1, socket_id_user1_game1, game_id_1)

        socket_session_connect(session_id_user2_game1, user_id_2, socket_id_user2_game1, game_id_1)
        socket_session_player(player_id_user2_game1, socket_id_user2_game1, game_id_1)

        socket_session_connect(session_id_user1_game2, user_id_1, socket_id_user1_game2, game_id_2)
        socket_session_player(player_id_user1_game2, socket_id_user1_game2, game_id_2)

        socket_session_connect(session_id_user2_game2, user_id_2, socket_id_user2_game2, game_id_2)
        socket_session_player(player_id_user2_game2, socket_id_user2_game2, game_id_2)



        def jd(arg):
            return json.dumps(utility.string_keys_values(arg, {}), indent=4, sort_keys=True)

        player_sessions_from_room = get_player_sessions_from_room(game_id_1)
        self.assertEqual(len(player_sessions_from_room), 2)
        self.assertEqual(player_sessions_from_room[player_id_user1_game1], session_id_user1_game1)
        self.assertEqual(player_sessions_from_room[player_id_user2_game1], session_id_user2_game1)

        session_players_from_user1 = get_session_players_from_user(user_id_1, game_id_1)
        self.assertEqual(len(session_players_from_user1), 1)
        self.assertEqual(session_players_from_user1[session_id_user1_game1], player_id_user1_game1)

        session_players_from_user2 = get_session_players_from_user(user_id_2, game_id_1)
        self.assertEqual(len(session_players_from_user2), 1)
        self.assertEqual(session_players_from_user2[session_id_user2_game1], player_id_user2_game1)

        self.assertEqual(get_session_from_player(player_id_user1_game1, game_id_1), session_id_user1_game1)
        self.assertEqual(get_socket_from_player(player_id_user1_game1, game_id_1), socket_id_user1_game1)
        self.assertEqual(get_session_from_player(player_id_user2_game1, game_id_1), session_id_user2_game1)
        self.assertEqual(get_socket_from_player(player_id_user2_game1, game_id_1), socket_id_user2_game1)


        player_sessions_from_room = get_player_sessions_from_room(game_id_2)
        self.assertEqual(len(player_sessions_from_room), 2)
        self.assertEqual(player_sessions_from_room[player_id_user1_game2], session_id_user1_game2)
        self.assertEqual(player_sessions_from_room[player_id_user2_game2], session_id_user2_game2)
    
        session_players_from_user1 = get_session_players_from_user(user_id_1, game_id_2)
        self.assertEqual(len(session_players_from_user1), 1)
        self.assertEqual(session_players_from_user1[session_id_user1_game2], player_id_user1_game2)
    
        session_players_from_user2 = get_session_players_from_user(user_id_2, game_id_2)
        self.assertEqual(len(session_players_from_user2), 1)
        self.assertEqual(session_players_from_user2[session_id_user2_game2], player_id_user2_game2)
    
        self.assertEqual(get_session_from_player(player_id_user1_game2, game_id_2), session_id_user1_game2)
        self.assertEqual(get_socket_from_player(player_id_user1_game2, game_id_2), socket_id_user1_game2)
        self.assertEqual(get_session_from_player(player_id_user2_game2, game_id_2), session_id_user2_game2)
        self.assertEqual(get_socket_from_player(player_id_user2_game2, game_id_2), socket_id_user2_game2)

        # print(f"player_id_user1_game1:", player_id_user1_game1)
        # print(f"player_id_user2_game1:", player_id_user2_game1)
        # print(f"player_id_user1_game2:", player_id_user1_game2)
        # print(f"player_id_user2_game2:", player_id_user2_game2)
        # 
        # print(f"get_player_sessions_from_room({game_id_1}) {jd(get_player_sessions_from_room(game_id_1))}")
        # print(f"get_player_sessions_from_room({game_id_2}) {jd(get_player_sessions_from_room(game_id_2))}")
        # 
        # print(f"get_session_players_from_user({user_id_1}, {game_id_1}) {jd(get_session_players_from_user(user_id_1, game_id_1))}")
        # print(f"get_session_players_from_user({user_id_1}, {game_id_2}) {jd(get_session_players_from_user(user_id_1, game_id_2))}")
        # print(f"get_session_players_from_user({user_id_2}, {game_id_1}) {jd(get_session_players_from_user(user_id_2, game_id_1))}")
        # print(f"get_session_players_from_user({user_id_2}, {game_id_2}) {jd(get_session_players_from_user(user_id_2, game_id_2))}")

        socket_session_disconnect(socket_id_user1_game1, game_id_1)
        socket_session_disconnect(socket_id_user1_game2, game_id_2)
#        print(f"socket_session:", jd(socketSession))

        # print(f"get_player_sessions_from_room({game_id_1}) {jd(get_player_sessions_from_room(game_id_1))}")
        # print(f"get_player_sessions_from_room({game_id_2}) {jd(get_player_sessions_from_room(game_id_2))}")
        # 
        # print(f"get_session_players_from_user({user_id_1}, {game_id_1}) {jd(get_session_players_from_user(user_id_1, game_id_1))}")
        # print(f"get_session_players_from_user({user_id_1}, {game_id_2}) {jd(get_session_players_from_user(user_id_1, game_id_2))}")
        # print(f"get_session_players_from_user({user_id_2}, {game_id_1}) {jd(get_session_players_from_user(user_id_2, game_id_1))}")
        # print(f"get_session_players_from_user({user_id_2}, {game_id_2}) {jd(get_session_players_from_user(user_id_2, game_id_2))}")

        player_sessions_from_room = get_player_sessions_from_room(game_id_1)
        self.assertEqual(len(player_sessions_from_room), 1)
        self.assertEqual(player_sessions_from_room[player_id_user2_game1], session_id_user2_game1)

        session_players_from_user1 = get_session_players_from_user(user_id_1, game_id_1)
        self.assertEqual(len(session_players_from_user1), 0)

        session_players_from_user2 = get_session_players_from_user(user_id_2, game_id_1)
        self.assertEqual(len(session_players_from_user2), 1)
        self.assertEqual(session_players_from_user2[session_id_user2_game1], player_id_user2_game1)

        self.assertEqual(get_session_from_player(player_id_user1_game1, game_id_1), None)
        self.assertEqual(get_socket_from_player(player_id_user1_game1, game_id_1), None)
        self.assertEqual(get_session_from_player(player_id_user2_game1, game_id_1), session_id_user2_game1)
        self.assertEqual(get_socket_from_player(player_id_user2_game1, game_id_1), socket_id_user2_game1)


        player_sessions_from_room = get_player_sessions_from_room(game_id_2)
        self.assertEqual(len(player_sessions_from_room), 1)
        self.assertEqual(player_sessions_from_room[player_id_user2_game2], session_id_user2_game2)

        session_players_from_user1 = get_session_players_from_user(user_id_1, game_id_2)
        self.assertEqual(len(session_players_from_user1), 0)

        session_players_from_user2 = get_session_players_from_user(user_id_2, game_id_2)
        self.assertEqual(len(session_players_from_user2), 1)
        self.assertEqual(session_players_from_user2[session_id_user2_game2], player_id_user2_game2)

        self.assertEqual(get_session_from_player(player_id_user1_game2, game_id_2), None)
        self.assertEqual(get_socket_from_player(player_id_user1_game2, game_id_2), None)
        self.assertEqual(get_session_from_player(player_id_user2_game2, game_id_2), session_id_user2_game2)
        self.assertEqual(get_socket_from_player(player_id_user2_game2, game_id_2), socket_id_user2_game2)

    def test_claim_session_match(self):
        utility = Utility()
        game_id = utility.create_game()

        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        player_id_1 = utility.add_player(game_id,user_id)
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

#        socket_session_disconnect(socket_id_1, game_id)

        # session_id_1b = 'session-12345b'
        # socket_id_1b = 'socket-12345b'
        # socket_session_connect(session_id_1b, user_id, socket_id_1b, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg), indent=4, sort_keys=True)

        response = utility.client.post(
            f"/api/game/{game_id}/claim/",
            data={'sessionId' : session_id_1},
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())
        #        print(f"json_data:", jd(json_data))

        self.assertEqual(json_data['player']['playerId'], player_id_1)
        self.assertEqual(response.status_code, 200)

    def test_claim_user_match(self):
        utility = Utility()
        game_id = utility.create_game()

        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        player_id_1 = utility.add_player(game_id, user_id)
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

        socket_session_disconnect(socket_id_1, game_id)

        session_id_1b = 'session-12345b'
        socket_id_1b = 'socket-12345b'
        socket_session_connect(session_id_1b, user_id, socket_id_1b, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg), indent=4, sort_keys=True)

        response = utility.client.post(
            f"/api/game/{game_id}/claim/",
            data={'sessionId': session_id_1b},
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())

        self.assertEqual(json_data['player']['playerId'], player_id_1)
        self.assertEqual(response.status_code, 200)

    def test_player_claim_no_game_404(self):
        game_id = '567890'
        utility = Utility()

        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg), indent=4, sort_keys=True)

        response = utility.client.post(
            f"/api/game/{game_id}/claim/",
            data={'sessionId': session_id_1},
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())
        self.assertEqual(json_data['error'], 'Game not found')
        self.assertEqual(response.status_code, 404)

    def test_claim_no_players(self):
        utility = Utility()
        game_id = utility.create_game()

        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg), indent=4, sort_keys=True)

        response = utility.client.post(
            f"/api/game/{game_id}/claim/",
            data={'sessionId': session_id_1},
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())
        self.assertEqual(json_data['error'], f"No players found for game {game_id}")
        self.assertEqual(response.status_code, 404)
        
    def test_player_claim_no_session_id(self):
        utility = Utility()
        game_id = utility.create_game()

        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        player_id_1 = utility.add_player(game_id,user_id)
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

        socket_session_disconnect(socket_id_1, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg, {}), indent=4, sort_keys=True)

        response = utility.client.post(
            f"/api/game/{game_id}/claim/",
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())

        self.assertEqual(json_data['error'], f"No session id")
        self.assertEqual(response.status_code, 400)

    def test_player_claim_no_user_id(self):
        utility = Utility()
        game_id = utility.create_game()

        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        player_id_1 = utility.add_player(game_id, user_id)
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

        socket_session_disconnect(socket_id_1, game_id)

        # session_id_1b = 'session-12345b'
        # socket_id_1b = 'socket-12345b'
        # socket_session_connect(session_id_1b, user_id, socket_id_1b, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg), indent=4, sort_keys=True)

        response = utility.client.post(
            f"/api/game/{game_id}/claim/",
            data={'sessionId': session_id_1},
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())
#        print(f"json_data:", jd(json_data))
        self.assertEqual(json_data['error'], f"No user id for session id {session_id_1}")
        self.assertEqual(response.status_code, 400)

    def test_player_claim_no_disconnected_players(self):
        utility = Utility()
        game_id = utility.create_game()

        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        player_id_1 = utility.add_player(game_id, user_id)
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

        #        socket_session_disconnect(socket_id_1, game_id)

        session_id_1b = 'session-12345b'
        socket_id_1b = 'socket-12345b'
        socket_session_connect(session_id_1b, user_id, socket_id_1b, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg), indent=4, sort_keys=True)

        response = utility.client.post(
            f"/api/game/{game_id}/claim/",
            data={'sessionId': session_id_1b},
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())

        self.assertEqual(json_data['error'], f"No available players found for game {game_id}")
        self.assertEqual(response.status_code, 404)

    def test_player_claim_no_user_dc_players(self):
        utility = Utility()
        game_id = utility.create_game()
        user_id_1 = utility.create_account(
            'username_1',
            'password_1',
            'email_1@email.com'
        )

        user_id_2 = utility.create_account(
            'username_2',
            'password_2',
            'email_2@email2.com'
        )

        player_id_1 = utility.add_player(game_id,user_id_1)
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        socket_session_connect(session_id_1, user_id_1, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

        socket_session_disconnect(socket_id_1, game_id)

        session_id_2 = 'session-user-2'
        socket_id_2 = 'socket-user-2'
        socket_session_connect(session_id_2, user_id_2, socket_id_2, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg), indent=4, sort_keys=True)

        response = utility.client.post(
            f"/api/game/{game_id}/claim/",
            data={'sessionId' : session_id_2},
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())
        #print(f"json_data:", jd(json_data))

        self.assertEqual(json_data['error'], f"No available players found for game {game_id}")
        self.assertEqual(response.status_code, 404)

    def test_rename_player(self):
        utility = Utility()
        game_id = utility.create_game()

        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        player_id_1 = utility.add_player(game_id,user_id)
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg), indent=4, sort_keys=True)

        player_name = "Player Name"

        response = utility.client.post(
            f"/api/game/{game_id}/name/",
            data={
                'userId' : user_id,
                'playerId': player_id_1,
                'name': player_name,
            },
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())
#        print(f"json_data:", jd(json_data))

        self.assertEqual(json_data['player']['playerId'], player_id_1)
        self.assertEqual(json_data['player']['name'], player_name)
        self.assertEqual(response.status_code, 200)

    def test_rename_no_player(self):
        utility = Utility()
        game_id = utility.create_game()

        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        player_id_1 = utility.add_player(game_id, user_id)
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg), indent=4, sort_keys=True)

        player_name = "Player Name"

        response = utility.client.post(
            f"/api/game/{game_id}/name/",
            data={
                'userId': user_id,
                'name': player_name,
            },
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())

        self.assertEqual(json_data['error'], f"playerId, userId and name parameters are required")
        self.assertEqual(response.status_code, 400)


    def test_rename_no_user_id(self):
        utility = Utility()
        game_id = utility.create_game()

        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        player_id_1 = utility.add_player(game_id, user_id)
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg), indent=4, sort_keys=True)

        player_name = "Player Name"

        response = utility.client.post(
            f"/api/game/{game_id}/name/",
            data={
                'playerId': player_id_1,
                'name': player_name,
            },
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())

        self.assertEqual(json_data['error'], f"playerId, userId and name parameters are required")
        self.assertEqual(response.status_code, 400)


    def test_rename_no_name(self):
        utility = Utility()
        game_id = utility.create_game()

        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        player_id_1 = utility.add_player(game_id, user_id)
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg), indent=4, sort_keys=True)

        player_name = "Player Name"

        response = utility.client.post(
            f"/api/game/{game_id}/name/",
            data={
                'userId': user_id,
                'playerId': player_id_1,
            },
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())

        self.assertEqual(json_data['error'], f"playerId, userId and name parameters are required")
        self.assertEqual(response.status_code, 400)

    def test_rename_no_game(self):
        utility = Utility()
        game_id = utility.create_game()
        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        player_id_1 = utility.add_player(game_id, user_id)
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg), indent=4, sort_keys=True)

        player_name = "Player Name"
        game_id = '567890'

        response = utility.client.post(
            f"/api/game/{game_id}/name/",
            data={
                'userId': user_id,
                'name': player_name,
                'playerId': player_id_1,
            },
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())
        self.assertEqual(response.status_code, 404)
        self.assertEqual(json_data['detail'], f"No Game matches the given query.")

    def test_rename_not_my_player(self):

        utility = Utility()
        game_id = utility.create_game()

        user_id_1 = utility.create_account(
            'username_1',
            'password_1',
            'email_1@email.com'
        )

        user_id_2 = utility.create_account(
            'username_2',
            'password_2',
            'email_2@email2.com'
        )
        player_id_1 = utility.add_player(game_id,user_id_1)
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        player_id_2 = utility.add_player(game_id,user_id_2)
        session_id_2 = 'session-67890'
        socket_id_2 = 'socket-67890'

        socket_session_connect(session_id_1, user_id_1, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

        socket_session_connect(session_id_2, user_id_2, socket_id_2, game_id)
        socket_session_player(player_id_2, socket_id_2, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg), indent=4, sort_keys=True)

        player_name = "Player Name"

        response = utility.client.post(
            f"/api/game/{game_id}/name/",
            data={
                'userId': user_id_2,
                'name': player_name,
                'playerId': player_id_1,
            },
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())
        # print(f"json_data:", jd(json_data))

        self.assertEqual(json_data['error'], f"You cannot rename a player that is not your own. player:{player_id_1}")
        self.assertEqual(response.status_code, 401)


    def test_rename_no_players_in_game(self):
        utility = Utility()
        game_id = utility.create_game()
        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )

        player_id_1 = "not in game"
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg), indent=4, sort_keys=True)

        player_name = "Player Name"

        response = utility.client.post(
            f"/api/game/{game_id}/name/",
            data={
                'userId': user_id,
                'name': player_name,
                'playerId': player_id_1,
            },
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())
        # print(f"json_data:", jd(json_data))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(json_data['error'], f"No players found for game {game_id}")


    def test_rename_player_not_found(self):
        utility = Utility()
        game_id = utility.create_game()

        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        player_id_1 = utility.add_player(game_id,user_id)
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg), indent=4, sort_keys=True)

        player_name = "Player Name"

        player_id_bad = str(uuid.uuid4())

        response = utility.client.post(
            f"/api/game/{game_id}/name/",
            data={
                'userId' : user_id,
                'playerId': player_id_bad,
                'name': player_name,
            },
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())
        # print(f"json_data:", jd(json_data))
        self.assertEqual(json_data['error'], f"No player {player_id_bad} to rename for game {game_id}")

        self.assertEqual(response.status_code, 404)

    def test_rename_bad_player_id(self):
        utility = Utility()
        game_id = utility.create_game()

        user_id = utility.create_account(
            'username',
            'password',
            'email@email.com'
        )
        player_id_1 = utility.add_player(game_id,user_id)
        session_id_1 = 'session-12345'
        socket_id_1 = 'socket-12345'

        socket_session_connect(session_id_1, user_id, socket_id_1, game_id)
        socket_session_player(player_id_1, socket_id_1, game_id)

        def jd(arg):
            return json.dumps(utility.string_keys_values(arg), indent=4, sort_keys=True)

        player_name = "Player Name"

        player_id_bad = "not in game"

        response = utility.client.post(
            f"/api/game/{game_id}/name/",
            data={
                'userId' : user_id,
                'playerId': player_id_bad,
                'name': player_name,
            },
            content_type="application/json"
        )
        json_data = json.loads(response.getvalue())
        # print(f"json_data:", jd(json_data))
        self.assertEqual(json_data['error'], f"Invalid player id {player_id_bad} to rename for game {game_id}")

        self.assertEqual(response.status_code, 400)
