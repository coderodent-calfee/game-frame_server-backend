# accounts/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model  # This will use your custom user model
from django.contrib.auth.models import Group  # If you want to include groups

User = get_user_model()  # This will fetch your custom Account model

class AccountSerializer(serializers.ModelSerializer):
    # Optionally, you can include or exclude fields, or add custom validation
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'bio', 'birthdate')  # Adjust fields as needed

    # You can also add custom validation if necessary
    def validate_email(self, value):
        if not value.endswith('@example.com'):
            raise serializers.ValidationError("Email must be from example.com")
        return value
