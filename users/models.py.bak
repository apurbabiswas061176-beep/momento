from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    bio = models.TextField(max_length=500, blank=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', default='default.jpg', blank=True)
    is_verified = models.BooleanField(default=False)
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)
    mood = models.CharField(max_length=30, default='chill', blank=True)

    def __str__(self):
        return self.username
