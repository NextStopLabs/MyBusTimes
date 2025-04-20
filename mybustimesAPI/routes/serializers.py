from rest_framework import serializers
from mybustimes.models import MBTOperator 
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
        fields = ['id', 'operator_name', 'operator_code']

class LinkedRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = route
        fields = ['id', 'route_num', 'route_name']

class relatedRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = route
        fields = ['id', 'route_num', 'route_name']

class timetableEntrySerializer(serializers.ModelSerializer):
    stop = stopSerializer()
    day_type = serializers.StringRelatedField(many=True)
    times = serializers.ListField(child=serializers.CharField())

    class Meta:
        model = timetableEntry
        fields = ['stop', 'day_type', 'times', 'route']

class routesSerializer(serializers.ModelSerializer):
    linked_route = LinkedRouteSerializer(many=True, read_only=True)
    related_route = relatedRouteSerializer(many=True, read_only=True)
    route_operators = operatorFleetSerializer(many=True, read_only=True)

    class Meta:
        model = route
        fields = [
            'id',
            'route_num',
            'route_name',
            'route_details',
            'inboud_destination',
            'outboud_destination',
            'route_operators',
            'linked_route',
            'related_route',
        ]