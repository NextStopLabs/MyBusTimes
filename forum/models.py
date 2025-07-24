from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

class Thread(models.Model):
    title = models.CharField(max_length=200)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    locked = models.BooleanField(default=False, help_text="Lock this thread to prevent further replies")
    admin_only = models.BooleanField(default=False, help_text="Only admins can reply to this thread")
    discord_channel_id = models.CharField(max_length=50, blank=True, null=True)
    message_limit = models.IntegerField(default=0, help_text="0 for no limit else maximum number of messages allowed in this thread before it deletes the oldest messages")

    def __str__(self):
        return self.title

class Post(models.Model):
    thread = models.ForeignKey(Thread, related_name="posts", on_delete=models.CASCADE)
    author = models.CharField(max_length=255, help_text="Username of the post author")
    content = models.TextField(help_text="Markdown supported")
    image = models.ImageField(upload_to='forum_posts/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.author}: {self.content[:50]}"
