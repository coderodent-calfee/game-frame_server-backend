# game-frame/accounts/signals.py
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

@receiver(user_logged_in)
def log_token(sender, request, user, **kwargs):
    from rest_framework_simplejwt.tokens import AccessToken
    # Generate a new access token
    access_token = AccessToken.for_user(user)
    print(f"JWT Token for user {user}: {access_token}")
