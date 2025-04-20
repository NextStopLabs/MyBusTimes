from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth import get_user_model
import json
from django.core.serializers.json import DjangoJSONEncoder
from .fields import ColourField, ColoursField, CSSField
from django.db.models.signals import post_save
from django.dispatch import receiver

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
    badges = models.ManyToManyField(badge, related_name='badges', blank=True)
    ticketer_code = models.CharField(max_length=50, blank=True, null=True)
    static_ticketer_code = models.BooleanField(default=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    last_active = models.DateTimeField(blank=True, null=True)
    banned = models.BooleanField(default=False)
    banned_date = models.DateTimeField(blank=True, null=True)
    banned_reason = models.TextField(blank=True, null=True)
    total_user_reports = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.username

User = get_user_model()

class LoginIPHashLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ip_hash = models.CharField(max_length=64)  # SHA-256 produces 64 hex chars
    login_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.ip_hash}"    

class liverie(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, db_index=True)
    show_name = models.BooleanField(default=True)
    colour = ColourField(
        max_length=7, help_text="For the most simplified version of the livery"
    )
    left_css = CSSField(
        max_length=1024,
        blank=True,
        verbose_name="Left CSS",
        help_text="Automatically generated from colours and angle",
    )
    right_css = CSSField(
        max_length=1024,
        blank=True,
        verbose_name="Right CSS",
        help_text="Should be a mirror image of the left CSS",
    )
    white_text = models.BooleanField(default=False)
    text_colour = ColourField(max_length=7, blank=True)
    stroke_colour = ColourField(
        max_length=7, blank=True, help_text="Use sparingly, often looks shit"
    )
    updated_at = models.DateTimeField(null=True, blank=True)
    published = models.BooleanField(
        default=False,
        help_text="Tick to include in the CSS and be able to apply this livery to vehicles",
    )
    added_by = models.ForeignKey('CustomUser', on_delete=models.CASCADE, blank=False, related_name='livery_added_by')
    aproved_by = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='livery_aproved_by')

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "liveries"

    def __str__(self):
        return f"{self.id} - {self.name}"

class vehicleType(models.Model):
    id = models.AutoField(primary_key=True)
    type_name = models.CharField(max_length=50, blank=False)
    active = models.BooleanField(default=False)
    double_decker = models.BooleanField(default=False)
    lengths = models.TextField(blank=True)
    type = models.CharField(max_length=50, blank=False, default='Bus')
    fuel = models.CharField(max_length=50, blank=False, default='Diesel')
    added_by = models.ForeignKey('CustomUser', on_delete=models.CASCADE, blank=False, related_name='types_added_by')
    aproved_by = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='types_aproved_by')

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

class MBTOperator(models.Model):
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
    
    owner = models.ForeignKey('CustomUser', on_delete=models.CASCADE, blank=False, related_name='owner')
    group = models.ForeignKey(group, on_delete=models.CASCADE, blank=True, null=True)
    organisation = models.ForeignKey(organisation, on_delete=models.CASCADE, blank=True, null=True)
    region = models.ManyToManyField(region, related_name='operators')
    
    def __str__(self):
        return self.operator_name

class helperPerm(models.Model):
    PERMS_CHOICES = [(i, str(i)) for i in range(1, 6)]  # 1 to 5

    id = models.AutoField(primary_key=True)
    perm_name = models.CharField(max_length=50, blank=False)
    perms_level = models.PositiveSmallIntegerField(
        choices=PERMS_CHOICES,
        blank=False,
        default=1,
        help_text="Permission level from 1 (lowest) to 5 (highest)"
    )

    def __str__(self):
        return f"{self.perm_name} (Level {self.perms_level})"

class helper(models.Model):
    id = models.AutoField(primary_key=True)
    operator = models.ForeignKey(MBTOperator, on_delete=models.CASCADE, blank=True, null=False, related_name='helper_operator')
    helper = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='helper_users')
    perms = models.ManyToManyField(helperPerm, related_name='helper_perms')

    def __str__(self):
        return f"{self.operator.operator_name } - {self.helper.username}"
    
class fleet(models.Model):
    id = models.AutoField(primary_key=True)
    operator = models.ForeignKey(MBTOperator, on_delete=models.CASCADE, blank=True, null=False, related_name='fleet_operator')
    loan_operator = models.ForeignKey(MBTOperator, on_delete=models.CASCADE, blank=True, null=True, related_name='fleet_loan_operator')

    in_service = models.BooleanField(default=True)
    for_sale = models.BooleanField(default=False)
    preserved = models.BooleanField(default=False)
    on_load = models.BooleanField(default=False)
    open_top = models.BooleanField(default=False)

    fleet_number = models.CharField(max_length=50)
    reg = models.CharField(max_length=50, blank=True)
    prev_reg = models.TextField(blank=True)

    livery = models.ForeignKey(liverie, on_delete=models.CASCADE, null=True, blank=True)
    colour = models.CharField(max_length=50, blank=True)
    vehicleType = models.ForeignKey(vehicleType, on_delete=models.CASCADE)
    type_details = models.CharField(max_length=50, blank=True)

    last_tracked_date = models.DateTimeField(blank=True, null=True)
    last_tracked_route = models.CharField(max_length=50, blank=True)

    branding = models.CharField(max_length=50, blank=True)
    depot = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=50, blank=True)
    length = models.CharField(max_length=50, blank=True)
    features = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    last_modified_by = models.ForeignKey(CustomUser, blank=False, on_delete=models.SET_NULL, null=True, related_name='fleet_modified_by')

    def __str__(self):
        # Check if livery is None and handle it gracefully
        livery_name = self.livery.name if self.livery else "No Livery"
        
        # If type is also nullable, handle that as well
        type_name = self.vehicleType.type_name if self.vehicleType else "No Type"
        
        return f"{self.fleet_number} - {self.reg} - {livery_name} - {type_name}"

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

class fleetChange(models.Model):
    id = models.AutoField(primary_key=True)
    vehicle = models.ForeignKey(fleet, on_delete=models.CASCADE, related_name='history_vehicle_id')
    operator = models.ForeignKey(MBTOperator, on_delete=models.CASCADE, related_name='history_operator_id')

    changes = models.TextField(blank=True)
    message = models.TextField(blank=True)
    disapproved_reason = models.TextField(blank=True)

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, blank=True, null=True, related_name='history_user')
    approved_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, blank=True, null=True, related_name='history_approved_by')

    create_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    approved = models.BooleanField(default=False)
    pending = models.BooleanField(default=True)
    disapproved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.vehicle.fleet_number} - {self.vehicle.reg} - {self.user} - {self.create_at}"

class ad(models.Model):
    ad_name = models.CharField(max_length=100)
    ad_img = models.ImageField(upload_to='images/')
    ad_link = models.TextField()

    def __str__(self):
        return self.ad_name

class theme(models.Model):
    id = models.AutoField(primary_key=True)
    theme_name = models.CharField(max_length=50, blank=True, null=True)
    css = models.TextField()  # Stores main CSS styles
    main_colour = models.CharField(max_length=50, blank=True)
    dark_theme = models.BooleanField(default=False)  # Boolean for dark mode

    def __str__(self):
        return f"{self.theme_name} - {'Dark' if self.dark_theme else 'Light'}"
