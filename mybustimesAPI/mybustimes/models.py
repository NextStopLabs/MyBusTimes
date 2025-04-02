from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    join_date = models.DateTimeField(auto_now_add=True)
    theme_id = models.IntegerField(default=1)
    badges = models.JSONField(default=dict, blank=True, null=True)  # Use `dict` instead of `list`
    ticketer_code = models.CharField(max_length=50, blank=True, null=True)
    static_ticketer_code = models.BooleanField(default=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    banned = models.BooleanField(default=False)
    banned_date = models.DateTimeField(blank=True, null=True)
    banned_reason = models.TextField(blank=True, null=True)
    total_user_reports = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.username

class theme(models.Model):
    id = models.AutoField(primary_key=True)
    theme_name = models.CharField(max_length=50, blank=True, null=True)
    css = models.TextField()  # Stores main CSS styles
    dark_theme = models.BooleanField(default=False)  # Boolean for dark mode

    def __str__(self):
        return f"theme {self.id} - {'Dark' if self.dark_theme else 'Light'}"
