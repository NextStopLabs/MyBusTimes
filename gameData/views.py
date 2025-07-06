import os
import json

from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import generics, status
from rest_framework.views import APIView

from .models import *
from .filters import *
from .serializers import *

class gameListView(generics.ListAPIView):
    queryset = game.objects.all()
    serializer_class = gameSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = gameFilter

class gameDetailView(generics.RetrieveAPIView):
    queryset = game.objects.all()
    serializer_class = gameSerializer
        
class RouteDataView(generics.ListAPIView):
    def get(self, request, game_name, *args, **kwargs):
        # Define the path to the JSON file in the /media/json directory
        json_file_path = os.path.join(settings.MEDIA_ROOT, 'JSON/gameRoutes', f'{game_name}.json')

        # Check if the file exists
        if not os.path.exists(json_file_path):
            return JsonResponse({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Read the JSON file
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            # Return the data as JSON
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class GameTilesView(generics.ListAPIView):
    queryset = game_tiles.objects.all()
    serializer_class = gameTilesSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = gameTilesFilter

class GameTilesDetailsView(generics.ListAPIView):
    queryset = game_tiles.objects.all()
    serializer_class = gameTilesSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = gameTilesFilter

    def get_queryset(self):
        game_name = self.kwargs.get('game')
        return game_tiles.objects.filter(game__game_name=game_name)

class GameTilesJSONDetailView(generics.RetrieveAPIView):
    def get(self, request, game, *args, **kwargs):
        # Retrieve the related game_tiles object
        game_tile = game_tiles.objects.filter(game__game_name=game).first()

        if not game_tile:
            return JsonResponse({'error': 'Game not found or no tiles for this game'}, status=status.HTTP_404_NOT_FOUND)

        # Use the tiles_json_file field to get the correct path
        if not game_tile.tiles_json_file:
            return JsonResponse({'error': 'No tiles JSON file associated with this game'}, status=status.HTTP_404_NOT_FOUND)

        # Construct the full path to the JSON file
        json_file_path = os.path.join(settings.MEDIA_ROOT, game_tile.tiles_json_file.name)

        # Check if the file exists
        if not os.path.exists(json_file_path):
            return JsonResponse({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Read the JSON file
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # Return the data as JSON
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RouteDestsDataView(generics.ListAPIView):
    def get(self, request, game, *args, **kwargs):
        # Define the path to the JSON file in the /media/json directory
        json_file_path = os.path.join(settings.MEDIA_ROOT, 'JSON/gameRoutes/Dests', f'{game}.json')

        # Check if the file exists
        if not os.path.exists(json_file_path):
            return JsonResponse({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Read the JSON file
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            # Return the data as JSON
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)