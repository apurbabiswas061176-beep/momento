from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    bio = models.TextField(max_length=500, blank=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', default='default.jpg', blank=True)
    is_verified = models.BooleanField(default=False)
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)
    mood = models.CharField(max_length=30, default='chill', blank=True)
    linked_friend = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='linked_by')
    link_expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.username



class UserMemory(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='memories')
    title = models.CharField(max_length=60, default='Memory')
    caption = models.CharField(max_length=220, blank=True, default='')
    image = models.ImageField(upload_to='memories/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']