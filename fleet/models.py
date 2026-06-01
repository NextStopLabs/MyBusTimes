from django.db import connection, models
from simple_history.models import HistoricalRecords
from .fields import ColourField, ColoursField, CSSField
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from pathlib import Path
import json
from django.core.serializers.json import DjangoJSONEncoder
from main.models import CustomUser, region
from django.utils.text import slugify
from simple_history.models import HistoricalRecords

class mapTileSet(models.Model):
    name = models.CharField(max_length=100, unique=True)
    tile_url = models.CharField(max_length=255)
    attribution = models.CharField(max_length=255, blank=True, null=True)
    tracking_trail_colour = models.CharField(
        max_length=32,
        blank=True,
        default='',
        help_text='Colour used for tracking trail arrows/lines on maps using this tile theme.',
    )
    is_default = models.BooleanField(default=False)
    pro_access = models.BooleanField(
        default=False,
        help_text='Allow any user with an active Pro subscription to use this map tile set.',
    )
    allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='allowed_map_tile_sets',
        help_text='Leave empty to make this map tile set available to everyone. Add users to lock it to them.',
    )

    history = HistoricalRecords()

    @classmethod
    def allowed_users_table_exists(cls):
        return cls.allowed_users.through._meta.db_table in connection.introspection.table_names()

    @classmethod
    def pro_access_column_exists(cls):
        table_name = cls._meta.db_table
        table_names = connection.introspection.table_names()
        if table_name not in table_names:
            return False
        with connection.cursor() as cursor:
            columns = connection.introspection.get_table_description(cursor, table_name)
        return any(column.name == 'pro_access' for column in columns)

    @classmethod
    def available_to_user(cls, user):
        queryset = cls.objects.all()
        if not cls.allowed_users_table_exists():
            return queryset
        if getattr(user, 'is_staff', False):
            return queryset
        pro_access_column_exists = cls.pro_access_column_exists()
        unlocked = models.Q(allowed_users__isnull=True)
        if pro_access_column_exists:
            unlocked &= models.Q(pro_access=False)
        if getattr(user, 'is_authenticated', False):
            filters = unlocked | models.Q(allowed_users=user)
            if pro_access_column_exists and user_has_active_pro_subscription(user):
                filters |= models.Q(pro_access=True)
            return queryset.filter(filters).distinct()
        return queryset.filter(unlocked).distinct()

    @classmethod
    def default_for_user(cls, user):
        return cls.available_to_user(user).filter(is_default=True).first() or cls.available_to_user(user).first()

    def is_available_to_user(self, user):
        if not self.allowed_users_table_exists():
            return True
        if getattr(user, 'is_staff', False):
            return True
        pro_access = self.pro_access if self.pro_access_column_exists() else False
        if not self.allowed_users.exists():
            return not pro_access or user_has_active_pro_subscription(user)
        if not getattr(user, 'is_authenticated', False):
            return False
        return self.allowed_users.filter(pk=user.pk).exists() or (
            pro_access and user_has_active_pro_subscription(user)
        )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Map Tile Sets"

def user_has_active_pro_subscription(user):
    if not getattr(user, 'is_authenticated', False):
        return False

    now = timezone.now()
    if (
        getattr(user, 'sub_plan', 'free') in {'pro', 'premium'}
        and getattr(user, 'ad_free_until', None)
        and user.ad_free_until > now
    ):
        return True

    return user.active_subscriptions.filter(
        models.Q(end_date__isnull=True) | models.Q(end_date__gt=now),
        plan__in={'pro', 'premium'},
    ).exists()

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
    declined = models.BooleanField(
        default=False, help_text="Tick to mark this livery as declined and not approved for use"
    )

    added_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=False, related_name='livery_added_by')
    aproved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, related_name='livery_aproved_by', blank=True, null=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "liveries"

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.id} - {self.name}"

class vehicleType(models.Model):
    id = models.AutoField(primary_key=True)
    type_name = models.CharField(max_length=100, blank=False)
    active = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False, help_text="If true, this type will not be displayed in the UI.")
    double_decker = models.BooleanField(default=False)
    lengths = models.TextField(blank=True)
    type = models.CharField(blank=False, default='Bus')
    fuel = models.CharField(blank=False, default='Diesel')
    added_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=False, related_name='types_added_by')
    aproved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='types_aproved_by')

    history = HistoricalRecords()

    def __str__(self):
        return self.type_name 

