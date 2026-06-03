from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils.timezone import now
import hashlib
from .models import *
from tracking.models import Tracking, Trip
from routes.models import route, board_category
from django.utils import timezone
from datetime import timedelta
from django.db.utils import OperationalError, ProgrammingError
import re

class liverieFleetSerializer(serializers.ModelSerializer):
    class Meta:
        model = liverie
        fields = ['id', 'name', 'colour', 'left_css', 'right_css', 'text_colour', 'stroke_colour']

class typeFleetSerializer(serializers.ModelSerializer):
    class Meta:
        model = vehicleType
        fields = ['id', 'type_name', 'double_decker', 'type', 'fuel']

class operatorFleetSerializer(serializers.ModelSerializer):
    class Meta:
        model = MBTOperator
        fields = ['id', 'operator_name', 'operator_slug', 'operator_code']

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)  # Ensure password is included in input

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 
                  'join_date', 'theme_id', 'badges', 'ticketer_code', 'last_login_ip', 
                  'banned', 'banned_date', 'banned_reason', 'total_user_reports']
        extra_kwargs = {'password': {'write_only': True}}  # Prevents password from showing in responses

    def create(self, validated_data):
        """Override create method to hash the password before saving the user."""
        password = validated_data.pop('password')  # Extract password from validated data
        user = CustomUser(**validated_data)
        user.set_password(password)  # Hash the password
        user.save()
        return user
    
class userSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'theme_id', 'badges', 'banned']    

