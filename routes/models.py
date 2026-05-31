from django.db import models
from simple_history.models import HistoricalRecords
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

class routeType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.name
    
def default_route_operators_id():
    from routes.models import MBTOperator
    return MBTOperator.objects.get(route_operators="BT").id

class route(models.Model):
    id = models.AutoField(primary_key=True)
    route_operators = models.ForeignKey(MBTOperator, on_delete=models.SET(default_route_operators_id), blank=True, null=False, related_name='route_operators', db_index=True)
    hidden = models.BooleanField(default=False)
    route_num = models.CharField(max_length=255, blank=True, null=True)
    route_name = models.CharField(max_length=255, blank=True, null=True)
    route_details = models.JSONField(default=default_route_details, blank=True)

    inbound_destination = models.CharField(max_length=255, blank=True, null=True)
    outbound_destination = models.CharField(max_length=255, blank=True, null=True)
    other_destination = models.JSONField(blank=True, null=True)
    route_operators = models.ManyToManyField(MBTOperator, blank=False, related_name='route_other_operators')

    route_depot = models.CharField(max_length=255, blank=True, null=True)

    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    linked_route = models.ManyToManyField('self', symmetrical=True, blank=True)
    related_route = models.ManyToManyField('self', symmetrical=True, blank=True)

    route_type = models.ForeignKey(routeType, on_delete=models.SET_NULL, blank=True, null=True)

    history = HistoricalRecords()

    def __str__(self):
        parts = [self.route_num]
        if self.route_name:
            parts.append(self.route_name)
        if self.inbound_destination:
            parts.append(self.inbound_destination)
        if self.outbound_destination:
            parts.append(self.outbound_destination)
        return " - ".join(filter(None, parts))

class serviceUpdate(models.Model):
    effected_route = models.ManyToManyField('route', blank=False, related_name='service_updates')
    start_date = models.DateField()
    end_date = models.DateField()
    update_title = models.CharField(max_length=255)
    update_description = models.TextField()

    history = HistoricalRecords()

    def __str__(self):
        prefetched = getattr(self, "_prefetched_objects_cache", {})
        if "effected_route" in prefetched:
            route_nums = [
                (r.route_num or "").strip()
                for r in prefetched["effected_route"]
            ]
            cleaned = [r for r in route_nums if r]
            routes = ", ".join(cleaned) if cleaned else "<no route>"
            return f"{self.update_title} - {routes} - {self.start_date} - {self.end_date}"
        return f"{self.update_title} - {self.start_date} - {self.end_date}"

class stop(models.Model):
    stop_name = models.CharField(max_length=256)
    latitude = models.FloatField()
    longitude = models.FloatField()
    game = models.ForeignKey(game, on_delete=models.CASCADE)
    source = models.CharField(max_length=20, default='custom')

    history = HistoricalRecords()

    def __str__(self):
        return self.stop_name

class dayType(models.Model):
    name = models.CharField(max_length=20)

    history = HistoricalRecords()

    def __str__(self):
        return self.name

class timetableEntry(models.Model):
    route = models.ForeignKey(route, on_delete=models.CASCADE)
    day_type = models.ManyToManyField(dayType, related_name='timetable_entries', blank=False)
    inbound = models.BooleanField(default=True)
    circular = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    operator_schedule = models.JSONField(blank=True, null=True)  # For storing operator-specific schedules
    stop_times = models.TextField(blank=True, null=True)  # JSON string of stop times

    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # Ensure 'times' contains serializable data (convert datetime objects to strings)
        if isinstance(self.stop_times, list):
            self.stop_times = [
                time.isoformat() if isinstance(time, datetime) else time
                for time in self.stop_times
            ]
        super().save(*args, **kwargs)

    history = HistoricalRecords()

    def _route_label(self):
        try:
            route_obj = self.route
        except route.DoesNotExist:
            route_obj = None

        if not route_obj:
            if self.route_id:
                return f"<deleted route {self.route_id}>"
            return "<deleted route>"

        return route_obj.route_num or str(route_obj.pk)

    def __str__(self):
        if self.inbound == True: 
            direction = "Inbound"
        else:
            direction = "Outbound"
        try:
            route_obj = self.route
        except route.DoesNotExist:
            route_obj = None

        if self.circular or not route_obj or route_obj.outbound_destination == None:
            direction = " Circular"
        prefetched = getattr(self, "_prefetched_objects_cache", {})
        if "day_type" in prefetched:
            day_names = [day.name for day in prefetched["day_type"]]
            return f"{self._route_label()} - {direction} - ({', '.join(day_names)})"
        return f"{self._route_label()} - {direction}"

