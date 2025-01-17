
import json
from django.test import Client, RequestFactory, TestCase

from game.models import Game
from accounts.models import Account

class Utilities():
    def __init__(self, name):
        self.name = name

class GameViewTestCase(TestCase):
    def __init__(self, methodName: str = "runTest"):
        super().__init__(methodName)
        self.game_ids = None
        self.user_ids = None

    def setUp(self):
        self.factory = RequestFactory()
        self.client = Client()

    def create_game_post(self):
        jsonResponse = self.client.post('/api/game/new/')
        self.assertEqual(jsonResponse.status_code, 201)
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
        self.assertEqual(response.status_code, 200)
        response.render()
        return json.loads(response.getvalue())

    def get_game_info(self, game_id):
        jsonResponse = self.client.get(f"/api/game/{game_id}/info/")
        self.assertEqual(jsonResponse.status_code, 200)
        new_game_response = json.loads(jsonResponse.getvalue())
        return new_game_response

    def add_player(self, game_id, query_params):
        jsonResponse = self.client.post(f"/api/game/{game_id}/add/", query_params)
        return json.loads(jsonResponse.getvalue())

    def test_create_game(self):
        body = self.list_games()
        self.assertEqual(body, [])

        new_game_response = self.create_game_post()

        self.assertIsNotNone(new_game_response)
        self.assertIsNotNone(new_game_response['game'])
        self.assertIsNotNone(new_game_response['game']['gameId'])
        self.assertEqual(len(new_game_response['game']['gameId']), 6)

        body = self.list_games()
        expected = [{'status': 'waiting'}]
        expected[0]['gameId'] = new_game_response['game']['gameId']

        self.assertEqual(body, expected)

        next_game = self.create_game_post()
        next_game_expected = {
            'status' : 'waiting',
            'gameId' : next_game['game']['gameId']
        }
        expected.append(next_game_expected)
        body = self.list_games()
        self.assertEqual(body, expected)

    def test_get_game_info(self):
        new_game_response = self.create_game_post()
        game_id = new_game_response['game']['gameId']
        body = self.get_game_info(game_id)
        self.assertEqual(body['game']['gameId'], game_id)

    def test_add_player_no_game_404(self):
        game_id = '567890'
        response = self.client.post(
            f"/api/game/{game_id}/add/",
            data={'userId' : '1234'},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)


    def test_add_player_no_user_id_400(self):
        new_game_id = self.create_game()

        response = self.client.post(
            f"/api/game/{new_game_id}/add/",
            data={'hello' : '1234'},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_add_player_no_user_acct(self):

        new_game_id = self.create_game()

        new_user = self.create_account(
            'username',
            'password',
            'email@email.com'
        )

        response = self.client.post(
            f"/api/game/{new_game_id}/add/",
            data={'userId' : '937ea451-3db3-4af2-9d93-ee8d4cae4b2c',
                  'name' : 'player name'},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)


    def test_add_player(self):

        new_game_id = self.create_game()

        new_user = self.create_account(
            'username',
            'password',
            'email@email.com'
        )

        response = self.client.post(
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

        
        
        # 
        # body = self.get_game_info(game_id)
        # print(body)
