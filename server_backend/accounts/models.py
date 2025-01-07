# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

class Account(AbstractUser):
    bio = models.TextField(null=True, blank=True)
    birthdate = models.DateField(null=True, blank=True)
