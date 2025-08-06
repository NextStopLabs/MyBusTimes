from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils.timezone import now
import hashlib
from .models import *
from tracking.models import Tracking, Trip
from routes.models import route
from django.utils import timezone
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
        fields = ['id', 'operator_name', 'operator_code']

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

class operatorSerializer(serializers.ModelSerializer):
    region = serializers.PrimaryKeyRelatedField(queryset=region.objects.all(), many=True)  # Allow writing region as IDs
    region_detail = regionsSerializer(source='region', many=True, read_only=True)  # Use regionsSerializer to read related region data

    class Meta:
        model = MBTOperator
        fields = ['id', 'operator_name', 'operator_code', 'operator_details', 'private', 'public', 'show_trip_id', 'owner', 'group', 'organisation', 'region', 'region_detail']

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
    class Meta:
        model = liverie
        fields = '__all__'

class TripSerializer(serializers.ModelSerializer):
    trip_route = RouteSerializer(read_only=True)

    class Meta:
        model = Trip
        fields = ['trip_id', 'trip_route', 'trip_end_location', 'trip_end_at', 'trip_start_at', 'trip_ended']

def alphanum_key(fleet_number):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', fleet_number or '')]


class fleetSerializer(serializers.ModelSerializer):
    vehicle_type_data = typeFleetSerializer(source='vehicleType', read_only=True, required=False)
    livery = liverieFleetSerializer(required=False)
    operator = operatorFleetSerializer(required=False)
    loan_operator = operatorFleetSerializer(required=False)

    type_id = serializers.PrimaryKeyRelatedField(queryset=vehicleType.objects.all(), source='vehicleType', write_only=True, required=False)
    livery_id = serializers.PrimaryKeyRelatedField(queryset=liverie.objects.all(), source='livery', write_only=True, required=False)
    operator_id = serializers.PrimaryKeyRelatedField(queryset=MBTOperator.objects.all(), source='operator', write_only=True, required=False)
    loan_operator_id = serializers.PrimaryKeyRelatedField(queryset=MBTOperator.objects.all(), source='loan_operator', write_only=True, required=False, allow_null=True)

    latest_trip = serializers.SerializerMethodField()
    last_trip_date = serializers.SerializerMethodField()
    last_trip_route = serializers.SerializerMethodField()
    last_tracking = serializers.SerializerMethodField()

    next_vehicle = serializers.SerializerMethodField()
    previous_vehicle = serializers.SerializerMethodField()

    def get_next_vehicle(self, obj):
        current_key = alphanum_key(obj.fleet_number)

        # Get all same-operator vehicles with a higher alphanum key
        candidates = fleet.objects.filter(operator=obj.operator).exclude(id=obj.id)

        # Sort in Python using alphanum_key
        sorted_vehicles = sorted(
            candidates,
            key=lambda v: alphanum_key(v.fleet_number)
        )

        # Find the first one that is greater than current
        for v in sorted_vehicles:
            if alphanum_key(v.fleet_number) > current_key:
                display = f"{v.fleet_number} - {v.reg}" if v.reg and v.fleet_number else v.reg or v.fleet_number or str(v.id)
                return {
                    'id': v.id,
                    'fleet_number': v.fleet_number,
                    'reg': v.reg,
                    'display': display,
                    'link': f"/operator/{v.operator.operator_name}/vehicles/{v.id}/"
                }

        return None

    def get_previous_vehicle(self, obj):
        current_key = alphanum_key(obj.fleet_number)

        candidates = fleet.objects.filter(operator=obj.operator).exclude(id=obj.id)

        sorted_vehicles = sorted(
            candidates,
            key=lambda v: alphanum_key(v.fleet_number)
        )

        previous = None
        for v in sorted_vehicles:
            if alphanum_key(v.fleet_number) >= current_key:
                break
            previous = v

        if previous:
            display = f"{previous.fleet_number} - {previous.reg}" if previous.reg and previous.fleet_number else previous.reg or previous.fleet_number or str(previous.id)
            return {
                'id': previous.id,
                'fleet_number': previous.fleet_number,
                'reg': previous.reg,
                'display': display,
                'link': f"/operator/{previous.operator.operator_name}/vehicles/{previous.id}/"
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
            'next_vehicle', 'previous_vehicle'
        ]

    def get_latest_trip(self, obj):
        from tracking.models import Trip
        now = timezone.now()

        latest_trip = Trip.objects.filter(
            trip_vehicle=obj,
            trip_start_at__lte=now,
            trip_end_at__lte=now  # only past-completed trips
        ).order_by('-trip_start_at').first()

        if latest_trip:
            return TripSerializer(latest_trip).data
        return None
    
    def get_last_tracking(self, obj):
        from tracking.models import Tracking
        now = timezone.now()

        latest_tracking = (
            Tracking.objects
            .filter(tracking_vehicle=obj, tracking_start_at__lte=now)
            .order_by('-tracking_start_at')
            .first()
        )

        if latest_tracking:
            return {
                'tracking_data': latest_tracking.tracking_data,
                'ended_location': latest_tracking.ended_location
            }
        return None


    def get_last_trip_date(self, obj):
        from tracking.models import Trip
        now = timezone.now()
        latest_trip = Trip.objects.filter(trip_vehicle=obj, trip_start_at__lte=now).order_by('-trip_start_at').first()
        if latest_trip:
            return latest_trip.trip_start_at
        return None

    def get_last_trip_route(self, obj):
        from tracking.models import Trip
        now = timezone.now()

        latest_trip = (
            Trip.objects
            .filter(trip_vehicle=obj, trip_start_at__lte=now)
            .order_by('-trip_start_at')
            .first()
        )

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
