import django_filters
from .models import *
from django.db.models import Q

class siteUpdateFilter(django_filters.FilterSet):
    order_by = django_filters.ChoiceFilter(
        choices=(
            ('-updated_at', 'Newest First'),
            ('updated_at', 'Oldest First'),
        ),
        method='filter_order_by',
        label='Order By',
        empty_label=None,
        initial='-updated_at'
    )

    class Meta:
        model = siteUpdate
        fields = {
            'title': ['icontains'],
            'live': ['exact'],
        }

    def filter_order_by(self, queryset, name, value):
        return queryset.order_by(value)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.data.get('order_by'):
            self.queryset = self.queryset.order_by('-updated_at')