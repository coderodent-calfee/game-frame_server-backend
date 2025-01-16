# server_backend/game/models.py
import uuid

from django.db import models
import secrets
import string

def generate_game_id(length=6):
    # Generate a secure random string of alphanumeric characters
    gameId = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))
    return gameId

class Game(models.Model):
    gameId = models.CharField(primary_key=True, max_length=6, default=generate_game_id)
    status = models.CharField(max_length=50, choices=[
        ('waiting', 'Waiting'),
        ('in-progress', 'In Progress'),
        ('completed', 'Completed')
    ], default='waiting')

    def __str__(self):
        return f"Game {self.gameId} - {self.status}"

class Player(models.Model):
    playerId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game = models.ForeignKey(Game, related_name='players', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    game_identifier = models.CharField(max_length=16, editable=False)
    userId = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='players')

    def save(self, *args, **kwargs):
        # Set game_identifier to the game's id, truncated to 6 characters
        self.game_identifier = self.game.gameId
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.name
