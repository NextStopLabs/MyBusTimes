from rest_framework import serializers
from fleet.models import fleet, liverie
from routes.models import route
from .models import Tracking, Trip

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
        fields = ['id', 'route_num', 'inbound_destination', 'outbound_destination']

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

class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = [
            "trip_id", "trip_vehicle", "trip_route", "trip_route_num",
            "trip_driver", "trip_start_location", "trip_end_location",
            "trip_start_at", "trip_end_at", "trip_updated_at",
            "trip_ended", "trip_missed",
        ]

class TrackingSerializer(serializers.ModelSerializer):
    tracking_route = RouteSerializer(read_only=True)
    class Meta:
        model = Tracking
        fields = [
            "tracking_id", "tracking_vehicle", "tracking_route", "tracking_trip",
            "tracking_game", "tracking_data", "tracking_history_data",
            "tracking_start_location", "tracking_end_location",
            "tracking_start_at", "tracking_end_at", "tracking_updated_at",
            "trip_ended",
        ]
