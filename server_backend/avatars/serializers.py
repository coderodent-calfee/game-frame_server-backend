from rest_framework import serializers
from .models import Image

class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ['id', 'uploader', 'type', 'private', 'created_at']
        # omit `data` for list view; we'll serve raw bytes in a separate endpoint
