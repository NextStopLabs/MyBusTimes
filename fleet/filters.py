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


class companyUpdateFilter(django_filters.FilterSet):
    class Meta:
        model = companyUpdate
        fields = {
            'operator': ['exact'],
            'routes': ['exact'],
        }

class operatorsFilter(django_filters.FilterSet):
    game = django_filters.CharFilter(method='filter_game')
    
    class Meta:
        model = MBTOperator
        fields = {
            'operator_name': ['icontains', 'exact'],
            'operator_code': ['icontains', 'exact'],
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
            'operator__operator_name': ['exact', 'icontains'],
            'loan_operator': ['exact'],
            'in_service': ['exact'],
            'fleet_number': ['exact', 'icontains'],
            'reg': ['exact', 'icontains'],
        }

class helperFilter(django_filters.FilterSet):
    class Meta:
        model = helper
        fields = {
            'operator': ['exact'],
            'helper': ['exact'],
        }

class historyFilter(django_filters.FilterSet):
    order_by = django_filters.ChoiceFilter(
        choices=(
            ('-create_at', 'Newest First'),
            ('create_at', 'Oldest First'),
        ),
        method='filter_order_by',
        label='Order By',
        empty_label=None,
        initial='-create_at'
    )

    class Meta:
        model = fleetChange
        fields = {
            'operator': ['exact'],
            'vehicle': ['exact'], 
            'user': ['exact'],
            'approved_by': ['exact'],
            'approved': ['exact'],
            'pending': ['exact'],
            'disapproved': ['exact']
        }

    def filter_order_by(self, queryset, name, value):
        return queryset.order_by(value)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.data.get('order_by'):
            self.queryset = self.queryset.order_by('-create_at')

class typeFilter(django_filters.FilterSet):
    type_name_contains = django_filters.CharFilter(field_name='type_name', lookup_expr='icontains', label='Type Name Contains')
    type_name_exact = django_filters.CharFilter(field_name='type_name', lookup_expr='exact', label='Type Name Exact')

    vehicleType = django_filters.CharFilter(field_name='vehicleType', lookup_expr='exact', label='Type')
    added_by = django_filters.CharFilter(field_name='added_by', lookup_expr='exact', label='Added By')
    approved_by = django_filters.CharFilter(field_name='approved_by', lookup_expr='exact', label='Approved By')
    id = django_filters.CharFilter(field_name='id', lookup_expr='exact', label='ID')

    class Meta:
        model = vehicleType
        fields = ['id', 'type_name_exact', 'type_name_contains', 'type', 'added_by', 'approved_by']

class groupFilter(django_filters.FilterSet):
    class Meta:
        model = group
        fields = ['group_name', 'group_owner', 'private']

class organisationFilter(django_filters.FilterSet):
    class Meta:
        model = organisation
        fields = ['organisation_name', 'organisation_owner']

class operatorNameFilter(django_filters.FilterSet):
    class Meta:
        model = MBTOperator
        fields = {
            'operator_name': ['icontains'],
            'operator_code': ['exact'],
        }

class liveriesFilter(django_filters.FilterSet):
    class Meta:
        model = liverie
        fields = {
            'id': ['exact'],
            'name': ['icontains'],
        }