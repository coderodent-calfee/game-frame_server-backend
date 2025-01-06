# game-frame/user/views.py
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter

from dj_rest_auth.registration.views import SocialLoginView
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
import requests

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .serializers import UserSerializer
from django.http import JsonResponse

import logging

logger = logging.getLogger(__name__)

logger.info("*** LOG active ***")

class UserList(APIView):
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GoogleCallbackView(APIView):
    def get(self, request):

        print(f" **** GET GOT ****")
        logger.info(f" **** GET GOT ****")
        # Step 1: Get the authorization code from the query parameters
        authorization_code = request.GET.get('code')
        print(f"\n\n **** Authorization Code: {authorization_code} ****")
        logger.info(f"\n\n **** Authorization Code: {authorization_code} ****")
        if not authorization_code:
            return Response({'error': 'Authorization code not found'}, status=400)

        # Step 2: Exchange the authorization code for an access token and refresh token
        token_url = 'https://oauth2.googleapis.com/token'
        data = {
            'code': authorization_code,
            'client_id': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
            'client_secret': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
            'redirect_uri': 'http://localhost:8000/accounts/google/login/callback/',
            'grant_type': 'authorization_code',
        }

        response = requests.post(token_url, data=data)
        token_data = response.json()
        print(f"\n\n **** token_data: {token_data} ****")
        logger.info(f"\n\n **** token_data: {token_data} ****")
        if 'access_token' not in token_data:
            return Response({'error': 'Failed to get access token from Google'}, status=400)

        # Step 3: Use the access token to get the user's Google profile information
        user_info_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f"Bearer {token_data['access_token']}"}
        user_info_response = requests.get(user_info_url, headers=headers)
        user_info = user_info_response.json()

        print(f"\n\n **** access_token: {token_data['access_token']} ****")
        logger.info(f"\n\n **** access_token: {token_data['access_token']} ****")
        print(f"\n\n **** user_info: {user_info} ****")
        logger.info(f"\n\n **** user_info: {user_info} ****")

        # Step 4: You can now use the user info to either create or update a user
        # For simplicity, assuming the user is already created:
        user = self.get_or_create_user(user_info)

        # Step 5: Generate JWT tokens for the user
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        # Step 6: Return the tokens to the client
        return Response({
            'refresh': str(refresh),
            'access': str(access_token),
            'user': user.username
        })

    def get_or_create_user(self, user_info):
        # Replace this with logic to either create a new user or update an existing one
        # Example:
        user, created = User.objects.get_or_create(username=user_info['email'], defaults={
            'email': user_info['email'],
            'first_name': user_info.get('given_name', ''),
            'last_name': user_info.get('family_name', ''),
        })
        return user
    
def google_callback(request):
    pass
    # Get the authorization code from the query parameters
    authorization_code = request.GET.get('code')
    if authorization_code:
        # Print to the console or log the code
        print(f" **** Authorization Code: {authorization_code} ****")
        return JsonResponse({"message": "Authorization code received", "code": authorization_code})
    else:
        return JsonResponse({"error": "Authorization code not found"}, status=400)

class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter
class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter


class CustomGoogleLogin(SocialLoginView):
    # either make more than one or somehow switch on the path
    adapter_class = GoogleOAuth2Adapter  # Or another provider you are using
    client_id = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY

    def get_response(self):
        # Get the user from the social authentication process
        user = self.user
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        return Response({
            'refresh': str(refresh),
            'access': str(access_token),
            'user': user.username
        })