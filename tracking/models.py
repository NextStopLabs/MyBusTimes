import json

from django.db import models
from fleet.models import fleet
from routes.models import route
from gameData.models import game
from django.utils import timezone
from django.utils import timezone
from main.models import CustomUser

def default_tracking_data():
    return {
        "X": 0,
        "Y": 0,
        "heading": 0,
    }

def default_tracking_history():
    return []

class Trip(models.Model):
    trip_id = models.AutoField(primary_key=True, db_index=True)
    trip_display_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    trip_vehicle = models.ForeignKey(fleet, on_delete=models.CASCADE, db_index=True)
    trip_route = models.ForeignKey(route, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    trip_route_num = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    trip_driver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    trip_start_location = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    trip_end_location = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    trip_start_at = models.DateTimeField(null=True, blank=True, db_index=True)
    trip_end_at = models.DateTimeField(null=True, blank=True, db_index=True)
    trip_updated_at = models.DateTimeField(auto_now=True, db_index=True)
    trip_ended = models.BooleanField(default=False, db_index=True)
    trip_missed = models.BooleanField(default=False, db_index=True)
    #trip_duty = models.ForeignKey('duty.Duty', on_delete=models.CASCADE, null=True, blank=True, db_index=True)

class Tracking(models.Model):
    tracking_id = models.AutoField(primary_key=True, db_index=True)
    tracking_vehicle = models.ForeignKey(fleet, on_delete=models.CASCADE, db_index=True)
    tracking_route = models.ForeignKey(route, on_delete=models.CASCADE, db_index=True, null=True, blank=True)
    tracking_trip = models.ForeignKey(Trip, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    tracking_game = models.ForeignKey(game, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    tracking_data = models.JSONField(default=default_tracking_data)
    tracking_history_data = models.JSONField(default=default_tracking_history)
    tracking_start_location = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    tracking_end_location = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    tracking_start_at = models.DateTimeField(null=True, blank=True, db_index=True)
    tracking_end_at = models.DateTimeField(null=True, blank=True, db_index=True)
    tracking_updated_at = models.DateTimeField(auto_now=True, db_index=True)
    trip_ended = models.BooleanField(default=False, db_index=True)

    def save(self, *args, **kwargs):
        # Parse tracking_data if it's a string
        if isinstance(self.tracking_data, str):
            try:
                tracking_data_dict = json.loads(self.tracking_data)
            except json.JSONDecodeError:
                tracking_data_dict = {}
        else:
            tracking_data_dict = self.tracking_data

        # Get or initialize history list
        history = self.tracking_history_data or []

        # Make a copy of the dict to add timestamp
        record = tracking_data_dict.copy()
        record['timestamp'] = timezone.now().isoformat()

        history.append(record)

        self.tracking_history_data = history

        # Save tracking_data as a string again if needed
        self.tracking_data = tracking_data_dict

        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['trip_ended']),
            models.Index(fields=['tracking_start_at']),
            models.Index(fields=['tracking_vehicle']),
            models.Index(fields=['tracking_route']),
        ]
