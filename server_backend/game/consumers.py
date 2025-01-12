import json
from channels.generic.websocket import AsyncWebsocketConsumer
from collections import defaultdict
from channels.generic.websocket import AsyncWebsocketConsumer
import logging

logger = logging.getLogger(__name__)

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

def get_user_from_session(session_id):
    return socketSession.get(session_id, None) if session_id else None

def get_socket_from_session(session_id):
    for socket_id, session in socketSession.items():
        if session == session_id:
            return socket_id
    return None

def get_player_sessions_from_room(room_name):
    output = {}
    if room_name in socketSession:
        for user_id, sessions in socketSession[room_name].items():
            for session_id, player_id in sessions.items():
               output[player_id] = session_id  
    return output

def get_session_from_player(player_id, room_name):
    if room_name in socketSession:
        for user_id, sessions in socketSession[room_name].items():
            # Iterate through sessions for each user
            for session_id, current_player_id in sessions.items():
                if current_player_id == player_id:
                    return session_id
    return None
def get_sessions_from_user(user_id, room_name):
    if room_name in socketSession:
        return socketSession[room_name].get(user_id, None)
    return None

def get_socket_from_player(player_id, room_name):
    session_id = get_session_from_player(player_id, room_name)
    return get_socket_from_session(session_id) if session_id else None


class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info("*** GameConsumer connection established")
        logger.info(f"*** Socket ID (channel_name): {self.channel_name}")
        self.socket_id = self.channel_name
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'game_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        logger.info("GameConsumer connection closed")
        user_id = None
        player_id = None
        room_name = self.room_name
        socket_id = self.socket_id
        session_id = socketSession.pop(socket_id, None)
        user_id = socketSession.pop(session_id, None) if session_id else None

        if user_id is not None and room_name in socketSession:
            if user_id in socketSession[room_name]:
                player_id = socketSession[room_name].pop(session_id, None)

        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        logger.debug("Received data: %s", text_data)
        data = json.loads(text_data)
        message_type = data.get("type")

        # Route message handling based on its type
        if message_type == "clientMessage":
            await self.handle_client_message(data)
        elif message_type == "sessionUser":
            await self.handle_session_user(data)
        elif message_type == "sessionPlayer":
            await self.handle_session_player(data)
        else:
            print(f"Unknown message type: {message_type}")
        
    async def handle_client_message(self, data):
        message = data.get("message")
        print(f"Client message received: {message}")
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': f'{message} received',
            }
        )
        
    async def handle_session_user(self, data):
        logger.info("*** handle_session_user ")

        session_id = data.get("sessionId")
        user_id = data.get("userId")
        socket_id = self.socket_id
        room_name = self.room_name
        logger.info("*** session user: %s %s", session_id, user_id)
        logger.info("*** room: %s", room_name)

        socketSession[socket_id] = session_id
        socketSession[session_id] = user_id

        if room_name not in socketSession:
            socketSession[room_name] = {}
        if user_id not in socketSession[room_name]:
            socketSession[room_name][user_id] = {}

        # Send message to WebSocket
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

        if room_name in socketSession:
            if user_id in socketSession[room_name]:
                socketSession[room_name][user_id] = {}

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'handle_session_user',
            'message': f'socket->session / session->user mapped',
            'session_id': session_id,
            'user_id': user_id,
        }))
