import django_filters
from .models import *
from django.db.models import Q

class routesFilter(django_filters.FilterSet):
    class Meta:
        model = route
        fields = {
            'id': ['exact'],
            'route_name': ['icontains'],
            'route_num': ['icontains'],
            'route_operators': ['exact'],
        }