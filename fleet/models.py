from django.db import models
from .fields import ColourField, ColoursField, CSSField
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.exceptions import ValidationError
from pathlib import Path
import json
from django.core.serializers.json import DjangoJSONEncoder
from main.models import CustomUser, region
from django.utils.text import slugify

class mapTileSet(models.Model):
    name = models.CharField(max_length=100, unique=True)
    tile_url = models.CharField(max_length=255)
    attribution = models.CharField(max_length=255, blank=True, null=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Map Tile Sets"

class liverie(models.Model):
    id = models.AutoField(primary_key=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True, blank=True)
    colour = models.CharField(
        max_length=100, help_text="For the most simplified version of the livery"
    )
    left_css = CSSField(
        max_length=2048,
        blank=True,
        verbose_name="Left CSS",
    )
    right_css = CSSField(
        max_length=2048,
        blank=True,
        verbose_name="Right CSS",
    )

    text_colour = models.CharField(max_length=100, blank=True)
    stroke_colour = models.CharField(
        max_length=100, blank=True, help_text="Use sparingly, often looks shit"
    )

    updated_at = models.DateTimeField(null=True, blank=True)
    published = models.BooleanField(
        default=False,
        help_text="Tick to include in the CSS and be able to apply this livery to vehicles",
    )

    added_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=False, related_name='livery_added_by')
    aproved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, related_name='livery_aproved_by', blank=True, null=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "liveries"

    def __str__(self):
        return f"{self.id} - {self.name}"

class vehicleType(models.Model):
    id = models.AutoField(primary_key=True)
    type_name = models.CharField(max_length=100, blank=False, unique=True)
    active = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False, help_text="If true, this type will not be displayed in the UI.")
    double_decker = models.BooleanField(default=False)
    lengths = models.TextField(blank=True)
    type = models.CharField(blank=False, default='Bus')
    fuel = models.CharField(blank=False, default='Diesel')
    added_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=False, related_name='types_added_by')
    aproved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='types_aproved_by')

    def __str__(self):
        return self.type_name 
    
class group(models.Model):
    id = models.AutoField(primary_key=True)
    group_name = models.CharField(blank=False, unique=True)
    group_owner = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=False, related_name='group_owner')

    private = models.BooleanField(default=False)
    
    def __str__(self):
        return self.group_name
    
class organisation(models.Model):
    id = models.AutoField(primary_key=True)
    organisation_name = models.CharField(blank=False)
    organisation_owner = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=False, related_name='organisation_owner')
    
    def __str__(self):
        return self.organisation_name

def default_operator_details():
    return {
        "website": "https://example.com",
        "twitter": "@example",
        "game": "OMSI2",
        "type": "real-company",
        "transit_authorities": "TFL, TfGM",
    }


