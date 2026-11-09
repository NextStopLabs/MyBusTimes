import django_filters
from .models import *
from django.db.models import Q

class routesFilter(django_filters.FilterSet):
    operator_code = django_filters.CharFilter(method='filter_by_operator_code')
    has_stops = django_filters.BooleanFilter(method='filter_has_stops')
    stops_have_cords = django_filters.BooleanFilter(method='filter_stops_have_cords')

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

    def filter_has_stops(self, queryset, name, value):
        return queryset.filter(routestop__stops__isnull=False).distinct()
    
    def filter_stops_have_cords(self, queryset, name, value):
        if not value:
            return queryset

        return queryset.filter(
            routestop__stops__icontains="cords"
        ).distinct()
    
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
            'board_type': ['exact'],
            'category': ['exact'],
        }

class transitAuthoritiesColourFilter(django_filters.FilterSet):
    class Meta:
        model = transitAuthoritiesColour
        fields = {
            'id': ['exact'],
            'authority_code': ['icontains', 'exact']
        }