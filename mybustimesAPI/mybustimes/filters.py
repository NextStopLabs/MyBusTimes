import django_filters
from .models import *
from django.db.models import Q

class CustomUserFilter(django_filters.FilterSet):
    class Meta:
        model = CustomUser
        fields = {
            'username': ['icontains', 'exact'],  # Combined filters for 'username'
            'banned': ['exact'],
        }

class operatorsFilter(django_filters.FilterSet):
    game = django_filters.CharFilter(method='filter_game')
    
    class Meta:
        model = operator
        fields = {
            'operator_name': ['icontains'],
            'operator_code': ['icontains'],
            'owner': ['exact'],
            'region': ['exact'],
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

class fleetsFilter(django_filters.FilterSet):
    class Meta:
        model = fleet
        fields = {
            'operator': ['exact'],
            'loan_operator': ['exact'],
        }

class badgesFilter(django_filters.FilterSet):
    class Meta:
        model = badge
        fields = {
            'self_asign': ['exact'],
        }

class liverieFilter(django_filters.FilterSet):
    class Meta:
        model = badge
        fields = {
            'self_asign': ['exact'],
        }

class typeFilter(django_filters.FilterSet):
    type_name = django_filters.CharFilter(field_name='type_name', lookup_expr='icontains', label='Type Name')
    type = django_filters.CharFilter(field_name='type', lookup_expr='exact', label='Type')
    added_by = django_filters.CharFilter(field_name='added_by', lookup_expr='exact', label='Added By')
    approved_by = django_filters.CharFilter(field_name='approved_by', lookup_expr='exact', label='Approved By')
    
    class Meta:
        model = type
        fields = ['type_name', 'type', 'added_by', 'approved_by']