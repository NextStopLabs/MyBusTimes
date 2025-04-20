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

class helperPermFilter(django_filters.FilterSet):
    class Meta:
        model = helperPerm
        fields = {
            'perm_name': ['icontains', 'exact'],
            'perms_level': ['exact'],
        }

    @property
    def qs(self):
        # Override the default queryset to add ordering by perm_name
        parent_qs = super().qs
        return parent_qs.order_by('perm_name')


class operatorsFilter(django_filters.FilterSet):
    game = django_filters.CharFilter(method='filter_game')
    
    class Meta:
        model = MBTOperator
        fields = {
            'operator_name': ['icontains'],
            'operator_code': ['icontains'],
            'owner': ['exact'],
            'region': ['exact'],
        }

    def filter_game(self, queryset, name, value):
        # Filter based on the game field inside operator_details JSON field
        return queryset.filter(Q(operator_details__game=value))

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

class helperFilter(django_filters.FilterSet):
    class Meta:
        model = helper
        fields = {
            'operator': ['exact'],
            'helper': ['exact'],
        }

class typeFilter(django_filters.FilterSet):
    type_name = django_filters.CharFilter(field_name='type_name', lookup_expr='icontains', label='Type Name')
    vehicleType = django_filters.CharFilter(field_name='vehicleType', lookup_expr='exact', label='Type')
    added_by = django_filters.CharFilter(field_name='added_by', lookup_expr='exact', label='Added By')
    approved_by = django_filters.CharFilter(field_name='approved_by', lookup_expr='exact', label='Approved By')
    
    class Meta:
        model = vehicleType
        fields = ['type_name', 'type', 'added_by', 'approved_by']