class favouriteLivery(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favourite_liveries'
    )
    livery = models.ForeignKey(
        liverie,
        on_delete=models.CASCADE,
        related_name='favourited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'livery')
        ordering = ('livery__name',)
        verbose_name_plural = 'Favourite liveries'

    def __str__(self):
        return f"{self.user} - {self.livery}"

class favouriteVehicleType(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favourite_vehicle_types'
    )
    vehicle_type = models.ForeignKey(
        vehicleType,
        on_delete=models.CASCADE,
        related_name='favourited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'vehicle_type')
        ordering = ('vehicle_type__type_name',)
        verbose_name_plural = 'Favourite vehicle types'

    def __str__(self):
        return f"{self.user} - {self.vehicle_type}"

class favouriteOperator(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favourite_operators'
    )
    operator = models.ForeignKey(
        'MBTOperator',
        on_delete=models.CASCADE,
        related_name='favourited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'operator')
        ordering = ('operator__operator_name',)
        verbose_name_plural = 'Favourite operators'

    def __str__(self):
        return f"{self.user} - {self.operator}"

class VehicleTypeChangeRequest(models.Model):
    REQUEST_TYPES = (
        ('edit', 'Edit'),
        ('delete', 'Delete'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('disapproved', 'Disapproved'),
    )

    vehicle_type = models.ForeignKey(vehicleType, on_delete=models.CASCADE, related_name='change_requests')
    requested_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='vehicle_type_change_requests')
    request_type = models.CharField(max_length=10, choices=REQUEST_TYPES)
    proposed_changes = models.JSONField(blank=True, null=True)
    replacement_type = models.ForeignKey(vehicleType, on_delete=models.SET_NULL, null=True, blank=True, related_name='vehicle_type_replacements')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='vehicle_type_change_reviews')
    disapproved_reason = models.TextField(blank=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.vehicle_type} - {self.request_type} ({self.status})"
    
class group(models.Model):
    id = models.AutoField(primary_key=True)
    group_name = models.CharField(blank=False, unique=True)
    group_owner = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=False, related_name='group_owner')
    class OrderBy(models.TextChoices):
        FLEET_NUMBER = 'fleet_number', 'Fleet Number'
        OPERATOR_NAME = 'operator_name', 'Operator Name'

    order_by = models.CharField(
        max_length=20,
        choices=OrderBy.choices,
        default=OrderBy.FLEET_NUMBER,
    )
    private = models.BooleanField(default=False)
    
    history = HistoricalRecords()

    def __str__(self):
        return self.group_name
    
class organisation(models.Model):
    id = models.AutoField(primary_key=True)
    organisation_name = models.CharField(blank=False)
    organisation_owner = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=False, related_name='organisation_owner')
    
    history = HistoricalRecords()

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
    show_livery_border = models.BooleanField(default=False)
    show_trip_id = models.BooleanField(default=True)

    vehicles_for_sale = models.IntegerField(default=0)

    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, blank=False, related_name='owner')
    group = models.ForeignKey(group, on_delete=models.SET_NULL, blank=True, null=True)
    organisation = models.ForeignKey(organisation, on_delete=models.SET_NULL, blank=True, null=True)
    region = models.ManyToManyField(region, related_name='operators')
    mapTile = models.ForeignKey(mapTileSet, on_delete=models.SET_NULL, null=True, blank=True, related_name='operators')

    verified = models.BooleanField(default=False, help_text="Mark this operator as verified to show a verified badge on the operator page.")
    public_notes = models.TextField(blank=True, help_text="Show on the operator pages to explain the company.")

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

    history = HistoricalRecords()

    def __str__(self):
        return self.operator_name

def reset_unavailable_map_tile_sets_for_user(user):
    default_tile_set = mapTileSet.default_for_user(user)
    if default_tile_set is None:
        return 0

    unavailable_tile_set_ids = [
        tile_set.id
        for tile_set in mapTileSet.objects.filter(operators__owner=user).distinct()
        if not tile_set.is_available_to_user(user)
    ]
    if not unavailable_tile_set_ids:
        return 0

    return MBTOperator.objects.filter(
        owner=user,
        mapTile_id__in=unavailable_tile_set_ids,
    ).update(mapTile=default_tile_set)

class companyUpdate(models.Model):
    id = models.AutoField(primary_key=True)
    operator = models.ForeignKey(MBTOperator, on_delete=models.CASCADE, blank=False, related_name='company_update_operator')
    update_text = models.TextField(blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    routes = models.ManyToManyField('routes.Route', related_name='company_updates', blank=True)

    history = HistoricalRecords()

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

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.perm_name} (Level {self.perms_level})"

