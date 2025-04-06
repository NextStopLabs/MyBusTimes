from rest_framework import serializers
from .models import *

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

class themeSerializer(serializers.ModelSerializer):
    class Meta:
        model = theme
        fields = ['id', 'theme_name', 'css', 'dark_theme']

class fleetSerializer(serializers.ModelSerializer):
    class Meta:
        model = fleet
        fields = '__all__'

class operatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = operator
        fields = '__all__'

class liveriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = liverie
        fields = '__all__'

class regionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = region
        fields = '__all__'

class groupsSerializer(serializers.ModelSerializer):
    class Meta:
        model = group
        fields = '__all__'

class organisationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = organisation
        fields = '__all__'

class routesSerializer(serializers.ModelSerializer):
    class Meta:
        model = route
        fields = '__all__'

class adSerializer(serializers.ModelSerializer):
    class Meta:
        model = ad
        fields = '__all__'

class badgesSerializer(serializers.ModelSerializer):
    class Meta:
        model = badge
        fields = '__all__'