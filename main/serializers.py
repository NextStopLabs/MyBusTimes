from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils.timezone import now
import hashlib
from .models import *

class siteUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = siteUpdate
        fields = '__all__'