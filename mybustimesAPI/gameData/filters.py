import django_filters
from .models import *
from django.db.models import Q

class gameFilter(django_filters.FilterSet):
    class Meta:
        model = game
        fields = {
            'game_name': ['exact', 'icontains'],
        }