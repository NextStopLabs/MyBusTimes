from rest_framework import serializers
from .models import *

class gameSerializer(serializers.ModelSerializer):
    class Meta:
        model = game
        fields = '__all__'