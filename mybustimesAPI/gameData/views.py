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
        json_file_path = os.path.join(settings.MEDIA_ROOT, 'json/gameRoutes', f'{game_name}.json')

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
    def get(self, request, game_name, *args, **kwargs):
        # Define the path to the JSON file in the /media/json directory
        json_file_path = os.path.join(settings.MEDIA_ROOT, 'json/gameRoutes/Dests', f'{game_name}.json')

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