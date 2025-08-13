from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Chat(models.Model):
    CHAT_TYPE_CHOICES = [
        ("direct", "Direct Message"),
        ("group_public", "Public Group"),
        ("group_private", "Private Group"),
    ]

    chat_type = models.CharField(max_length=20, choices=CHAT_TYPE_CHOICES)
    name = models.CharField(max_length=255, blank=True, null=True)  # For groups
    description = models.TextField(blank=True, null=True)  # For groups
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_chats")
    members = models.ManyToManyField(User, through="ChatMember", related_name="chats")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.chat_type == "direct":
            return f"Direct Chat {self.id}"
        return self.name or f"Group Chat {self.id}"


class ChatMember(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(default=timezone.now)  # For unread tracking
    is_admin = models.BooleanField(default=False)

    class Meta:
        unique_together = ("chat", "user")


class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    text = models.TextField(blank=True)
    image = models.ImageField(upload_to="chat_images/", blank=True, null=True)
    file = models.FileField(upload_to="chat_files/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender} in chat {self.chat.id}"


class ReadReceipt(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="read_receipts")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("message", "user")


class TypingStatus(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="typing_statuses")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_typing = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("chat", "user")
