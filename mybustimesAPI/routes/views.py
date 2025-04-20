from django.shortcuts import render
from rest_framework import generics, permissions, viewsets, status
from django_filters.rest_framework import DjangoFilterBackend

from mybustimes.permissions import ReadOnlyOrAuthenticatedCreate
from .models import *
from .filters import *
from .serializers import *

class routesListView(generics.ListCreateAPIView):
    queryset = route.objects.all()
    serializer_class = routesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = routesFilter

class routesDetailView(generics.RetrieveAPIView):
    queryset = route.objects.all()
    serializer_class = routesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = routesFilter

class routesListView(generics.ListCreateAPIView):
    queryset = route.objects.all()
    serializer_class = routesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = routesFilter

class routesDetailView(generics.RetrieveAPIView):
    queryset = route.objects.all()
    serializer_class = routesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = routesFilter

# Stops
class stopListView(generics.ListCreateAPIView):
    queryset = stop.objects.all()
    serializer_class = stopSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]


class stopDetailView(generics.RetrieveAPIView):
    queryset = stop.objects.all()
    serializer_class = stopSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

# Day Types
class dayTypeListView(generics.ListCreateAPIView):
    queryset = dayType.objects.all()
    serializer_class = dayTypeSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]


# Timetable Entries
class timetableEntryListView(generics.ListCreateAPIView):
    queryset = timetableEntry.objects.all()
    serializer_class = timetableEntrySerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    # Optionally define a filterset for route, dayType, etc.


class timetableEntryDetailView(generics.RetrieveAPIView):
    queryset = timetableEntry.objects.all()
    serializer_class = timetableEntrySerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]