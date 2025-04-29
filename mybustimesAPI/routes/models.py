from django.db import models
from mybustimes.models import MBTOperator 
from gameData.models import game
from datetime import datetime
from django.core.exceptions import ValidationError

def default_route_details():
    return {
        "route_colour": "var(--background-color)",
        "route_text_colour": "var(--text-color)",
        "details": {
            "school_service": "false",
            "contactless": "true",
            "cash": "true"
        }
    }

class route(models.Model):
    id = models.AutoField(primary_key=True)
    route_num = models.CharField(max_length=50, blank=True, null=True)
    route_name = models.CharField(max_length=255, blank=True, null=True)
    route_details = models.JSONField(default=default_route_details, blank=True)
 
    inboud_destination = models.CharField(max_length=100, blank=True, null=True)
    outboud_destination = models.CharField(max_length=100, blank=True, null=True)
    other_destination = models.JSONField(blank=True, null=True)
    route_operators = models.ManyToManyField(MBTOperator, blank=False, related_name='route_other_operators',)

    linked_route = models.ManyToManyField('self', symmetrical=True, blank=True)
    related_route = models.ManyToManyField('self', symmetrical=True, blank=True)

    def __str__(self):
        return f"{self.route_num if self.route_num else ''} {' - ' if self.route_name and self.route_num else ''} {self.route_name if self.route_name else ''} {' - ' + self.inboud_destination if self.inboud_destination else ''} {' - ' + self.outboud_destination if self.outboud_destination else ''}"
    
class serviceUpdate(models.Model):
    effected_route = models.ManyToManyField(route, blank=False, related_name='service_updates')
    start_date = models.DateField()
    end_date = models.DateField()
    update_details = models.JSONField()

    def __str__(self):
        routes = ", ".join([r.route_num for r in self.effected_route.all()])
        return f"{routes} - {self.start_date} - {self.end_date}"

class stop(models.Model):
    stop_name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    game = models.ForeignKey(game, on_delete=models.CASCADE)
    source = models.CharField(max_length=20, default='custom')

    def __str__(self):
        return self.stop_name

class dayType(models.Model):
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name
from datetime import datetime

from datetime import datetime

class timetableEntry(models.Model):
    route = models.ForeignKey(route, on_delete=models.CASCADE)
    stop = models.ForeignKey(stop, on_delete=models.CASCADE)
    day_type = models.ManyToManyField(dayType, related_name='timetable_entries', blank=False)
    times = models.JSONField()

    def save(self, *args, **kwargs):
        # Ensure 'times' contains serializable data (convert datetime objects to strings)
        if isinstance(self.times, list):
            self.times = [
                time.isoformat() if isinstance(time, datetime) else time
                for time in self.times
            ]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.route.id} - {self.stop.stop_name} @ {', '.join(self.times)} ({', '.join([day.name for day in self.day_type.all()])})"