class routeStop(models.Model):
    route = models.ForeignKey(route, on_delete=models.CASCADE)
    inbound = models.BooleanField(default=True)
    circular = models.BooleanField(default=False)
    stops = models.JSONField()
    snapped_route = models.TextField(blank=True, null=True)
    history = HistoricalRecords()

    def __str__(self):
        try:
            return f"{self.route.id}"
        except route.DoesNotExist:
            return f"<deleted route {self.route_id}>" if self.route_id else "<deleted route>"

class board_category(models.Model):
    name = models.CharField(max_length=100)
    parent_category = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='subcategories')
    operator = models.ForeignKey(MBTOperator, on_delete=models.CASCADE, related_name='board_categories', blank=True, null=True)
    board_type = models.CharField(max_length=20, choices=[
        ('duty', 'Duty'),
        ('running-boards', 'Running Board'),
    ], default='duty')

    history = HistoricalRecords()

    def __str__(self):
        if self.parent_category:
            return f"{self.parent_category.name} > {self.name}"
        return self.name
    
    class Meta:
        verbose_name_plural = "Board Categories"

class duty(models.Model):
    duty_name = models.CharField(max_length=100)
    category = models.ForeignKey(board_category, on_delete=models.SET_NULL, blank=True, null=True, related_name='duties')
    duty_operator = models.ForeignKey(MBTOperator, on_delete=models.CASCADE, related_name='duties', blank=True, null=True)
    duty_day = models.ManyToManyField(dayType, related_name='duty_types')
    duty_details = models.JSONField(blank=True, null=True)
    board_type = models.CharField(max_length=20, choices=[
        ('duty', 'Duty'),
        ('running-boards', 'Running Board'),
    ], default='duty')

    history = HistoricalRecords()

    def __str__(self):
        board_type = "Running Board" if self.board_type == "running-boards" else "Duty"
        return f"{self.duty_name if self.duty_name else 'Unnamed Duty'} ({board_type})"
    
class dutyTrip(models.Model):
    duty = models.ForeignKey(duty, on_delete=models.CASCADE, related_name='duty_trips')
    route_link = models.ForeignKey(route, related_name='duty_trip_route', blank=True, null=True, on_delete=models.CASCADE)
    route = models.CharField(max_length=100, blank=True, null=True)
    inbound = models.BooleanField(default=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    start_at = models.CharField(max_length=100, blank=True, null=True)
    end_at = models.CharField(max_length=100, blank=True, null=True)

    history = HistoricalRecords()

    def __str__(self):
        try:
            duty_name = self.duty.duty_name
        except duty.DoesNotExist:
            duty_name = '<deleted duty>'
        except Exception:
            duty_name = getattr(self, 'duty_id', '<no duty>')
        return f"{duty_name} - {self.route or 'No Route'} - {self.start_at} to {self.end_at}"

class transitAuthoritiesColour(models.Model):
    authority_code = models.CharField(max_length=100, unique=True)
    primary_colour = models.CharField(max_length=7, default="#000000")  # Hex colour code
    secondary_colour = models.CharField(max_length=7, default="#FFFFFF")  # Hex colour code

    history = HistoricalRecords()

    def __str__(self):
        return self.authority_code

    class Meta:
        verbose_name_plural = "Transit Authorities Colours"
