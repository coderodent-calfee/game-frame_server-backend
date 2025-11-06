import os
import django
import uuid

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server_backend.settings")
django.setup()

from avatars.models import Image
from django.contrib.auth import get_user_model

# Path to your SVG file
file_path = r"C:\Users\rober\Downloads\people.svg"

# Optional: choose an uploader (replace with actual user id)
User = get_user_model()
uploader = User.objects.first()  # or filter for a specific user

# Read file as bytes
with open(file_path, "rb") as f:
    data = f.read()

# Create the Image object
img = Image.objects.create(
    uploader=uploader,
    type='svg',  # set according to your file
    data=data,
    private=False
)

print(f"Saved image with ID: {img.id}")
