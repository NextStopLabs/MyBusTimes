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
    banned = models.BooleanField(default=False)
    banned_date = models.DateTimeField(blank=True, null=True)
    banned_reason = models.TextField(blank=True, null=True)
    total_user_reports = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.username
    
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

class type(models.Model):
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
    route_num = models.CharField(max_length=50, blank=False)
    route_name = models.CharField(max_length=4, blank=True, null=True)
    route_details = models.JSONField(default=default_route_details, blank=True, null=True)
 
    inboud_destination = models.CharField(max_length=100, blank=True, null=True)
    outboud_destination = models.CharField(max_length=100, blank=True, null=True)
    route_operator = models.ForeignKey(MBTOperator, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.route_num

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
        return f"{self.fleet_number} - {self.reg} - {self.livery.name} - {self.type.type_name}"
    
class fleetChange(models.Model):
    id = models.AutoField(primary_key=True)
    vehicle = models.ForeignKey(fleet, on_delete=models.CASCADE)
    operator_new = models.CharField(max_length=50)
    operator_old = models.CharField(max_length=50)
    loan_operator_new = models.CharField(max_length=50)
    loan_operator_old = models.CharField(max_length=50)

    in_service_new = models.BooleanField()
    in_service_old = models.BooleanField()
    for_sale_new = models.BooleanField()
    for_sale_old = models.BooleanField()
    preserved_new = models.BooleanField()
    preserved_old = models.BooleanField()
    on_load_new = models.BooleanField()
    on_load_old = models.BooleanField()
    open_top_new = models.BooleanField()
    open_top_old = models.BooleanField()

    fleet_number_new = models.CharField(max_length=50, blank=True)
    fleet_number_old = models.CharField(max_length=50, blank=True)
    reg_new = models.CharField(max_length=50, blank=True)
    reg_old = models.CharField(max_length=50, blank=True)
    prev_reg_new = models.TextField(blank=True)
    prev_reg_old = models.TextField(blank=True)

    livery_name_new = models.CharField(max_length=50, blank=True)
    livery_name_old = models.CharField(max_length=50, blank=True)
    livery_css_new = models.TextField(blank=True)
    livery_css_old = models.TextField(blank=True)
    colour_new = models.CharField(max_length=50, blank=True)
    colour_old = models.CharField(max_length=50, blank=True)
    type_name_new = models.CharField(max_length=50, blank=True)
    type_name_old = models.CharField(max_length=50, blank=True)
    type_details_new = models.CharField(max_length=50, blank=True)
    type_details_old = models.CharField(max_length=50, blank=True)

    branding_new = models.CharField(max_length=50, blank=True)
    branding_old = models.CharField(max_length=50, blank=True)
    depot_new = models.CharField(max_length=50, blank=True)
    depot_old = models.CharField(max_length=50, blank=True)
    name_new = models.CharField(max_length=50, blank=True)
    name_old = models.CharField(max_length=50, blank=True)
    length_new = models.CharField(max_length=50, blank=True)
    length_old = models.CharField(max_length=50, blank=True)
    features_new = models.TextField(blank=True)
    features_old = models.TextField(blank=True)
    notes_new = models.TextField(blank=True)
    notes_old = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.fleet_number_new} - {self.reg_new} - {self.livery_name_new} - {self.type_name_new}"
    
    def save(self, *args, **kwargs):
        try:
            # Get the original fleet object using vehicle_id (assuming this is fleet.fleet_number)
            vehicle = fleet.objects.get(fleet_number=self.vehicle_id)

            # Populate OLD fields from the original vehicle
            self.type_name_old = vehicle.type.type_name
            self.livery_name_old = vehicle.livery.name
            self.livery_css_old = vehicle.livery.left_css if hasattr(vehicle.livery, 'css') else ''
        except fleet.DoesNotExist:
            pass  # handle if fleet doesn't exist

        # If `type_name_new` or `livery_name_new` isn't manually filled in, try to auto-fill it
        if not self.type_name_new and self.operator_new == vehicle.operator.operator_name:
            self.type_name_new = vehicle.type.type_name
        if not self.livery_name_new:
            self.livery_name_new = vehicle.livery.name
        if not self.livery_css_new and hasattr(vehicle.livery, 'css'):
            self.livery_css_new = vehicle.livery.left_css

        super().save(*args, **kwargs)

@receiver(post_save, sender=fleet)
def create_fleet_change(sender, instance, created, **kwargs):
    # Check if the instance was just created or updated
    if not created:
        # Get the previous state of the fleet object, you can store the previous state in a separate way
        # For simplicity, let's assume you have some logic to fetch the previous state.
        
        previous_fleet = fleet.objects.get(id=instance.id)  # You can optimize how you store previous values
        
        # Create a new fleetChange entry to log changes
        fleet_change = fleetChange(
            vehicle=instance,
            operator_old=previous_fleet.operator.operator_name,
            operator_new=instance.operator.operator_name,
            loan_operator_old=previous_fleet.loan_operator,
            loan_operator_new=instance.loan_operator,
            in_service_old=previous_fleet.in_service,
            in_service_new=instance.in_service,
            for_sale_old=previous_fleet.for_sale,
            for_sale_new=instance.for_sale,
            preserved_old=previous_fleet.preserved,
            preserved_new=instance.preserved,
            on_load_old=previous_fleet.on_load,
            on_load_new=instance.on_load,
            open_top_old=previous_fleet.open_top,
            open_top_new=instance.open_top,
            fleet_number_old=previous_fleet.fleet_number,
            fleet_number_new=instance.fleet_number,
            reg_old=previous_fleet.reg,
            reg_new=instance.reg,
            prev_reg_old=previous_fleet.prev_reg,
            prev_reg_new=instance.prev_reg,
            livery_name_old=previous_fleet.livery.name,
            livery_name_new=instance.livery.name,
            livery_css_old=previous_fleet.livery.css,
            livery_css_new=instance.livery.css,
            colour_old=previous_fleet.colour,
            colour_new=instance.colour,
            type_name_old=previous_fleet.type.type_name,
            type_name_new=instance.type.type_name,
            type_details_old=previous_fleet.details,
            type_details_new=instance.details,
            branding_old=previous_fleet.branding,
            branding_new=instance.branding,
            depot_old=previous_fleet.depot,
            depot_new=instance.depot,
            name_old=previous_fleet.name,
            name_new=instance.name,
            length_old=previous_fleet.length,
            length_new=instance.length,
            features_old=previous_fleet.features,
            features_new=instance.features,
            notes_old=previous_fleet.notes,
            notes_new=instance.notes,
            timestamp=timezone.now()
        )
        fleet_change.save()

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
