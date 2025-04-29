import django_filters
from .models import *
from django.db.models import Q

class routesFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='search_filter', label='Search')

    def search_filter(self, queryset, name, value):
        if value.isdigit():
            return queryset.filter(route_num=value)
        return queryset.filter(
            Q(inboud_destination__icontains=value) | 
            Q(outboud_destination__icontains=value) | 
            Q(other_destination__icontains=value) |
            Q(route_num__icontains=value)
        )


    class Meta:
        model = route
        fields = {
            'id': ['exact'],
            'route_name': ['icontains'], 
            'route_num': ['icontains'],
            'route_operators': ['exact'],
        }