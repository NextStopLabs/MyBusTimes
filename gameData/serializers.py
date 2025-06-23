from rest_framework import serializers
from .models import *
from mybustimesAPI.settings import API_BASE_URL

class gameSerializer(serializers.ModelSerializer):
    class Meta:
        model = game
        fields = '__all__'

class gameSerializerSimple(serializers.ModelSerializer):
    class Meta:
        model = game
        fields = ['id', 'game_name']

class gameTilesSerializer(serializers.ModelSerializer):
    game = gameSerializerSimple()

    class Meta:
        model = game_tiles
        fields = '__all__'