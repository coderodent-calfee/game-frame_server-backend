import json
from collections import defaultdict
from channels.generic.websocket import AsyncWebsocketConsumer
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

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
                if session_id:
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

def socket_session_connect(session_id, user_id, socket_id, room_name):
    logger.info(f"*** handle Session->User : '{str(socket_id)[-6:]}->{str(user_id)[:6]}'")
    logger.info("*** session user: %s %s", session_id, user_id)
    logger.info("*** room: %s", room_name)

    socketSession[socket_id] = session_id
    logger.info(f"*** handle socket->Session : socketSession[{str(socket_id)[-6:]}]->{str(socketSession[socket_id])[:6]}'")
    socketSession[session_id] = user_id
    logger.info(f"*** handle Session->User : socketSession[{str(session_id)[:6]}]->{str(socketSession[session_id])[:6]}'")

    if room_name not in socketSession:
        socketSession[room_name] = {}
    if user_id not in socketSession[room_name]:
        socketSession[room_name][user_id] = {}
    logger.info(f"*** handle room->user :socketSession[{str(room_name)}][{user_id}]='{str(socketSession[room_name][user_id])}'")

def socket_session_player(player_id, socket_id, room_name):
    session_id = socketSession.get(socket_id, None)
    user_id = socketSession.get(session_id, None) if session_id else None

    if room_name in socketSession:
        if user_id in socketSession[room_name]:
            socketSession[room_name][user_id][session_id] = player_id
    logger.info(f"*** handle session player :socketSession[{str(room_name)}][{user_id}][{session_id}]='{str(socketSession[room_name][user_id][session_id])}'")

def socket_session_disconnect(socket_id, room_name):
    user_id = None
    player_id = None
    session_id = socketSession.pop(socket_id, None)
    user_id = socketSession.pop(session_id, None) if session_id else None
    
    if user_id is not None and room_name in socketSession:
        if user_id in socketSession[room_name]:
            player_id = socketSession[room_name][user_id].pop(session_id, None)
    
    logger.info(f"*** remove socket->Session : socketSession[{str(socket_id)[-6:]}]->{str(socketSession[socket_id])[:6]}'")
    logger.info(f"*** remove Session->User : socketSession[{str(session_id)[:6]}]->{str(socketSession[session_id])[:6]}'")
    logger.info(f"*** remove session player :socketSession[{str(room_name)}][{user_id}][{session_id}] was '{str(player_id)[:6]}'")

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.socket_id = self.channel_name
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'game_{self.room_name}'
        print(f"*** Socket Id : {str(self.socket_id)[-6:]}")
        logger.info(f"*** Socket Id : {str(self.socket_id)[-6:]}")

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        logger.info("*** GameConsumer connection closed")
        room_name = self.room_name
        socket_id = self.socket_id
        socket_session_disconnect(socket_id, room_name)
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        logger.info("Received data: %s", text_data)
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


    async def player_added(self, event):
        message = event['message']
        logger.info("player_added: %s", message)

        # Send the message to the WebSocket
        await self.send(text_data=json.dumps({
            'type': 'player_added',
            'message': message,
        }))
    
    async def broadcast_message(self, event):
        await self.send(text_data=json.dumps(event["data"]))
        
    @classmethod
    def send_message_to_group(cls, group_name, json_data):
        logger.info("*** GameConsumer send_message_to_group: %s", group_name)
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

        socket_session_player(player_id, socket_id, room_name)

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'handle_session_player',
            'message': f' socketSession[room_name][user_id][session_id] = player_id',
            'session_id': session_id,
            'user_id': user_id,
            'player_id': player_id,
        }))
