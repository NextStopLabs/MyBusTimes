import django_filters
from .models import *
from django.db.models import Q

class CustomUserFilter(django_filters.FilterSet):
    class Meta:
        model = CustomUser
        fields = {
            'username': ['icontains'],
            'banned': ['exact'],
        }

class operatorsFilter(django_filters.FilterSet):
    game = django_filters.CharFilter(method='filter_game')
    
    class Meta:
        model = operator
        fields = {
            'operator_name': ['icontains'],
            'operator_code': ['icontains'],
        }

    def filter_game(self, queryset, name, value):
        # Filter based on the game field inside operator_details JSON field
        return queryset.filter(Q(operator_details__game=value))

class routesFilter(django_filters.FilterSet):
    class Meta:
        model = route
        fields = {
            'route_name': ['icontains'],
            'route_num': ['icontains'],
            'route_operator': ['exact'],
        }