from django.db import models
from fleet.models import MBTOperator 
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

    inbound_destination = models.CharField(max_length=100, blank=True, null=True)
    outbound_destination = models.CharField(max_length=100, blank=True, null=True)
    other_destination = models.JSONField(blank=True, null=True)
    route_operators = models.ManyToManyField(MBTOperator, blank=False, related_name='route_other_operators',)

    linked_route = models.ManyToManyField('self', symmetrical=True, blank=True)
    related_route = models.ManyToManyField('self', symmetrical=True, blank=True)

    def __str__(self):
        return f"{self.route_num if self.route_num else ''} {' - ' if self.route_name and self.route_num else ''} {self.route_name if self.route_name else ''} {' - ' + self.inbound_destination if self.inbound_destination else ''} {' - ' + self.outbound_destination if self.outbound_destination else ''}"

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

class timetableEntry(models.Model):
    route = models.ForeignKey(route, on_delete=models.CASCADE)
    day_type = models.ManyToManyField(dayType, related_name='timetable_entries', blank=False)
    inbound = models.BooleanField(default=True)
    circular = models.BooleanField(default=False)
    operator_schedule = models.JSONField()
    stop_times = models.JSONField()

    def save(self, *args, **kwargs):
        # Ensure 'times' contains serializable data (convert datetime objects to strings)
        if isinstance(self.stop_times, list):
            self.stop_times = [
                time.isoformat() if isinstance(time, datetime) else time
                for time in self.stop_times
            ]
        super().save(*args, **kwargs)

    def __str__(self):
        if self.inbound == True: 
            direction = "Inbound"
        else:
            direction = "Outbound"
        if self.circular or self.route.outbound_destination == None:
            direction = " Circular"
        return f"{self.route.route_num} - {direction} - ({', '.join([day.name for day in self.day_type.all()])})"

class routeStop(models.Model):
    route = models.ForeignKey(route, on_delete=models.CASCADE)
    inbound = models.BooleanField(default=True)
    circular = models.BooleanField(default=False)
    stops = models.JSONField()

    def __str__(self):
        return f"{self.route.id}"

class duty(models.Model):
    duty_name = models.CharField(max_length=100)
    duty_operator = models.ForeignKey(MBTOperator, on_delete=models.CASCADE, related_name='duties', blank=True, null=True)
    duty_day = models.ManyToManyField(dayType, related_name='duty_types')
    duty_details = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.duty_name if self.duty_name else "Unnamed Duty"
    
class dutyTrip(models.Model):
    duty = models.ForeignKey(duty, on_delete=models.CASCADE, related_name='duty_trips')
    route = models.ForeignKey(route, on_delete=models.CASCADE, related_name='duty_trips')
    start_time = models.TimeField()
    end_time = models.TimeField()
    start_at = models.CharField(max_length=100, blank=True, null=True)
    end_at = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.duty.duty_name} - {self.route.route_num} - {self.start_at} to {self.end_at}"

class transitAuthoritiesColour(models.Model):
    authority_code = models.CharField(max_length=100, unique=True)
    primary_colour = models.CharField(max_length=7, default="#000000")  # Hex colour code
    secondary_colour = models.CharField(max_length=7, default="#FFFFFF")  # Hex colour code

    def __str__(self):
        return self.authority_code

    class Meta:
        verbose_name_plural = "Transit Authorities Colours"