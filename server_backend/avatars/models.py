from django.db import models
from django.conf import settings
import uuid

class Image(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_images'
    )
    type = models.CharField(
        max_length=10,
        choices=[('svg','SVG'), ('png','PNG'), ('jpg','JPG')],
        default='png'
    )
    data = models.BinaryField()  # raw bytes for image content
    private = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "images"

    def __str__(self):
        return f"Image {self.id} ({self.type})"