class MBTOperator(models.Model):
    id = models.AutoField(primary_key=True)
    operator_name = models.CharField(blank=False, unique=True, help_text="Name of the operator, e.g., 'Example Bus Company'")
    operator_code = models.CharField(blank=False, unique=True)
    operator_slug = models.SlugField(unique=True, blank=True, max_length=255)
    operator_details = models.JSONField(default=default_operator_details, blank=True, null=True)
    private = models.BooleanField(default=False)
    public = models.BooleanField(default=False)
    show_trip_id = models.BooleanField(default=True)

    vehicles_for_sale = models.IntegerField(default=0)

    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, blank=False, related_name='owner')
    group = models.ForeignKey(group, on_delete=models.SET_NULL, blank=True, null=True)
    organisation = models.ForeignKey(organisation, on_delete=models.SET_NULL, blank=True, null=True)
    region = models.ManyToManyField(region, related_name='operators')
    mapTile = models.ForeignKey(mapTileSet, on_delete=models.SET_NULL, null=True, blank=True, related_name='operators')

    def save(self, *args, **kwargs):
        if not self.operator_slug:
            base_slug = slugify(self.operator_name)
            slug = base_slug
            counter = 1

            # Check for existing slugs
            while MBTOperator.objects.filter(operator_slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.operator_slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.operator_name

class companyUpdate(models.Model):
    id = models.AutoField(primary_key=True)
    operator = models.ForeignKey(MBTOperator, on_delete=models.CASCADE, blank=False, related_name='company_update_operator')
    update_text = models.TextField(blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    routes = models.ManyToManyField('routes.Route', related_name='company_updates', blank=True)

    def __str__(self):
        return f"{self.operator.operator_name} - {self.created_at} - {self.update_text[:50]}"

class helperPerm(models.Model):
    PERMS_CHOICES = [(i, str(i)) for i in range(1, 6)]  # 1 to 5

    id = models.AutoField(primary_key=True)
    perm_name = models.CharField(blank=False, unique=True, help_text="Name of the permission")
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
    helper = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='helper_users')
    perms = models.ManyToManyField(helperPerm, related_name='helper_perms')

    def __str__(self):
        operator_name = self.operator.operator_name if self.operator else "No Operator"
        helper_name = self.helper.username if self.helper else "No Helper"
        return f"{operator_name} - {helper_name}"

def default_operator_id():
    # returns the operator instance or ID to set
    from .models import MBTOperator
    return MBTOperator.objects.get(pk=2265)

class fleet(models.Model):
    id = models.AutoField(primary_key=True, db_index=True)
    operator = models.ForeignKey(MBTOperator, on_delete=models.SET(default_operator_id), blank=True, null=False, related_name='fleet_operator', db_index=True)
    loan_operator = models.ForeignKey(MBTOperator, on_delete=models.SET_NULL, blank=True, null=True, related_name='fleet_loan_operator', db_index=True)

    in_service = models.BooleanField(default=True, db_index=True)
    for_sale = models.BooleanField(default=False, db_index=True)
    preserved = models.BooleanField(default=False, db_index=True)
    on_load = models.BooleanField(default=False, db_index=True)
    open_top = models.BooleanField(default=False, db_index=True)

    fleet_number = models.CharField(blank=True, null=True, db_index=True)
    fleet_number_sort = models.CharField(max_length=100, blank=True, null=True)
    reg = models.CharField(blank=True, null=True, db_index=True)
    prev_reg = models.TextField(blank=True, null=True, db_index=True)

    livery = models.ForeignKey(liverie, on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    colour = models.CharField(blank=True, db_index=True)
    vehicleType = models.ForeignKey(vehicleType,on_delete=models.SET_NULL, null=True, db_index=True)
    type_details = models.CharField(blank=True)

    last_tracked_date = models.DateTimeField(blank=True, null=True, db_index=True)
    last_tracked_route = models.CharField(blank=True, null=True, db_index=True)

    branding = models.CharField(blank=True, db_index=True)
    depot = models.CharField(blank=True, null=True, db_index=True)
    name = models.CharField(blank=True, db_index=True)
    length = models.CharField(blank=True, null=True, db_index=True)
    features = models.JSONField(blank=True, db_index=True)
    notes = models.TextField(blank=True, null=True, db_index=True)
    advanced_details = models.JSONField(blank=True, null=True, db_index=True)

    last_modified_by = models.ForeignKey(CustomUser, blank=False, on_delete=models.SET_NULL, null=True, related_name='fleet_modified_by', db_index=True)
    summary = models.TextField(blank=True)
    
    def __str__(self):
        # Check if livery is None and handle it gracefully
        livery_name = self.livery.name if self.livery else "No Livery"
        operator_name = self.operator.operator_name if self.operator else "No Operator"
        type_name = self.vehicleType.type_name if self.vehicleType else "No Type"

        if self.fleet_number:
            return f"{self.fleet_number} - {self.reg} - {livery_name} - {operator_name} - {type_name}"
        else:
            return f"{self.reg} - {livery_name} - {operator_name} - {type_name}"


class fleetChange(models.Model):
    id = models.AutoField(primary_key=True)
    vehicle = models.ForeignKey(fleet, on_delete=models.SET_NULL, null=True, related_name='history_vehicle_id')
    operator = models.ForeignKey(MBTOperator, on_delete=models.SET_NULL, null=True, related_name='history_operator_id')

    up_vote = models.PositiveIntegerField(default=0)
    down_vote = models.PositiveIntegerField(default=0)
    voters = models.ManyToManyField(CustomUser, related_name='history_voters', blank=True)

    changes = models.TextField(blank=True)
    message = models.TextField(blank=True)
    disapproved_reason = models.TextField(blank=True)

    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True, related_name='history_user')
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True, related_name='history_approved_by')

    create_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    approved = models.BooleanField(default=False)
    pending = models.BooleanField(default=True)
    disapproved = models.BooleanField(default=False)

    def __str__(self):
        return_str = ''

        if self.vehicle:
            return_str += f"{self.vehicle} - "

            # Only try to access vehicle.operator if it exists
            if self.vehicle.operator:
                return_str += f"{self.vehicle.operator.operator_name} - "

            if self.vehicle.vehicleType:
                return_str += f"{self.vehicle.vehicleType.type_name}"

        return return_str
        
class operatorType(models.Model):
    id = models.AutoField(primary_key=True)
    operator_type_name = models.CharField(blank=False)
    published = models.BooleanField(default=False, help_text="Mark this operator type as published to be used in the system.")

    def __str__(self):
        return self.operator_type_name

class reservedOperatorName(models.Model):
    id = models.AutoField(primary_key=True)
    operator_name = models.CharField(blank=False)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, blank=False, related_name='reserved_operator_name_owner')
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True, related_name='reserved_operator_name_approved_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.operator_name} - {self.owner.username} - {'Approved' if self.approved else 'Not Approved'}"

    def clean(self):
        if not self.is_name_reservable(self.operator_name):
            raise ValidationError({'operator_name': f'"{self.operator_name}" contains a non reservable term and cannot be reserved.'})

    @classmethod
    def is_name_reservable(cls, operator_name):
        json_path = Path(settings.MEDIA_ROOT) / 'JSON' / 'non-reservable-names.json'
        with open(json_path, 'r') as file:
            non_reservable_names = json.load(file)

        operator_name_lower = operator_name.lower()
        for forbidden in non_reservable_names:
            if forbidden.lower() in operator_name_lower:
                return False
        return True

class ticket(models.Model):
    id = models.AutoField(primary_key=True)
    operator = models.ForeignKey(MBTOperator, on_delete=models.CASCADE, blank=False, related_name='ticket_operator')
    ticket_name = models.CharField(blank=False)
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2, blank=False)
    ticket_details = models.TextField(blank=True)
    zone = models.CharField(blank=True, help_text="Zone for the ticket (e.g., 'Zone 1', 'Zone A').")
    valid_for_days = models.PositiveIntegerField(blank=True, null=True)
    single_use = models.BooleanField(default=False, help_text="If true, this ticket can only be used once.")
    name_on_ticketer = models.CharField(blank=True, help_text="Name to be displayed on the ticketer for this ticket.")
    colour_on_ticketer = ColourField(max_length=7, blank=True, help_text="Colour of the ticket in hex format (e.g., #FF5733).")
    ticket_category = models.CharField(max_length=100, blank=True, help_text="Category of the ticket (e.g., 'Adult', 'Child', 'Senior').")
    hidden_on_ticketer = models.BooleanField(default=False, help_text="If true, this ticket will not be displayed on the ticketer.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ticket_name} - {self.operator.operator_name}"