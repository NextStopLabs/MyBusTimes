from importlib.metadata import files
from django.db import models
from main.models import MBTTeam
# Create your models here.
class TicketType(models.Model):
    type_name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    discord_category_id = models.CharField(max_length=100, blank=True, null=True)
    team = models.ForeignKey(MBTTeam, on_delete=models.CASCADE, related_name='ticket_types')

    def __str__(self):
        return self.type_name

class Ticket(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE, related_name='tickets')
    user = models.ForeignKey('main.CustomUser', on_delete=models.CASCADE, related_name='tickets')
    sender_email = models.EmailField(blank=True, null=True)
    assigned_team = models.ForeignKey(MBTTeam, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    assigned_agent = models.ForeignKey('main.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    discord_channel_id = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey('main.CustomUser', on_delete=models.CASCADE, related_name='ticket_messages')
    username = models.CharField(max_length=100, blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    files = models.FileField(upload_to='ticket_messages/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    seen_by = models.ManyToManyField('main.CustomUser', related_name='seen_ticket_messages', blank=True)  # read receipts

class Notification(models.Model):
    user = models.ForeignKey('main.CustomUser', on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    url = models.URLField(blank=True, null=True)  # e.g. link to the ticket
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class TicketSession(models.Model):
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name='session')
    active_users = models.ManyToManyField('main.CustomUser', related_name='active_ticket_sessions', blank=True)
    last_typing = models.JSONField(default=dict, blank=True)  