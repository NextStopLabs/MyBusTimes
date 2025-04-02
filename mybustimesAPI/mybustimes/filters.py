import django_filters
from .models import CustomUser

class CustomUserFilter(django_filters.FilterSet):
    class Meta:
        model = CustomUser
        fields = {
            'username': ['icontains'],
            'banned': ['exact'],
        }