class helper(models.Model):
    id = models.AutoField(primary_key=True)
    operator = models.ForeignKey(MBTOperator, on_delete=models.CASCADE, blank=True, null=False, related_name='helper_operator')
    helper = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='helper_users')
    perms = models.ManyToManyField(helperPerm, related_name='helper_perms')

    history = HistoricalRecords()

    def __str__(self):
        operator_name = self.operator.operator_name if self.operator else "No Operator"
        helper_name = self.helper.username if self.helper else "No Helper"
        return f"{operator_name} - {helper_name}"

class Depot(models.Model):
    operator = models.ForeignKey(MBTOperator, on_delete=models.CASCADE, related_name='depots')
    name = models.CharField(max_length=100)
    double_decker = models.BooleanField(default=True)
    single_decker = models.BooleanField(default=True)
    minibuses = models.BooleanField(default=True)
    custom_vehicle_options = models.JSONField(default=list, blank=True)
    running_board_categories = models.ManyToManyField(
        'routes.board_category',
        blank=True,
        db_constraint=False,
        related_name='depots',
        limit_choices_to={'board_type': 'running-boards'},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ('name',)
        constraints = [
            models.UniqueConstraint(fields=['operator', 'name'], name='unique_depot_name_per_operator')
        ]

    def __str__(self):
        return f"{self.operator.operator_name} - {self.name}"

    @property
    def vehicle_options(self):
        options = []
        if self.double_decker:
            options.append("Double Decker")
        if self.single_decker:
            options.append("Single Decker")
        if self.minibuses:
            options.append("Minibuses")
        options.extend(self.custom_vehicle_options or [])
        return options

class DepotBoardCategoryVehicleOptions(models.Model):
    depot = models.ForeignKey(Depot, on_delete=models.CASCADE, related_name='category_vehicle_options')
    category = models.ForeignKey(
        'routes.board_category',
        on_delete=models.CASCADE,
        db_constraint=False,
        related_name='depot_vehicle_options',
        limit_choices_to={'board_type': 'running-boards'},
    )
    vehicle_options = models.JSONField(default=list, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ('category__name',)
        constraints = [
            models.UniqueConstraint(fields=['depot', 'category'], name='unique_depot_category_vehicle_options')
        ]

    def __str__(self):
        return f"{self.depot.name} - {self.category}"

def default_operator_id():
    # returns the operator instance or ID to set
    from .models import MBTOperator
    try:
        return MBTOperator.objects.get(operator_code="UC")
    except MBTOperator.DoesNotExist:
        # Create the default "Unknown Company" operator if it doesn't exist
        return MBTOperator.objects.get_or_create(
            operator_code="UC",
            defaults={"operator_name": "Unknown Company"}
        )[0]

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

    history = HistoricalRecords()

    vehicle_category = models.ForeignKey('routes.board_category', on_delete=models.SET_NULL, blank=True, null=True, related_name='fleet_vehicle_category', db_index=True)
    sim_lat = models.FloatField(blank=True, null=True)
    sim_lon = models.FloatField(blank=True, null=True)
    sim_heading = models.FloatField(blank=True, null=True)
    sim_delay = models.IntegerField(blank=True, null=True)
    current_trip = models.ForeignKey('tracking.Trip', on_delete=models.SET_NULL, blank=True, null=True, related_name='fleet_current_trip')
    updated_at = models.DateTimeField(db_index=True, blank=True, null=True)

    def __str__(self):
        # Handle related objects safely
        try:
            livery_name = self.livery.name if self.livery else "No Livery"
        except Exception:
            livery_name = "No Livery"

        try:
            operator_name = self.operator.operator_name
        except Exception:
            operator_name = "No Operator"

        try:
            type_name = self.vehicleType.type_name if self.vehicleType else "No Type"
        except Exception:
            type_name = "No Type"

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

    history = HistoricalRecords()

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

    history = HistoricalRecords()

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

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.operator_name} - {self.owner.username} - {'Approved' if self.approved else 'Not Approved'}"

    def clean(self):
        if not self.is_name_reservable(self.operator_name):
            raise ValidationError({'operator_name': f'"{self.operator_name}" contains a non reservable term and cannot be reserved.'})

    @classmethod
    def is_name_reservable(cls, operator_name):
        json_path = Path(settings.MEDIA_URL) / 'JSON' / 'non-reservable-names.json'
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

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.ticket_name} - {self.operator.operator_name}"
