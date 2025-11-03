import json
from collections import defaultdict
from channels.generic.websocket import AsyncWebsocketConsumer
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync, sync_to_async

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

# socketSession structure
# socketSession = {
#     'room_name': {
#         'user_id': {
#             'session_id': 'player_id',
#         },
#     },
#     'socket_id': 'session_id',
#     'session_id': 'user_id',
# }
socketSession = defaultdict(dict)

def reset_socket_session():
    socketSession.clear()
    return socketSession

def get_player_from_session(session_id, room_name):
    user_id = get_user_from_session(session_id)
    session_players = get_session_players_from_user(user_id, room_name)
    return session_players.get(session_id, None)

def get_player_from_socket(socket_id, room_name):
    session_id = get_session_from_socket(socket_id)
    return get_player_from_session(session_id, room_name)

def get_user_from_session(session_id):
    session_id_str = str(session_id) if session_id else None
    return socketSession.get(session_id_str, None) if session_id else None

def get_session_from_socket(socket_id):
    socket_id_str = str(socket_id) if socket_id else None
    return socketSession.get(socket_id_str, None) if socket_id else None

def get_socket_from_session(session_id):
    session_id_str = str(session_id)
    for socket_id_str, session_str in socketSession.items():
        if session_str == session_id_str:
            return socket_id_str
    return None

def get_player_sessions_from_room(room_name):
    room_name_str = str(room_name)
    output = {}
    if room_name_str in socketSession:
        for user_id_str, sessions in socketSession[room_name].items():
            for session_id_str, player_id_str in sessions.items():
                output[player_id_str] = session_id_str
    return output

def get_session_from_player(player_id, room_name):
    room_name_str = str(room_name)
    player_id_str = str(player_id)
    if room_name_str in socketSession:
        for user_id_str, sessions in socketSession[room_name].items():
            for session_id_str, current_player_id_str in sessions.items():
                if current_player_id_str == player_id_str:
                    return session_id_str
    return None

def get_session_players_from_user(user_id, room_name):
    room_name_str = str(room_name)
    user_id_str = str(user_id)
    if room_name_str in socketSession:
        return socketSession[room_name_str].get(user_id_str, {})
    return {}

def get_socket_from_player(player_id, room_name):
    room_name_str = str(room_name)
    player_id_str = str(player_id)
    session_id_str = get_session_from_player(player_id_str, room_name_str)
    return get_socket_from_session(session_id_str) if session_id_str else None

def socket_session_connect(session_id, user_id, socket_id, room_name):
    session_id_str = str(session_id)
    user_id_str = str(user_id)
    socket_id_str = str(socket_id)
    room_name_str = str(room_name)

    socketSession[socket_id_str] = session_id_str
    socketSession[session_id_str] = user_id_str

    if room_name_str not in socketSession:
        socketSession[room_name_str] = {}
    if user_id_str not in socketSession[room_name_str]:
        socketSession[room_name_str][user_id_str] = {}

def socket_session_player(player_id, socket_id, room_name):
    socket_id_str = str(socket_id)
    room_name_str = str(room_name)
    player_id_str = str(player_id)


    session_id_str = socketSession.get(socket_id_str, None)
    user_id_str = socketSession.get(session_id_str, None) if session_id_str else None

    if room_name_str in socketSession:
        if user_id_str in socketSession[room_name_str]:
            socketSession[room_name_str][user_id_str][session_id_str] = player_id_str

def socket_session_disconnect(socket_id, room_name):
    room_name_str = str(room_name)
    socket_id_str = str(socket_id)
    session_id_str = socketSession.pop(socket_id_str, None)
    user_id_str = socketSession.pop(session_id_str, None) if session_id_str else None
    
    print(f"socketSession keys: {list(socketSession.keys())}")
    print(f"room_name={room_name!r} ({type(room_name)}), room_name_str={room_name_str!r}")


    if user_id_str is not None and room_name in socketSession:
        if user_id_str in socketSession[room_name_str]:
            socketSession[room_name_str][user_id_str].pop(session_id_str, None)

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.socket_id = self.channel_name
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'game_{self.room_name}'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        room_name = str(self.room_name)
        socket_id = self.socket_id
        player_id = get_player_from_socket(socket_id, room_name)
        socket_session_disconnect(socket_id, room_name)

        await self.handle_player_disconnect(player_id)
        
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            handlers = {
                "clientMessage": self.handle_client_message,
                "sessionUser": self.handle_session_user,
                "sessionPlayer": self.handle_session_player
            }

            handler = handlers.get(message_type)
            if handler:
                await handler(data)
            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.error("Invalid JSON received")


    async def player_added(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'player_added',
            'message': message,
        }))
        
    async def player_disconnected(self, event):
        await self.send(text_data=json.dumps({
            'type': event.get('type', 'player_disconnected'),
            'message': event.get('message', ''),
            'data': event.get('data', {})
        }))

    async def broadcast_message(self, event):
        await self.send(text_data=json.dumps(event["data"]))
        
    @classmethod
    def send_message_to_group(cls, group_name, json_data):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            group_name,
            {"type": "broadcast_message", "data": json_data})


    async def handle_client_message(self, data):
        message = data.get("message")
        print(f"Client message received: {message}")
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_message',
                "data": {'message': f'{message} received'},
            }
        )
        
    async def handle_session_user(self, data):

        session_id = data.get("sessionId")
        user_id = data.get("userId")
        socket_id = self.socket_id
        room_name = self.room_name
        socket_session_connect(session_id, user_id, socket_id, room_name)
        await self.send(text_data=json.dumps({
            'type': 'handle_session_user',
            'message': f'socket->session / session->user mapped',
            'session_id': session_id,
            'user_id': user_id,
        }))


    async def handle_session_player(self, data):
        player_id = data.get("playerId")
        room_name = self.room_name
        socket_id = self.socket_id
        session_id = socketSession.get(socket_id, None)
        user_id = socketSession.get(session_id, None) if session_id else None
    
        socket_session_player(player_id, socket_id, room_name)
    
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_handle_session_player',
                'message': f'socketSession[{room_name}][{user_id}][{session_id}] = {player_id}',
                'session_id': session_id,
                'user_id': user_id,
                'player_id': player_id,
            }
        )

    async def broadcast_handle_session_player(self, event):
        await self.send(text_data=json.dumps({
            'type': 'handle_session_player',
            'message': event['message'],
            'session_id': event['session_id'],
            'user_id': event['user_id'],
            'player_id': event['player_id'],
        }))

    async def handle_player_disconnect(self, player_id):
        game_id = self.room_name

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'message': f"{player_id} disconnected",
                'type': 'player_disconnected',
                'data': {
                    'playerId': str(player_id),
                    'game_identifier': game_id,
                }
            }
        )
