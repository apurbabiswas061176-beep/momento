from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class CustomUser(AbstractUser):
    bio = models.TextField(max_length=500, blank=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', default='default.jpg', blank=True)
    is_verified = models.BooleanField(default=False)
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)
    mood = models.CharField(max_length=30, default='chill', blank=True)
    linked_friend = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='linked_by')
    link_expires_at = models.DateTimeField(null=True, blank=True)
    duo_streak = models.PositiveIntegerField(default=0)
    last_duo_post_date = models.DateField(null=True, blank=True)
    last_streak_updated_date = models.DateField(null=True, blank=True)

    def record_duo_activity(self):
        partner = self.linked_friend
        if not partner:
            return 0
        now = timezone.now()
        if self.link_expires_at and now > self.link_expires_at:
            self.duo_streak = 0
            self.save(update_fields=['duo_streak'])
            return 0
        today = now.date()
        self.last_duo_post_date = today
        self.save(update_fields=['last_duo_post_date'])
        if partner.last_duo_post_date == today and self.last_streak_updated_date != today:
            if self.last_streak_updated_date and (today - self.last_streak_updated_date).days == 1:
                new_streak = self.duo_streak + 1
            else:
                new_streak = 1
            self.duo_streak = new_streak
            self.last_streak_updated_date = today
            self.save(update_fields=['duo_streak', 'last_streak_updated_date'])
            partner.duo_streak = new_streak
            partner.last_streak_updated_date = today
            partner.save(update_fields=['duo_streak', 'last_streak_updated_date'])
        return self.duo_streak

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
