# accounts/views.py
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers


from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer
from .models import Account

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Require authentication
def protected_view(request):
    return Response({"message": "This is a protected view!"})

@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Require authentication
def protected_view(request):
    data = request.data
    # Example: Extracting specific fields from the body
    sessionId = data.get('sessionId')

    # Debugging: Log the received data
    print(f"Received data: {data}")

    # Return a response, including the received data for confirmation
    return Response({
        "message": "Data received successfully!",
        "received_data": data,
        "sessionId": sessionId,
    })

User = get_user_model()
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

@api_view(['POST'])
def register(request):
    if request.method == 'POST':
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'userId': str(user.userId),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_accounts(request):
    if request.method == 'GET':
        accounts = Account.objects.all()  # Retrieve all accounts
        data = accounts.values('username', 'email', 'userId')  # Fetch specific fields
        return Response(data, status=status.HTTP_200_OK)