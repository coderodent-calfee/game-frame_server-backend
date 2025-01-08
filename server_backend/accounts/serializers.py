from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['userId'] = str(user.userId)  # Add userId to the token
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Add userId to the response payload
        data['userId'] = str(self.user.userId)
        return data
