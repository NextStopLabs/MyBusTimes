from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth import get_user_model
import json
from django.core.serializers.json import DjangoJSONEncoder

class badge(models.Model):
    id = models.AutoField(primary_key=True)
    badge_name = models.CharField(max_length=50, blank=False)
    badge_backgroud = models.TextField(blank=False)
    badge_text_color = models.CharField(max_length=7, blank=False)
    additional_css = models.TextField(blank=True, null=True)
    
    self_asign = models.BooleanField(default=False)

    def __str__(self):
        return self.badge_name

class CustomUser(AbstractUser):
    join_date = models.DateTimeField(auto_now_add=True)
    theme_id = models.IntegerField(default=1)
    badges = models.ManyToManyField(badge, related_name='badges', blank=True, null=True)
    ticketer_code = models.CharField(max_length=50, blank=True, null=True)
    static_ticketer_code = models.BooleanField(default=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    banned = models.BooleanField(default=False)
    banned_date = models.DateTimeField(blank=True, null=True)
    banned_reason = models.TextField(blank=True, null=True)
    total_user_reports = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.username
    
class liverie(models.Model):
    id = models.AutoField(primary_key=True)
    livery_name = models.CharField(max_length=50, blank=False)
    active = models.BooleanField(default=False)
    css = models.TextField()
    added_by = models.CharField(max_length=50, blank=False)
    aproved_by = models.CharField(max_length=50, blank=False)

    def __str__(self):
        return self.livery_name

class type(models.Model):
    id = models.AutoField(primary_key=True)
    type_name = models.CharField(max_length=50, blank=False)
    active = models.BooleanField(default=False)
    double_decker = models.BooleanField(default=False)
    lengths = models.TextField(blank=True)
    type = models.CharField(max_length=50, blank=False, default='Bus')
    fuel = models.CharField(max_length=50, blank=False, default='Diesel')
    added_by = models.CharField(max_length=50, blank=False)
    aproved_by = models.CharField(max_length=50, blank=False)

    def __str__(self):
        return self.type_name 
    
class group(models.Model):
    id = models.AutoField(primary_key=True)
    group_name = models.CharField(max_length=50, blank=False)
    group_owner = models.CharField(max_length=50, blank=False)

    private = models.BooleanField(default=False)
    
    def __str__(self):
        return self.group_name
    
class organisation(models.Model):
    id = models.AutoField(primary_key=True)
    organisation_name = models.CharField(max_length=50, blank=False)
    organisation_owner = models.CharField(max_length=50, blank=False)

    private = models.BooleanField(default=False)
    
    def __str__(self):
        return self.organisation_name


class update(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=50, blank=False)
    body = models.TextField(blank=False)
    tages = models.TextField(blank=False)
    link = models.TextField(blank=True, null=True)

    readBy = models.ManyToManyField(CustomUser, blank=True, related_name="read_updates")

    def __str__(self):
        return self.title


class region(models.Model):
    region_name = models.CharField(max_length=100, unique=True)
    region_code = models.CharField(max_length=3, unique=True)
    region_country = models.CharField(max_length=100, default='England')
    in_the = models.BooleanField(default=False)

    def __str__(self):
        return self.region_name

class featureToggle(models.Model):
    name = models.CharField(max_length=255, unique=True)
    enabled = models.BooleanField(default=True)
    maintenance = models.BooleanField(default=False)
    coming_soon = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {'Enabled' if self.enabled else 'Disabled'}"


class operator(models.Model):
    id = models.AutoField(primary_key=True)
    operator_name = models.CharField(max_length=50, blank=False)
    operator_code = models.CharField(max_length=4, blank=False)
    operator_details = models.JSONField(default={
        "website": "https://example.com",
        "twitter": "@example",
        "game": "OMSI2",
        "type": "real-company"
    }, blank=True, null=True)
    
    private = models.BooleanField(default=False)
    public = models.BooleanField(default=False)
    show_trip_id = models.BooleanField(default=True)
    
    owner = models.CharField(max_length=50, blank=False, default='admin')
    group = models.ForeignKey(group, on_delete=models.CASCADE, blank=True, null=True)
    organisation = models.ForeignKey(organisation, on_delete=models.CASCADE, blank=True, null=True)
    region = models.ManyToManyField(region, related_name='operators')
    
    def __str__(self):
        return self.operator_name
    
class route(models.Model):
    id = models.AutoField(primary_key=True)
    route_num = models.CharField(max_length=50, blank=False)
    route_name = models.CharField(max_length=4, blank=True, null=True)
    route_details = models.JSONField(default={
  "route_colour": "var(--background-color)",
  "route_text_colour": "var(--text-color)",
  "details": {
    "school_service": "false",
    "contactless": "true",
    "cash": "true"
  }
}, blank=True, null=True)
 
    inboud_destination = models.CharField(max_length=100, blank=True, null=True)
    outboud_destination = models.CharField(max_length=100, blank=True, null=True)
    route_operator = models.ForeignKey(operator, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.route_num

class fleet(models.Model):
    
    id = models.AutoField(primary_key=True)
    operator = models.ForeignKey('operator', on_delete=models.CASCADE, blank=True, null=False, related_name='fleet_operator')
    loan_operator = models.ForeignKey('operator', on_delete=models.CASCADE, blank=True, null=True, related_name='fleet_loan_operator')

    in_service = models.BooleanField(default=True)
    for_sale = models.BooleanField(default=False)
    preserved = models.BooleanField(default=False)
    on_load = models.BooleanField(default=False)
    open_top = models.BooleanField(default=False)

    fleet_number = models.CharField(max_length=50)
    reg = models.CharField(max_length=50, blank=True)
    prev_reg = models.TextField(blank=True)

    livery = models.ForeignKey(liverie, on_delete=models.CASCADE)
    colour = models.CharField(max_length=50, blank=True)
    type = models.ForeignKey(type, on_delete=models.CASCADE)
    type_details = models.CharField(max_length=50, blank=True)

    last_tracked_date = models.DateTimeField(blank=True, null=True)
    last_tracked_route = models.CharField(max_length=50, blank=True)

    branding = models.CharField(max_length=50, blank=True)
    depot = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=50, blank=True)
    length = models.CharField(max_length=50, blank=True)
    features = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.fleet_number} - {self.livery.livery_name} - {self.type.type_name}"

    def save(self, *args, **kwargs):
        if self.pk:  # Check if updating an existing fleet entry
            old_instance = fleet.objects.get(pk=self.pk)
            changes = {}
            old_values = {}
            new_values = {}

            for field in self._meta.fields:
                field_name = field.name
                old_value = getattr(old_instance, field_name)
                new_value = getattr(self, field_name)

                if old_value != new_value:
                    changes[field_name] = {"old": old_value, "new": new_value}
                    old_values[field_name] = old_value
                    new_values[field_name] = new_value

            if changes:
                FleetChangeLog.objects.create(
                    fleet=self,
                    user=getattr(self, 'modified_by', None),  # Use `modified_by` if set
                    changed_fields=", ".join(changes.keys()),
                    old_values=json.dumps(old_values, cls=DjangoJSONEncoder),
                    new_values=json.dumps(new_values, cls=DjangoJSONEncoder),
                )

        super().save(*args, **kwargs)

    
User = get_user_model()  # Dynamically get the CustomUser model


class ad(models.Model):
    ad_name = models.CharField(max_length=100)
    ad_img = models.ImageField(upload_to='images/')
    ad_link = models.TextField()

    def __str__(self):
        return self.ad_name

class FleetChangeLog(models.Model):
    id = models.AutoField(primary_key=True)
    fleet = models.ForeignKey(fleet, on_delete=models.CASCADE, related_name="change_logs")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    changed_fields = models.TextField()  # Stores names of changed fields
    old_values = models.JSONField()  # Stores old values before update
    new_values = models.JSONField()  # Stores new values after update
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        username = self.user.username if self.user else "Unknown"
        return f"Change Log for {self.fleet.fleet_number} by {username} on {self.timestamp}"


class theme(models.Model):
    id = models.AutoField(primary_key=True)
    theme_name = models.CharField(max_length=50, blank=True, null=True)
    css = models.TextField()  # Stores main CSS styles
    main_colour = models.CharField(max_length=50, blank=True)
    dark_theme = models.BooleanField(default=False)  # Boolean for dark mode

    def __str__(self):
        return f"{self.theme_name} - {'Dark' if self.dark_theme else 'Light'}"
