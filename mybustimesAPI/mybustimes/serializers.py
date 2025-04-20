from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils.timezone import now
import hashlib
from .models import *

class liverieFleetSerializer(serializers.ModelSerializer):
    class Meta:
        model = liverie
        fields = ['id', 'name', 'colour', 'left_css', 'right_css']

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
    

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        request = self.context.get("request")
        ip = self.get_client_ip(request)
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()

        # Save the hash log
        LoginIPHashLog.objects.create(user=self.user, ip_hash=ip_hash)

        # Also update the user's last_login_ip
        self.user.last_login_ip = ip
        self.user.save(update_fields=["last_login_ip"])

        return data

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "")
        return ip
    
class userSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'theme_id', 'badges', 'banned']    

class themeSerializer(serializers.ModelSerializer):
    class Meta:
        model = theme
        fields = ['id', 'theme_name', 'css', 'dark_theme', 'main_colour']

class regionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = region
        fields = '__all__'

class operatorSerializer(serializers.ModelSerializer):
    region = regionsSerializer(many=True, read_only=True)

    class Meta:
        model = MBTOperator
        fields = ['id', 'operator_name', 'operator_code', 'operator_details', 'private', 'public', 'show_trip_id', 'owner', 'group', 'organisation', 'region']

class groupsSerializer(serializers.ModelSerializer):
    class Meta:
        model = group
        fields = '__all__'

class organisationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = organisation
        fields = '__all__'

class adSerializer(serializers.ModelSerializer):
    class Meta:
        model = ad
        fields = '__all__'

class badgesSerializer(serializers.ModelSerializer):
    class Meta:
        model = badge
        fields = '__all__'

class typeSerializer(serializers.ModelSerializer):
    class Meta:
        model = vehicleType
        fields = '__all__'

class helperPermSerializer(serializers.ModelSerializer):
    class Meta:
        model = helperPerm
        fields = '__all__'

class helperPermDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = helperPerm
        fields = ['perm_name']

class helperSerializer(serializers.ModelSerializer):
    perms = serializers.SerializerMethodField()  # Use SerializerMethodField for custom data formatting

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

class fleetSerializer(serializers.ModelSerializer):
    vehicle_type_data = typeFleetSerializer(source='vehicleType', read_only=True)
    livery = liverieFleetSerializer()
    operator = operatorFleetSerializer()
    loan_operator = operatorFleetSerializer()

    type_id = serializers.PrimaryKeyRelatedField(queryset=vehicleType.objects.all(), source='vehicleType', write_only=True, required=False)
    livery_id = serializers.PrimaryKeyRelatedField(queryset=liverie.objects.all(), source='livery', write_only=True, required=False)
    operator_id = serializers.PrimaryKeyRelatedField(queryset=MBTOperator.objects.all(), source='operator', write_only=True, required=False)
    loan_operator_id = serializers.PrimaryKeyRelatedField(queryset=MBTOperator.objects.all(), source='loan_operator', write_only=True, required=False, allow_null=True)

    class Meta:
        model = fleet
        fields = [
            'id', 'last_tracked_date', 'last_tracked_route', 'in_service', 'for_sale', 'preserved', 'on_load', 'open_top',
            'fleet_number', 'reg', 'operator', 'operator_id',
            'loan_operator', 'loan_operator_id',
            'vehicle_type_data', 'type_id',
            'type_details', 'livery', 'livery_id',
            'colour', 'branding', 'prev_reg', 'depot', 'name',
            'features', 'notes', 'length', 'last_modified_by'
        ]
