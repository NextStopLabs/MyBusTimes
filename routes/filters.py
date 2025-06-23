import django_filters
from .models import *
from django.db.models import Q

class routesFilter(django_filters.FilterSet):
    operator_code = django_filters.CharFilter(method='filter_by_operator_code')

    class Meta:
        model = route
        fields = {
            'id': ['exact'],
            'route_name': ['icontains'], 
            'route_num': ['icontains'],
            'route_operators': ['exact'],
        }

    def filter_by_operator_code(self, queryset, name, value):
        return queryset.filter(route_operators__operator_code__iexact=value)

class timetableFilter(django_filters.FilterSet):
    class Meta:
        model = timetableEntry
        fields = {
            'route': ['exact'],
            'day_type': ['exact'],
        }

class dayTypeFilter(django_filters.FilterSet):
    class Meta:
        model = dayType
        fields = {
            'id': ['exact'],
            'name': ['icontains'],
        }

class timetableDaysFilter(django_filters.FilterSet):
    class Meta:
        model = timetableEntry
        fields = {
            'route': ['exact'],
            'day_type': ['exact'],
        }

class dutyFilter(django_filters.FilterSet):

    class Meta:
        model = duty
        fields = {
            'id': ['exact'],
            'duty_name': ['icontains', 'exact'],
            'duty_operator': ['exact'],
            'duty_day': ['exact'],
        }

class transitAuthoritiesColourFilter(django_filters.FilterSet):
    class Meta:
        model = transitAuthoritiesColour
        fields = {
            'id': ['exact'],
            'authority_code': ['icontains', 'exact']
        }