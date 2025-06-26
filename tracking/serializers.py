from rest_framework import serializers
from fleet.models import fleet, liverie
from routes.models import route
from .models import Tracking

class LiverySerializer(serializers.ModelSerializer):
    class Meta:
        model = liverie
        fields = ['id', 'name', 'left_css', 'right_css', 'stroke_colour', 'text_colour', 'colour']

class FleetSerializer(serializers.ModelSerializer):
    vehicleType = serializers.SerializerMethodField()
    operator = serializers.SerializerMethodField()
    livery = LiverySerializer(read_only=True)
    colour = serializers.SerializerMethodField()

    def get_vehicleType(self, obj):
        return obj.vehicleType.type_name

    def get_operator(self, obj):
        return obj.operator.operator_name

    def get_colour(self, obj):
        return obj.colour

    class Meta:
        model = fleet
        fields = ['id', 'fleet_number', 'reg', 'vehicleType', 'branding', 'operator', 'livery', 'colour']

class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = route
        fields = ['id', 'route_num', 'inboud_destination', 'outboud_destination']

class trackingDataSerializer(serializers.ModelSerializer):
    tracking_vehicle = FleetSerializer(read_only=True)
    tracking_route = RouteSerializer(read_only=True)

    class Meta:
        model = Tracking
        fields = '__all__'

class trackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tracking
        fields = '__all__'