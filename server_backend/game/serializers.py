# game/serializers.py
from rest_framework import serializers
from .models import Game, Player

class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['playerId', 'game_identifier', 'name']
        
class GameSerializer(serializers.ModelSerializer):
    players = PlayerSerializer(many=True, read_only=True)

    class Meta:
        model = Game
        fields = ['gameId', 'players', 'status']



