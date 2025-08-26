from rest_framework import serializers
from fleet.models import MBTOperator 
from .models import *

class stopSerializer(serializers.ModelSerializer):
    class Meta:
        model = stop
        fields = ['stop_name', 'latitude', 'longitude']

class dayTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = dayType  # Correct model reference
        fields = ['id', 'name'] 

class operatorFleetSerializer(serializers.ModelSerializer):
    class Meta:
        model = MBTOperator
        fields = ['id', 'operator_name',  'operator_slug', 'operator_code']

class LinkedRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = route
        fields = ['id', 'route_num', 'route_name']

class relatedRouteSerializer(serializers.ModelSerializer):
    route_operators = operatorFleetSerializer(many=True, read_only=True)

    class Meta:
        model = route
        fields = ['id', 'route_num', 'route_name', 'inbound_destination', 'outbound_destination', 'route_operators']

class serviceUpdateRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = route
        fields = ['id', 'route_num', 'inbound_destination', 'outbound_destination']

class serviceUpdateSerializer(serializers.ModelSerializer):
    effected_route = serviceUpdateRouteSerializer(many=True, read_only=True)

    class Meta:
        model = serviceUpdate
        fields = ['id', 'effected_route', 'start_date', 'end_date', 'update_title', 'update_description']

class routesSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = route
        fields = ['id', 'route_num']

class StopTimeSerializer(serializers.Serializer):
    stop_name = serializers.CharField()
    expected_time = serializers.TimeField()

class routesSerializer(serializers.ModelSerializer):
    route_operators = serializers.PrimaryKeyRelatedField(
        many=True, queryset=MBTOperator.objects.all(), write_only=True
    )
    linked_route_post = serializers.PrimaryKeyRelatedField(
        many=True, queryset=route.objects.all(), write_only=True, required=False
    )
    related_route_post = serializers.PrimaryKeyRelatedField(
        many=True, queryset=route.objects.all(), write_only=True, required=False
    )

    route_operators_data = operatorFleetSerializer(source="route_operators", many=True, read_only=True)
    linked_route = LinkedRouteSerializer(many=True, read_only=True)
    related_route = relatedRouteSerializer(many=True, read_only=True)
    service_updates = serviceUpdateSerializer(many=True, read_only=True)
    full_searchable_name = serializers.SerializerMethodField()

    # Add new SerializerMethodField for RGBA
    route_colour_rgba = serializers.SerializerMethodField()

    class Meta:
        model = route
        fields = [
            'id',
            'route_num',
            'route_name',
            'route_details',
            'inbound_destination',
            'outbound_destination',
            'route_operators',
            'route_operators_data',
            'linked_route_post',
            'linked_route',
            'related_route_post',
            'related_route',
            'service_updates',
            'full_searchable_name',
            'route_colour_rgba',  # Include the new field
        ]

    def get_full_searchable_name(self, obj):
        return ' '.join(part for part in [obj.route_num, obj.inbound_destination, obj.outbound_destination] if part).strip()

    def get_route_colour_rgba(self, obj):
        # Get hex colour from route_details
        colour_hex = obj.route_details.get('route_colour') if obj.route_details else None
        if not colour_hex:
            return None

        # Convert hex to RGBA (assuming alpha = 1)
        colour_hex = colour_hex.lstrip('#')
        if len(colour_hex) == 6:  # standard RGB
            r, g, b = int(colour_hex[:2], 16), int(colour_hex[2:4], 16), int(colour_hex[4:], 16)
            return f'rgba({r}, {g}, {b}, 1)'
        elif len(colour_hex) == 8:  # RGBA hex
            r, g, b, a = int(colour_hex[:2], 16), int(colour_hex[2:4], 16), int(colour_hex[4:6], 16), int(colour_hex[6:], 16)/255
            return f'rgba({r}, {g}, {b}, {a})'
        return None

    def create(self, validated_data):
        linked_routes = validated_data.pop('linked_route_post', [])
        related_routes = validated_data.pop('related_route_post', [])
        route_operators = validated_data.pop('route_operators', [])

        route_instance = route.objects.create(**validated_data)

        if route_operators:
            route_instance.route_operators.set(route_operators)
        if linked_routes:
            route_instance.linked_route.set(linked_routes)
        if related_routes:
            route_instance.related_route.set(related_routes)

        return route_instance

class routesKindaSerializer(serializers.ModelSerializer):
    route_operators = operatorFleetSerializer(many=True, read_only=True)
    stop_times = stopSerializer(many=True, read_only=True)

    class Meta:
        model = route
        fields = [
            'route_id',
            'route_num',
            'route_name',
            'inbound_destination',
            'outbound_destination',
            'route_operators',
            'stop_times',
        ]


class dayTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = dayType
        fields = ['id', 'name']

class timetableSerializer(serializers.ModelSerializer):
    day_type = serializers.StringRelatedField(many=True)
    route = routesSimpleSerializer(read_only=True)
    operator_schedule = serializers.SerializerMethodField()

    def get_operator_schedule(self, obj):
        operator_codes = obj.operator_schedule
        operators = []
    
        for code in operator_codes:
            try:
                operator = MBTOperator.objects.get(operator_code=code)
                operators.append(operator.operator_name)
            except MBTOperator.DoesNotExist:
                operators.append(f"Unknown ({code})")  # Or just skip with: continue
    
        return operators

    
    class Meta:
        model = timetableEntry
        fields = ['id', 'route', 'stop_times', 'day_type', 'operator_schedule']

class timetableDaysSerializer(serializers.ModelSerializer):
    day_type = serializers.StringRelatedField(many=True)
    route = routesSimpleSerializer(read_only=True)

    class Meta:
        model = timetableEntry
        fields = ['id', 'day_type', 'route']

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Define desired weekday order
        weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        # Sort the day_type list according to the order
        data['day_type'] = sorted(
            data['day_type'],
            key=lambda day: weekday_order.index(day) if day in weekday_order else 999
        )

        return data
    
class dutyTripSerializer(serializers.ModelSerializer):
    route = serializers.StringRelatedField()  # Or a nested serializer if needed
    #day = serializers.StringRelatedField(many=True)  # Assuming dayType has a __str__

    class Meta:
        model = dutyTrip
        fields = ['id', 'route', 'start_time', 'end_time', 'start_at', 'end_at']

class dutySerializer(serializers.ModelSerializer):
    duty_operator = operatorFleetSerializer(read_only=True)
    duty_trips = serializers.SerializerMethodField()
    duty_day = serializers.SerializerMethodField()

    class Meta:
        model = duty
        fields = [
            'id', 
            'duty_name', 
            'duty_operator',
            'duty_details',
            'duty_day',
            'duty_trips'
        ]

    def get_duty_trips(self, obj):
        trips = obj.duty_trips.all()  # uses related_name='duty_trips'
        return dutyTripSerializer(trips, many=True).data

    def get_duty_day(self, obj):
        return [day.name for day in obj.duty_day.all()]

class transitAuthoritiesColourSerializer(serializers.ModelSerializer):
    class Meta:
        model = transitAuthoritiesColour
        fields = ['authority_code', 'primary_colour', 'secondary_colour']