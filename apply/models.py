from django.db import models
from django.conf import settings
from messaging.models import Chat

class Position(models.Model):
    name = models.CharField(max_length=255)
    available_places = models.PositiveIntegerField()
    initial_questions = models.TextField(help_text="One question per line.")
    description = models.TextField(blank=True, null=True)
    requirements = models.TextField(blank=True, null=True, help_text="One requirement per line.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.available_places} places)"


class Application(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]

    # applicant could be linked to the Django User model
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications"
    )

    chat = models.ForeignKey(
        Chat,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications"
    )

    position = models.ForeignKey(
        Position,
        on_delete=models.CASCADE,
        related_name="applications"
    )

    details = models.TextField(blank=True, null=True)
    question_answers = models.JSONField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Application by {self.applicant} for {self.position} - {self.status}"