class userSerializerSimple(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username']

class regionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = region
        fields = '__all__'

class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = route
        fields = ['id', 'route_num', 'inbound_destination', 'outbound_destination']

class companyUpdateSerializer(serializers.ModelSerializer):
    routes = RouteSerializer(many=True, read_only=True)
    
    class Meta:
        model = companyUpdate
        fields = '__all__'

# Lightweight serializer for operator lists (e.g., map filter, dropdowns)
class operatorListSerializer(serializers.ModelSerializer):
    """Minimal serializer for operator lists - much faster than full serializer."""
    is_favourite = serializers.SerializerMethodField()

    def get_is_favourite(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        try:
            return favouriteOperator.objects.filter(user=request.user, operator=obj).exists()
        except (OperationalError, ProgrammingError):
            return False

    class Meta:
        model = MBTOperator
        fields = ['id', 'operator_name', 'operator_slug', 'operator_code', 'is_favourite']

class operatorSerializer(serializers.ModelSerializer):
    region = serializers.PrimaryKeyRelatedField(queryset=region.objects.all(), many=True)  # Allow writing region as IDs
    region_detail = regionsSerializer(source='region', many=True, read_only=True)  # Use regionsSerializer to read related region data
    user = serializers.SerializerMethodField()
    is_favourite = serializers.SerializerMethodField()

    def get_is_favourite(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        try:
            return favouriteOperator.objects.filter(user=request.user, operator=obj).exists()
        except (OperationalError, ProgrammingError):
            return False

    def get_user(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        user = request.user
        
        # Check if user is owner
        is_owner = obj.owner == user
        
        # Check if user is a helper
        is_helper = helper.objects.filter(operator=obj, helper=user).exists()
        
        return {
            'is_owner': is_owner,
            'is_helper': is_helper,
            'has_access': is_owner or is_helper
        }

    class Meta:
        model = MBTOperator
        fields = ['id', 'operator_name', 'operator_slug', 'operator_code', 'operator_details', 'private', 'public', 'show_trip_id', 'owner', 'group', 'organisation', 'region', 'region_detail', 'user', 'is_favourite']

class groupsSerializer(serializers.ModelSerializer):
    group_owner = userSerializerSimple()

    class Meta:
        model = group
        fields = '__all__'

class organisationsSerializer(serializers.ModelSerializer):
    organisation_owner = userSerializerSimple()

    class Meta:
        model = organisation
        fields = '__all__'

class typeSerializer(serializers.ModelSerializer):
    is_favourite = serializers.SerializerMethodField()

    def get_is_favourite(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        try:
            return favouriteVehicleType.objects.filter(user=request.user, vehicle_type=obj).exists()
        except (OperationalError, ProgrammingError):
            return False

    class Meta:
        model = vehicleType
        fields = '__all__'

class helperPermSerializer(serializers.ModelSerializer):
    class Meta:
        model = helperPerm
        fields = '__all__'

class fleetChangesSerializer(serializers.ModelSerializer):
    changes = serializers.SerializerMethodField()

    def get_changes(self, obj):
        # Parse the JSON string into a Python object
        if isinstance(obj.changes, str):
            try:
                changes = json.loads(obj.changes)
                # Format each change entry
                formatted_changes = []
                for change in changes:
                    formatted_changes.append({
                        'field': change.get('item', ''),
                        'from': change.get('from', ''),
                        'to': change.get('to', '')
                    })
                return formatted_changes
            except json.JSONDecodeError:
                return []
        return obj.changes
    user = serializers.CharField(source='user.username', read_only=True)
    approved_by = serializers.CharField(source='approved_by.username', read_only=True)
    vehicle = serializers.SerializerMethodField()
    vehicle_id = serializers.IntegerField(source='vehicle.id', read_only=True)
    operator = serializers.SerializerMethodField()
    approved_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    def get_vehicle(self, obj):
        return f"{obj.vehicle.fleet_number} - {obj.vehicle.reg}"

    def get_operator(self, obj):
        return obj.operator.operator_name

    class Meta:
        model = fleetChange
        fields = ['id', 'vehicle', 'vehicle_id', 'operator', 'changes', 'user', 'approved_by', 'approved_at', 'approved', 'pending', 'disapproved', 'message', 'disapproved_reason', 'up_vote', 'down_vote', 'voters']

class helperPermDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = helperPerm
        fields = ['perm_name']

class ticketSerializer(serializers.ModelSerializer):
    class Meta:
        model = ticket
        fields = '__all__'

class helperSerializer(serializers.ModelSerializer):
    perms = serializers.SerializerMethodField()  # Use SerializerMethodField for custom data formatting
    operator = operatorSerializer()
    
    class Meta:
        model = helper
        fields = ['id', 'operator', 'helper', 'perms']

    def get_perms(self, obj):
        # Get the related perms and return only the 'perm_name' values
        return [perm.perm_name for perm in obj.perms.all()]

class liveriesSerializer(serializers.ModelSerializer):
    is_favourite = serializers.SerializerMethodField()

    def get_is_favourite(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        try:
            return favouriteLivery.objects.filter(user=request.user, livery=obj).exists()
        except (OperationalError, ProgrammingError):
            return False

    class Meta:
        model = liverie
        fields = '__all__'

class TripSerializer(serializers.ModelSerializer):
    trip_route = RouteSerializer(read_only=True)

    class Meta:
        model = Trip
        fields = ['trip_id', 'trip_route', 'trip_end_location', 'trip_end_at', 'trip_start_at', 'trip_ended']

def alphanum_key(fleet_number):
    key_parts = []

    for text in re.split(r'([0-9]+)', fleet_number or ''):
        if not text:
            continue
        if text.isdigit():
            key_parts.append((0, int(text)))
        else:
            key_parts.append((1, text.lower()))

    return tuple(key_parts)


class fleetListSerializer(serializers.ModelSerializer):
    vehicle_type_data = typeFleetSerializer(source='vehicleType', read_only=True, required=False)
    livery = liverieFleetSerializer(required=False)
    operator = operatorFleetSerializer(required=False)
    loan_operator = operatorFleetSerializer(required=False)

    class Meta:
        model = fleet
        fields = [
            'id', 'in_service', 'for_sale', 'preserved', 'on_load', 'open_top',
            'fleet_number', 'reg', 'operator', 'loan_operator',
            'vehicle_type_data', 'type_details', 'livery',
            'colour', 'branding', 'prev_reg', 'depot', 'name',
            'features', 'notes', 'length', 'last_modified_by',
        ]

class fleetSerializer(serializers.ModelSerializer):
    vehicle_type_data = typeFleetSerializer(source='vehicleType', read_only=True, required=False)
    livery = liverieFleetSerializer(required=False)
    operator = operatorFleetSerializer(required=False)
    loan_operator = operatorFleetSerializer(required=False)

    type_id = serializers.PrimaryKeyRelatedField(queryset=vehicleType.objects.all(), source='vehicleType', write_only=True, required=False)
    livery_id = serializers.PrimaryKeyRelatedField(queryset=liverie.objects.all(), source='livery', write_only=True, required=False)
    operator_id = serializers.PrimaryKeyRelatedField(queryset=MBTOperator.objects.all(), source='operator', write_only=True, required=False)
    loan_operator_id = serializers.PrimaryKeyRelatedField(queryset=MBTOperator.objects.all(), source='loan_operator', write_only=True, required=False, allow_null=True)
    vehicle_category = serializers.PrimaryKeyRelatedField(queryset=board_category.objects.all())

    advanced_details = serializers.JSONField(required=False)

    latest_trip = serializers.SerializerMethodField()
    last_trip_date = serializers.SerializerMethodField()
    last_trip_route = serializers.SerializerMethodField()
    last_tracking = serializers.SerializerMethodField()

    next_vehicle = serializers.SerializerMethodField()
    previous_vehicle = serializers.SerializerMethodField()
    last_trip_display = serializers.SerializerMethodField()
    flickr_link = serializers.SerializerMethodField()

    def get_last_trip_display(self, obj):
        trip_date = getattr(obj, '_last_trip_date', None)
        if not trip_date:
            return ''
        local = timezone.localtime(trip_date)
        now   = timezone.localtime(timezone.now())
        diff  = now - local
        if diff <= timedelta(days=1):
            return local.strftime('%H:%M')
        if local.year != now.year:
            return local.strftime('%d %b %Y')
        return local.strftime('%d %b')

    def get_flickr_link(self, obj):
        reg = obj.reg.replace(' ', '') if obj.reg else ''
        reg_cut = reg.replace(' ', '') if reg else ''
        prev_reg = obj.prev_reg.replace(' ', '') if obj.prev_reg else ''
        prev_reg_cut = prev_reg.replace(' ', '') if prev_reg else ''

        if prev_reg:
            return f'https://www.flickr.com/search/?text="{reg}"%20or%20{reg_cut}%20or%20"{prev_reg}"%20or%20{prev_reg_cut}&sort=date-taken-desc'
        else:
            return f'https://www.flickr.com/search/?text="{reg}"%20or%20{reg_cut}&sort=date-taken-desc'

    def get_next_vehicle(self, obj):
        if not obj.fleet_number_sort:
            return None
        next_v = (
            fleet.objects
            .filter(operator_id=obj.operator_id, in_service=True, fleet_number_sort__gt=obj.fleet_number_sort)
            .exclude(id=obj.id)
            .order_by('fleet_number_sort')
            .values('id', 'fleet_number', 'reg', 'operator__operator_slug')
            .first()
        )
        if next_v:
            display = f"{next_v['fleet_number']} - {next_v['reg']}" if next_v['reg'] and next_v['fleet_number'] else next_v['reg'] or next_v['fleet_number'] or str(next_v['id'])
            return {
                'id': next_v['id'],
                'fleet_number': next_v['fleet_number'],
                'reg': next_v['reg'],
                'display': display,
                'link': f"/operator/{next_v['operator__operator_slug']}/vehicles/{next_v['id']}/"
            }
        return None

    def get_previous_vehicle(self, obj):
        if not obj.fleet_number_sort:
            return None
        prev_v = (
            fleet.objects
            .filter(operator_id=obj.operator_id, in_service=True, fleet_number_sort__lt=obj.fleet_number_sort)
            .exclude(id=obj.id)
            .order_by('-fleet_number_sort')
            .values('id', 'fleet_number', 'reg', 'operator__operator_slug')
            .first()
        )
        if prev_v:
            display = f"{prev_v['fleet_number']} - {prev_v['reg']}" if prev_v['reg'] and prev_v['fleet_number'] else prev_v['reg'] or prev_v['fleet_number'] or str(prev_v['id'])
            return {
                'id': prev_v['id'],
                'fleet_number': prev_v['fleet_number'],
                'reg': prev_v['reg'],
                'display': display,
                'link': f"/operator/{prev_v['operator__operator_slug']}/vehicles/{prev_v['id']}/"
            }
        return None

    class Meta:
        model = fleet
        fields = [
            'id', 'last_trip_date', 'last_trip_route', 'in_service', 'for_sale', 'preserved', 'on_load', 'open_top',
            'fleet_number', 'reg', 'operator', 'operator_id',
            'loan_operator', 'loan_operator_id',
            'vehicle_type_data', 'type_id',
            'type_details', 'livery', 'livery_id',
            'colour', 'branding', 'prev_reg', 'depot', 'name',
            'features', 'notes', 'length', 'last_modified_by', 'latest_trip', 'last_tracking',
            'next_vehicle', 'previous_vehicle', 'flickr_link',
            'last_trip_display', 'advanced_details', 'vehicle_category',
        ]

    def get_latest_trip(self, obj):
        latest_trip = getattr(obj, '_latest_trip', None)
        if latest_trip:
            return TripSerializer(latest_trip).data
        return None
    
    def get_last_tracking(self, obj):
        from tracking.models import Tracking
        latest_tracking = getattr(obj, '_latest_tracking', None)
        if latest_tracking:
            return {
                'tracking_data': latest_tracking.tracking_data,
                'ended_location': latest_tracking.trip_ended
            }
        return None

    def get_last_trip_date(self, obj):
        latest_trip = getattr(obj, '_latest_trip', None)
        if latest_trip:
            return latest_trip.trip_start_at
        return None

    def get_last_trip_route(self, obj):
        latest_trip = getattr(obj, '_latest_trip', None)
        if not latest_trip:
            return None
        if latest_trip.trip_route:
            return str(latest_trip.trip_route.route_num)
        elif latest_trip.trip_route_num:
            return str(latest_trip.trip_route_num)
        return None

class operatorTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = operatorType
        fields = '__all__'

class operatorNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = MBTOperator
        fields = ['id', 'operator_name']
