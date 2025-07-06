# Python standard library imports
import re
import os
import json
import random
import requests
from datetime import date, datetime, time, timedelta
from itertools import groupby, chain
from functools import cmp_to_key
from collections import defaultdict
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# Django imports
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.core.serializers import serialize
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now, make_aware, datetime, timedelta

# Django REST Framework imports
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, permissions, viewsets, status
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import IntegerField
from django.db.models.functions import Cast

# Project-specific imports
from mybustimes.permissions import ReadOnlyOrAuthenticatedCreate
from .models import *
from routes.models import *
from .filters import *
from .forms import *
from .serializers import *
from routes.serializers import *
from main.models import featureToggle, update


class fleetListView(generics.ListCreateAPIView):
    queryset = fleet.objects.all()
    serializer_class = fleetSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = fleetsFilter

class fleetDetailView(generics.RetrieveAPIView):
    queryset = fleet.objects.all()
    serializer_class = fleetSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = fleetsFilter

class fleetUpdateView(generics.UpdateAPIView):
    queryset = fleet.objects.all()
    serializer_class = fleetSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

class fleetDeleteView(generics.DestroyAPIView):
    queryset = fleet.objects.all()
    serializer_class = fleetSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

class fleetCreateView(generics.CreateAPIView):
    queryset = fleet.objects.all()
    serializer_class = fleetSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        instance = self.get_queryset().get(pk=response.data['id'])
        full_data = self.get_serializer(instance).data
        return Response(full_data, status=status.HTTP_201_CREATED)

class fleetEditUpVote(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            change = fleetChange.objects.get(pk=pk)
        except fleetChange.DoesNotExist:
            return Response({'error': 'Change not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user in change.voters.all():
            return Response({'error': 'You have already voted.'}, status=status.HTTP_400_BAD_REQUEST)

        change.up_vote += 1
        change.voters.add(request.user)
        change.save()

        return Response({'message': 'Upvoted successfully.', 'up_votes': change.up_vote})

class fleetEditDownVote(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            change = fleetChange.objects.get(pk=pk)
        except fleetChange.DoesNotExist:
            return Response({'error': 'Change not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user in change.voters.all():
            return Response({'error': 'You have already voted.'}, status=status.HTTP_400_BAD_REQUEST)

        change.down_vote += 1
        change.voters.add(request.user)
        change.save()

        return Response({'message': 'Downvoted successfully.', 'down_votes': change.down_vote})

class updateListView(generics.ListCreateAPIView):
    serializer_class = companyUpdateSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = companyUpdateFilter

    def get_queryset(self):
        operator_name = self.kwargs.get('name')
        if operator_name:
            return companyUpdate.objects.filter(operator__operator_name=operator_name)
        return companyUpdate.objects.all()

class updateDetailView(generics.RetrieveAPIView):
    serializer_class = companyUpdateSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = companyUpdateFilter

    def get_queryset(self):
        operator_name = self.kwargs.get('name')
        if operator_name:
            return companyUpdate.objects.filter(operator__operator_name=operator_name)
        return companyUpdate.objects.all()

class operatorListView(generics.ListCreateAPIView):
    queryset = MBTOperator.objects.all()
    serializer_class = operatorSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = operatorsFilter

class operatorDetailView(RetrieveAPIView):
    queryset = MBTOperator.objects.all()
    serializer_class = operatorSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = operatorsFilter

    def retrieve(self, request, *args, **kwargs):
        operator_name = self.kwargs.get('name')
        try:
            operator = MBTOperator.objects.get(operator_name=operator_name)
            serializer = self.get_serializer(operator)
            return Response(serializer.data)
        except MBTOperator.DoesNotExist:
            return Response({"message": "Operator not found", "found": False}, status=status.HTTP_200_OK)

class operatorUpdateView(UpdateAPIView):
    queryset = MBTOperator.objects.all()
    serializer_class = operatorSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = operatorsFilter
    lookup_field = 'operator_name'  # lookup by operator_name field

    def get_object(self):
        operator_name = self.kwargs.get('name')
        try:
            return MBTOperator.objects.get(operator_name=operator_name)
        except MBTOperator.DoesNotExist:
            return None

    def update(self, request, *args, **kwargs):
        operator = self.get_object()
        if not operator:
            return Response({"message": "Operator not found", "found": False}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(operator, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

class liveriesListView(generics.ListCreateAPIView):
    queryset = liverie.objects.filter(published=True)
    serializer_class = liveriesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = liveriesFilter 

class liveriesDetailView(generics.RetrieveAPIView):
    queryset = liverie.objects.filter(published=True)
    serializer_class = liveriesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = liveriesFilter 

class organisationsListView(generics.ListCreateAPIView):
    queryset = organisation.objects.all()
    serializer_class = organisationsSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = organisationFilter

class organisationsDetailView(generics.RetrieveAPIView):
    queryset = organisation.objects.all()
    serializer_class = organisationsSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = organisationFilter

class groupsListView(generics.ListCreateAPIView):
    queryset = group.objects.all()
    serializer_class = groupsSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = groupFilter

class groupsDetailView(generics.RetrieveAPIView):
    queryset = group.objects.all()
    serializer_class = groupsSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = groupFilter

class fleetChangesListView(generics.ListCreateAPIView):
    queryset = fleetChange.objects.all()
    serializer_class = fleetChangesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = historyFilter

class fleetChangesDetailView(generics.RetrieveAPIView):
    queryset = fleetChange.objects.all()
    serializer_class = fleetChangesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = historyFilter

class helperListView(generics.ListCreateAPIView):
    queryset = helper.objects.all()
    serializer_class = helperSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = helperFilter

class helperDetailView(generics.RetrieveAPIView):
    queryset = helper.objects.all()
    serializer_class = helperSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = helperFilter

class helperPermsListView(generics.ListCreateAPIView):
    queryset = helperPerm.objects.all()
    serializer_class = helperPermSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = helperPermFilter

class helperPermsDetailView(generics.RetrieveAPIView):
    queryset = helperPerm.objects.all()
    serializer_class = helperPermSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = helperPermFilter

class typeListView(generics.ListCreateAPIView):
    queryset = vehicleType.objects.filter(active=True).order_by('type_name')
    serializer_class = typeSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = typeFilter

class typeDetailView(generics.RetrieveAPIView):
    queryset = vehicleType.objects.filter(active=True).order_by('type_name')
    serializer_class = typeSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = typeFilter

class operatorTypeListView(generics.ListCreateAPIView):
    queryset = operatorType.objects.all()
    serializer_class = operatorTypeSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

class operatorTypeDetailView(generics.RetrieveAPIView):
    queryset = operatorType.objects.all()
    serializer_class = operatorTypeSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

class operatorNameListView(generics.ListCreateAPIView):
    queryset = MBTOperator.objects.all()
    serializer_class = operatorNameSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = operatorNameFilter

#templates
def parse_route_key(route):
    route_num = getattr(route, 'route_num', '')

    # Match patterns
    normal = re.match(r'^(\d+)$', route_num)
    suffix = re.match(r'^(\d+)([A-Za-z]+)$', route_num)
    xprefix = re.match(r'^X(\d+)$', route_num, re.IGNORECASE)
    other = re.match(r'^[A-Za-z]+(\d+)$', route_num)

    if normal:
        return (0, int(normal.group(1)), route_num.upper())
    elif suffix:
        return (1, int(suffix.group(1)), route_num.upper())
    elif xprefix:
        return (2, int(xprefix.group(1)), route_num.upper())
    elif other:
        return (3, int(other.group(1)), route_num.upper())
    else:
        return (4, float('inf'), route_num.upper()) 

def get_unique_linked_routes(initial_routes):
    route_set = set(initial_routes)

    for r in initial_routes:
        route_set.update(r.linked_route.all())
        # related routes are NOT added into this set intentionally

    route_map = {r.id: r for r in route_set}
    graph = {r.id: set() for r in route_set}

    # Only build edges based on 'linked' routes
    for r in route_set:
        for linked in r.linked_route.all():
            if linked.id in graph:
                graph[r.id].add(linked.id)
                graph[linked.id].add(r.id)

    visited = set()
    groups = []

    def dfs(route_id, group):
        if route_id in visited or route_id not in route_map:
            return
        visited.add(route_id)
        group.append(route_map[route_id])
        for neighbor in graph.get(route_id, []):
            dfs(neighbor, group)

    for r in route_set:
        if r.id not in visited:
            group = []
            dfs(r.id, group)
            if group:
                primary = next((g for g in group if g in initial_routes), group[0])
                groups.append({
                    "primary": primary,
                    "linked": [r for r in group if r != primary]
                })

    return sorted(groups, key=lambda g: parse_route_key(g["primary"]))

def get_helper_permissions(user, operator):
    if not user.is_authenticated:
        return []

    if user.is_superuser:
        return ['owner']

    try:
        # Check if user is owner of the operator
        is_owner = MBTOperator.objects.filter(operator_name=operator.operator_name, owner=user).exists()
        if is_owner:
            return ['owner']

        # Get helper instance
        helper_instance = helper.objects.get(helper=user, operator=operator)
        permissions = helper_instance.perms.all()

        # Print permission names for debugging
        perm_names = [perm.perm_name for perm in permissions]
        print(f"Helper permissions for {user.username} on operator {operator.operator_name}: {perm_names}")

        return perm_names

    except helper.DoesNotExist:
        return []

def generate_tabs(active, operator, show_withdrawn=None):

    if show_withdrawn is None:
        vehicle_qs = fleet.objects.filter(operator=operator, in_service=True)
    else:
        vehicle_qs = fleet.objects.filter(operator=operator)
    vehicle_count = vehicle_qs.count()

    duty_count = duty.objects.filter(duty_operator=operator, board_type='duty').count()
    rb_count = duty.objects.filter(duty_operator=operator, board_type='running-boards').count()
    ticket_count = ticket.objects.filter(operator=operator).count()
    route_count = route.objects.filter(route_operators=operator).count()
    update_count = companyUpdate.objects.filter(operator=operator).count()

    tabs = []

    
    
    tab_name = f"{route_count} routes" if active == "routes" else "Routes"
    tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_name}/", "active": active == "routes"})

    tab_name = f"{vehicle_count} vehicles" if active == "vehicles" else "Vehicles"
    tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_name}/vehicles/", "active": active == "vehicles"})

    if duty_count > 0:
        tab_name = f"{duty_count} duties" if active == "duties" else "Duties"
        tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_name}/duties/", "active": active == "duties"})

    if rb_count > 0:
        tab_name = f"{rb_count} running boards" if active == "running_boards" else "Running Boards"
        tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_name}/running-boards/", "active": active == "running_boards"})

    if ticket_count > 0:
        tab_name = f"{ticket_count} tickets" if active == "tickets" else "Tickets"
        tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_name}/tickets/", "active": active == "tickets"})

    if update_count > 0:
        tab_name = f"{update_count} updates" if active == "updates" else "Updates"
        tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_name}/updates/", "active": active == "updates"})

    return tabs

def feature_enabled(request, feature_name):
    feature_key = feature_name.lower().replace('_', ' ')

    try:
        feature = featureToggle.objects.get(name=feature_name)
        if feature.enabled:
            # Feature is enabled, so just return None to let the view continue
            return None

        if feature.maintenance:
            return render(request, 'feature_maintenance.html', {'feature_name': feature_key}, status=503)

        if feature.super_user_only and not request.user.is_superuser:
            return render(request, 'feature_disabled.html', {'feature_name': feature_key}, status=403)

        # Feature is disabled in other ways
        return render(request, 'feature_disabled.html', {'feature_name': feature_key}, status=404)

    except featureToggle.DoesNotExist:
        # If feature doesn't exist, you might want to block or allow
        return render(request, 'feature_disabled.html', {'feature_name': feature_key}, status=404)


def operator(request, operator_name):
    response = feature_enabled(request, "view_routes")
    if response:
        return response

    try:
        operator = MBTOperator.objects.get(operator_name=operator_name)
        routes = list(route.objects.filter(route_operators=operator).order_by('route_num'))

        # Safely get operator_details as a dict or empty dict if None
        details = operator.operator_details or {}

        transit_authority = details.get('transit_authority') or details.get('transit_authorities')
    except MBTOperator.DoesNotExist:
        return render(request, '404.html', status=404)

    regions = operator.region.all()

    transit_authority_details = None
    if transit_authority:
        first_authority_code = transit_authority.split(",")[0].strip()
        transit_authority_details = transitAuthoritiesColour.objects.filter(authority_code=first_authority_code).first()

    helper_permissions = get_helper_permissions(request.user, operator)
    unique_routes = get_unique_linked_routes(routes)
    unique_routes = sorted(unique_routes, key=lambda x: parse_route_key(x['primary']))

    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': operator_name, 'url': f'/operator/{operator_name}/'}]

    tabs = generate_tabs("routes", operator)

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'routes': unique_routes,
        'regions': regions,
        'helper_permissions': helper_permissions,
        'transit_authority_details': transit_authority_details,
        'tabs': tabs,
    }
    return render(request, 'operator.html', context)

def route_detail(request, operator_name, route_id):
    response = feature_enabled(request, "view_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    days = dayType.objects.all()

    selected_day_id = request.GET.get('day')
    selectedDay = 1
    if selected_day_id:
        try:
            selectedDay = dayType.objects.get(id=selected_day_id)
        except dayType.DoesNotExist:
            selectedDay = 1

    serialized_route = routesSerializer(route_instance).data
    full_route_num = serialized_route.get('full_searchable_name', '')

    helper_permissions = get_helper_permissions(request.user, operator)

    # Breadcrumbs
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': route_instance.route_num or 'Route Details', 'url': f'/operator/{operator_name}/route/{route_id}/'}
    ]

    # Operators
    mainOperator = next((op for op in route_instance.route_operators.all() if op.operator_name == operator_name), None)
    otherOperators = [op for op in route_instance.route_operators.all() if op.operator_name != operator_name]
    allOperators = [mainOperator] + otherOperators if mainOperator else otherOperators

    # Timetable entries
    inbound_timetable_entries = timetableEntry.objects.filter(route=route_instance, day_type=selectedDay, inbound=True).order_by('stop_times__stop_time')
    inbound_timetableData = inbound_timetable_entries.first().stop_times if inbound_timetable_entries.exists() else {}

    inbound_flat_schedule = list(chain.from_iterable(
        entry.operator_schedule for entry in inbound_timetable_entries
    )) if inbound_timetable_entries.exists() else []

    inbound_groupedSchedule = []
    for code, group in groupby(inbound_flat_schedule):
        count = len(list(group))
        try:
            op = MBTOperator.objects.get(operator_code=code)
            name = op.operator_name
        except MBTOperator.DoesNotExist:
            name = code
        inbound_groupedSchedule.append({
            "code": code,
            "name": name,
            "colspan": count
        })

    if not inbound_timetableData:
        inbound_first_stop_name = None
        inbound_first_stop_times = []
    else:
        inbound_first_stop_name = list(inbound_timetableData.keys())[0]
        inbound_first_stop_times = inbound_timetableData[inbound_first_stop_name]["times"]

    outbound_timetable_entries = timetableEntry.objects.filter(route=route_instance, day_type=selectedDay, inbound=False).order_by('stop_times__stop_time')
    outbound_timetableData = outbound_timetable_entries.first().stop_times if outbound_timetable_entries.exists() else {}

    outbound_flat_schedule = list(chain.from_iterable(
        entry.operator_schedule for entry in outbound_timetable_entries
    )) if outbound_timetable_entries.exists() else []

    outbound_groupedSchedule = []
    for code, group in groupby(outbound_flat_schedule):
        count = len(list(group))
        try:
            op = MBTOperator.objects.get(operator_code=code)
            name = op.operator_name
        except MBTOperator.DoesNotExist:
            name = code
        outbound_groupedSchedule.append({
            "code": code,
            "name": name,
            "colspan": count
        })

    if not outbound_timetableData:
        outbound_first_stop_name = None
        outbound_first_stop_times = []
    else:
        outbound_first_stop_name = list(outbound_timetableData.keys())[0]
        outbound_first_stop_times = outbound_timetableData[outbound_first_stop_name]["times"]

    current_updates = route_instance.service_updates.all().filter(end_date__gte=date.today())

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'full_route_num': full_route_num,
        'route': route_instance,
        'helperPermsData': helper_permissions,  # renamed for template match
        'allOperators': allOperators,
        'inboundTimetableData': inbound_timetableData if isinstance(inbound_timetableData, dict) else {},
        'inboundStops': list(inbound_timetableData.keys()) if isinstance(inbound_timetableData, dict) else [],
        'inboundGroupedSchedule': inbound_groupedSchedule,
        'inboundUniqueOperators': list({group['code'] for group in inbound_groupedSchedule}),
        'outboundTimetableData': outbound_timetableData if isinstance(outbound_timetableData, dict) else {},
        'outboundStops': list(outbound_timetableData.keys()) if isinstance(outbound_timetableData, dict) else [],
        'outboundGroupedSchedule': outbound_groupedSchedule,
        'outboundUniqueOperators': list({group['code'] for group in outbound_groupedSchedule}),
        'otherRoutes': route.objects.filter(linked_route__id=route_instance.id),
        'days': days,
        'selectedDay': selectedDay,
        'current_updates': current_updates,
        'transit_authority_details': getattr(operator.operator_details, 'transit_authority_details', None),
        'inbound_first_stop_name': inbound_first_stop_name,
        'inbound_first_stop_times': inbound_first_stop_times,
        'outbound_first_stop_name': outbound_first_stop_name,
        'outbound_first_stop_times': outbound_first_stop_times,
    }

    return render(request, 'route_detail.html', context)

def vehicles(request, operator_name):
    response = feature_enabled(request, "view_fleet")
    if response:
        return response
    
    withdrawn = request.GET.get('withdrawn')
    show_withdrawn = withdrawn and withdrawn.lower() == 'true'

    try:
        operator = MBTOperator.objects.get(operator_name=operator_name)
        def alphanum_key(fleet_number):
            return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', fleet_number or '')]

        if show_withdrawn:
            vehicles = list(fleet.objects.filter(operator=operator))
        else:
            vehicles = list(fleet.objects.filter(operator=operator, in_service=True))

        vehicles.sort(key=lambda v: alphanum_key(v.fleet_number))

        # Serialize the queryset
        serialized_vehicles = fleetSerializer(vehicles, many=True)

    except MBTOperator.DoesNotExist:
        return render(request, '404.html', status=404)

    regions = operator.region.all()

    helper_permissions = get_helper_permissions(request.user, operator)

    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': operator_name, 'url': f'/operator/{operator_name}/'}, {'name': 'Vehicles', 'url': f'/operator/{operator_name}/vehicles/'}]

    tabs = generate_tabs("vehicles", operator, show_withdrawn)

    def has_non_null_field(data_list, field):
        return any(item.get(field) not in [None, '', [], {}] for item in data_list)

    show_livery = has_non_null_field(serialized_vehicles.data, 'livery') or has_non_null_field(serialized_vehicles.data, 'colour')
    show_branding = (
        has_non_null_field(serialized_vehicles.data, 'branding') and
        has_non_null_field(serialized_vehicles.data, 'livery')
    )
    show_prev_reg = has_non_null_field(serialized_vehicles.data, 'prev_reg')
    show_name = has_non_null_field(serialized_vehicles.data, 'name')
    show_depot = has_non_null_field(serialized_vehicles.data, 'depot')
    show_features = has_non_null_field(serialized_vehicles.data, 'features')

    now = timezone.localtime(timezone.now())
    print(f"Current time (local): {now}")

    for item in serialized_vehicles.data:
        raw_date_value = item.get('last_trip_date')
        print(f"Raw date for vehicle {item.get('fleet_number')}: {raw_date_value}")

        if raw_date_value:
            if isinstance(raw_date_value, str):
                raw_date = parse_datetime(raw_date_value)
                if raw_date is None:
                    item['last_trip_display'] = ''
                    continue
            elif hasattr(raw_date_value, 'strftime'):
                raw_date = raw_date_value
            else:
                item['last_trip_display'] = ''
                continue

            # Convert raw_date to local time for display and comparison
            raw_date_local = timezone.localtime(raw_date)

            diff = now - raw_date_local

            if diff <= timedelta(days=1):
                item['last_trip_display'] = raw_date_local.strftime('%H:%M')
            elif raw_date_local.year != now.year:
                item['last_trip_display'] = raw_date_local.strftime('%d %b %Y')
            else:
                item['last_trip_display'] = raw_date_local.strftime('%d %b')
        else:
            item['last_trip_display'] = ''

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'vehicles': serialized_vehicles.data,
        'helper_permissions': helper_permissions,
        'tabs': tabs,
        'regions': regions,
        'show_livery': show_livery,
        'show_branding': show_branding,
        'show_prev_reg': show_prev_reg,
        'show_name': show_name,
        'show_depot': show_depot,
        'show_features': show_features,
    }
    return render(request, 'vehicles.html', context)

def vehicle_detail(request, operator_name, vehicle_id):
    response = feature_enabled(request, "view_vehicles")
    if response:
        return response
    
    try:
        operator = MBTOperator.objects.get(operator_name=operator_name)
        vehicle = fleet.objects.get(id=vehicle_id, operator=operator)
    except (MBTOperator.DoesNotExist, fleet.DoesNotExist):
        return render(request, '404.html', status=404)

    helper_permissions = get_helper_permissions(request.user, operator)

    today =  date.today()
    
    start_of_day = datetime.combine(today, time.min)
    end_of_day = datetime.combine(today, time.max)

    trips = Trip.objects.filter(
        trip_vehicle=vehicle,
        trip_start_at__range=(start_of_day, end_of_day)
    ).order_by('trip_start_at')

    trips_json = serialize('json', trips)

    print(f"Trips for vehicle {vehicle.fleet_number} on {today}: {[trip.trip_start_at for trip in trips]}")

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Vehicles', 'url': f'/operator/{operator_name}/vehicles#{vehicle.fleet_number}-{vehicle.operator.operator_code}'},
        {'name': f'{vehicle.fleet_number} - {vehicle.reg}', 'url': f'/operator/{operator_name}/vehicles/{vehicle_id}/'}
    ]

    tabs = generate_tabs("vehicles", operator)

    serialized_vehicle = fleetSerializer(vehicle)  # single object, no many=True

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'vehicle': serialized_vehicle.data,
        'helper_permissions': helper_permissions,
        'tabs': tabs,
        'trips': trips,
        'trips_json': trips_json,
    }
    return render(request, 'vehicle_detail.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def vehicle_edit(request, operator_name, vehicle_id):
    response = feature_enabled(request, "edit_vehicles")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    vehicle = get_object_or_404(fleet, id=vehicle_id, operator=operator)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Buses' not in userPerms and not request.user.is_superuser:
        return redirect(f'/operator/{operator_name}/vehicles/{vehicle_id}/')

    # Load related data needed for selects and checkboxes
    operators = MBTOperator.objects.all()
    types = vehicleType.objects.all()
    liveries_list = liverie.objects.all()
    allowed_operators = []

    helper_operator_ids = helper.objects.filter(
        helper=request.user,
        perms__perm_name="Move Buses"
    ).values_list("operator_id", flat=True)

    # 3. Combined queryset (owners + allowed helpers)
    allowed_operators = MBTOperator.objects.filter(
        Q(id__in=helper_operator_ids) | Q(owner=request.user)
    ).distinct()

    features_path = os.path.join(settings.MEDIA_ROOT, 'JSON', 'features.json')
    with open(features_path, 'r') as f:
        features_json = json.load(f)
        features_list = features_json.get("features", [])

    if request.method == "POST":
        # Update vehicle with form data

        # Checkboxes (exist if checked)
        vehicle.in_service = 'in_service' in request.POST
        vehicle.preserved = 'preserved' in request.POST
        vehicle.open_top = 'open_top' in request.POST

        # Text inputs
        vehicle.fleet_number = request.POST.get('fleet_number', '').strip()
        vehicle.reg = request.POST.get('reg', '').strip()
        vehicle.type_details = request.POST.get('type_details', '').strip()
        vehicle.length = request.POST.get('length', '').strip() or None
        vehicle.colour = request.POST.get('colour', '').strip()
        vehicle.branding = request.POST.get('branding', '').strip()
        vehicle.prev_reg = request.POST.get('prev_reg', '').strip()
        vehicle.depot = request.POST.get('depot', '').strip()
        vehicle.name = request.POST.get('name', '').strip()
        vehicle.notes = request.POST.get('notes', '').strip()
        vehicle.summary = request.POST.get('summary', '').strip()
        vehicle.last_modified_by = request.user

        # Foreign keys (ensure valid or None)
        try:
            vehicle.operator = MBTOperator.objects.get(id=request.POST.get('operator'))
        except MBTOperator.DoesNotExist:
            vehicle.operator = None

        loan_op = request.POST.get('loan_operator')
        if loan_op == "null" or not loan_op:
            vehicle.loan_operator = None
        else:
            try:
                vehicle.loan_operator = MBTOperator.objects.get(id=loan_op)
            except MBTOperator.DoesNotExist:
                vehicle.loan_operator = None

        try:
            vehicle.vehicleType = vehicleType.objects.get(id=request.POST.get('type'))
        except vehicleType.DoesNotExist:
            vehicle.vehicleType = None

        livery_id = request.POST.get('livery')
        if livery_id:
            try:
                vehicle.livery = liverie.objects.get(id=livery_id)
            except liverie.DoesNotExist:
                vehicle.livery = None
        else:
            vehicle.livery = None


        # Features JSON string stored in hidden input - parse and save as a comma-separated string or JSON field
        features_json = request.POST.get('features', '[]')
        try:
            features_selected = json.loads(features_json)
        except json.JSONDecodeError:
            features_selected = []

        vehicle.features = features_selected

        vehicle.save()

        messages.success(request, "Vehicle updated successfully.")
        # Redirect back to the vehicle detail page or wherever you want
        return redirect('vehicle_detail', operator_name=vehicle.operator.operator_name, vehicle_id=vehicle_id)

    else:
        # GET request — prepare context for the form

        # Parse features to a list for checkbox pre-check
        if vehicle.features:
            if isinstance(vehicle.features, str):
                features_selected = [f.strip() for f in vehicle.features.split(',')]
            elif isinstance(vehicle.features, list):
                features_selected = vehicle.features
            else:
                features_selected = []
        else:
            features_selected = []

        # user data (for your hidden input)
        user_data = [request.user]

        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator_name, 'url': f'/operator/{operator_name}/'},
            {'name': 'Vehicles', 'url': f'/operator/{operator_name}/vehicles/'},
            {'name': f'{vehicle.fleet_number} - {vehicle.reg}', 'url': f'/operator/{operator_name}/vehicles/{vehicle_id}/edit/'}
        ]

        tabs = []  # populate as needed or reuse your generate_tabs method

        context = {
            'fleetData': vehicle,
            'operatorData': operators,
            'typeData': types,
            'liveryData': liveries_list,
            'features': features_list,
            'userData': user_data,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
            'allowed_operators': allowed_operators,
        }
        return render(request, 'edit.html', context)
    
def send_discord_webhook_embed(title: str, description: str, color: int = 0x00ff00, fields: list = None, image_url: str = None):
    webhook_url = settings.DISCORD_FOR_SALE_WEBHOOK

    embed = {
        "title": title,
        "description": description,
        "color": color,
        "fields": fields or []
    }

    if image_url:
        embed["image"] = {"url": image_url}

    data = {
        "embeds": [embed]
    }
    

    response = requests.post(webhook_url, json=data)
    response.raise_for_status()

@login_required
@require_http_methods(["GET", "POST"])
def vehicle_sell(request, operator_name, vehicle_id):
    response = feature_enabled(request, "sell_vehicles")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    vehicle = get_object_or_404(fleet, id=vehicle_id, operator=operator)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Sell Buses' not in userPerms and not request.user.is_superuser:
        return redirect(f'/operator/{operator_name}/vehicles/{vehicle_id}/')

    if vehicle.for_sale:
        vehicle.for_sale = False
        message = "removed"
    else:
        vehicle.for_sale = True
        message = "listed"

        encoded_operator_name = quote(operator_name)

        title = "Vehicle Listed for Sale"
        description = f"**{operator.operator_name}** has listed {vehicle.fleet_number} - {vehicle.reg} for sale."
        fields = [
            {"name": "Fleet Number", "value": vehicle.fleet_number if hasattr(vehicle, 'fleet_number') else 'N/A', "inline": True},
            {"name": "Registration", "value": vehicle.reg if hasattr(vehicle, 'reg') else 'N/A', "inline": True},
            {"name": "Type", "value": vehicle.vehicleType.type_name if hasattr(vehicle, 'vehicleType') else 'N/A', "inline": False},
            {"name": "View", "value": f"https://mbtv2-test-dont-fucking-share-this-link.mybustimes.cc/operator/{encoded_operator_name}/vehicles/{vehicle.id}/?v={random.randint(1000,9999)}", "inline": False}
        ]
        send_discord_webhook_embed(title, description, color=0xFFA500, fields=fields, image_url=f"https://mbtv2-test-dont-fucking-share-this-link.mybustimes.cc/operator/vehicle_image/{vehicle.id}/?v={random.randint(1000,9999)}")  # Orange


    vehicle.save()

    messages.success(request, f"Vehicle {message} for sale successfully.")
    # Redirect back to the vehicle detail page or wherever you want
    return redirect('vehicle_detail', operator_name=operator_name, vehicle_id=vehicle_id)

def generate_vehicle_card(fleet_number, reg, vehicle_type, status):
    width, height = 750, 100  # 8:1 ratio
    bg_color = "#00000000"
    padding = 0

    img = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "OpenSans-Bold.ttf")
    font_large = ImageFont.truetype(font_path, size=45)
    font_small = ImageFont.truetype(font_path, size=25)

    # Draw shadowed text function
    def draw_shadowed_text(pos, text, font, fill, shadowcolor=(0,0,0, 250)):
        x, y = pos
        # Draw shadow slightly offset
        #draw.text((x+3, y+3), text, font=font, fill=shadowcolor)
        # Draw main text
        draw.text((x, y), text, font=font, fill=fill)

    # Fleet number and reg, bold and white with shadow
    draw_shadowed_text((10, 0), f"{fleet_number} - {reg}", font_large, "#ffffff")

    # Vehicle type smaller and lighter (using white with some transparency)
    draw_shadowed_text((10, 50), vehicle_type, font_small, "#eeeeee")

    # Status box behind status text
    status_text = status.upper()
    bbox = draw.textbbox((0,0), status_text, font=font_large)
    status_width = bbox[2] - bbox[0]
    status_height = bbox[3] - bbox[1]

    box_padding = 10
    box_x0 = width - status_width - box_padding * 2 - 10
    box_y0 = 0 + 10 
    box_x1 = width - 10
    box_y1 = 0 + status_height + 30 

    # Rounded rectangle background (simple rectangle here)
    status_bg_color = (0, 128, 0, 200) if status.lower() == "for sale" else (200, 0, 0, 200)
    draw.rounded_rectangle([box_x0, box_y0, box_x1, box_y1], radius=12, fill=status_bg_color)

    # Status text in white on top
    draw.text((box_x0 + box_padding, 5), status_text, font=font_large, fill="white")

    return img

def vehicle_card_image(request, vehicle_id):
    vehicle = get_object_or_404(fleet, id=vehicle_id)
    img = generate_vehicle_card(vehicle.fleet_number, vehicle.reg, vehicle.vehicleType.type_name, "For Sale" if vehicle.for_sale else "Not for Sale")

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return HttpResponse(buffer, content_type='image/png')

def vehicle_status_preview(request, vehicle_id):
    vehicle = get_object_or_404(fleet, id=vehicle_id)

    if not vehicle.for_sale:
        link = "Sold" if vehicle.for_sale else "Not for Sale"
    else:
        link = f"https://mybustimes.cc/for_sale#vehicle_{vehicle.id}"

    description = (
        f"Reg: {vehicle.reg or 'N/A'}\n"
        f"Fleet Number: {vehicle.fleet_number or 'N/A'}\n"
        f"Type: {getattr(vehicle.vehicleType, 'type_name', 'N/A')}\n\n"
        f"{link}\n\n"
    )

    embed = {
        "id": str(vehicle.id),
        "title": "Vehicle Listed for Sale",
        "description": description,
        "color": 0x00FF00 if vehicle.for_sale else 0xFF0000,
        "image_url": f"https://mbt1.mybustimes.cc/operator/vehicle_image/{vehicle.id}?v={random.randint(1000,9999)}",
        "breadcrumbs": [
            {'name': 'Home', 'url': '/'},
            {'name': 'For Sale', 'url': '/for_sale/'},
        ]
    }

    return render(request, "discord_preview.html", embed)

def duties(request, operator_name):
    response = feature_enabled(request, "view_boards")
    if response:
        return response
    
    is_running_board = 'running-boards' in request.resolver_match.route

    if is_running_board:
        title = "Running Board"
        titles = "Running Boards"
        board_type = 'running-boards'
    else:
        title = "Duty"
        titles = "Duties"
        board_type = 'duty'

    try:
        operator = MBTOperator.objects.get(operator_name=operator_name)
        duties_queryset = duty.objects.filter(duty_operator=operator, board_type=board_type).prefetch_related('duty_day').order_by('duty_name')
    except MBTOperator.DoesNotExist:
        return render(request, '404.html', status=404)

    userPerms = get_helper_permissions(request.user, operator)

    # Group duties by day name
    grouped_duties = defaultdict(list)
    for d in duties_queryset:
        for day in d.duty_day.all():
            grouped_duties[day.name].append(d)

    # Optional: sort by weekday order
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    grouped_duties_ordered = {day: grouped_duties[day] for day in weekday_order if day in grouped_duties}

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': titles, 'url': f'/operator/{operator_name}/{board_type}/'}
    ]

    tabs = generate_tabs("duties", operator)

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'grouped_duties': grouped_duties_ordered,
        'tabs': tabs,
        'all_duties': duties_queryset,
        'user_perms': userPerms,
        'title': title,
        'titles': titles,
        'add_perm': f"Add {title}",
    }
    return render(request, 'duties.html', context)

def duty_detail(request, operator_name, duty_id):
    response = feature_enabled(request, "view_boards")
    if response:
        return response
    
    is_running_board = 'running-boards' in request.resolver_match.route

    if is_running_board:
        title = "Running Board"
        titles = "Running Boards"
        board_type = 'running-boards'
    else:
        title = "Duty"
        titles = "Duties"
        board_type = "duty"

    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    duty_instance = get_object_or_404(duty, id=duty_id, duty_operator=operator)

    # Get all vehicles for this operator
    vehicles = fleet.objects.filter(operator=operator).order_by('fleet_number')

    userPerms = get_helper_permissions(request.user, operator)

    trips = dutyTrip.objects.filter(duty=duty_instance).order_by('start_time')

    # Get all days associated with this duty
    days = duty_instance.duty_day.all()

    # Breadcrumbs
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Duties', 'url': f'/operator/{operator_name}/duties/'},
        {'name': duty_instance.duty_name or 'Duty Details', 'url': f'/operator/{operator_name}/duty/{duty_id}/'}
    ]

    tabs = generate_tabs("duties", operator)

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'duty': duty_instance,
        'trips': trips,
        'vehicles': vehicles,
        'days': days,
        'tabs': tabs,
        'user_perms': userPerms,
    }
    return render(request, 'duty_detail.html', context)

def wrap_text(text, max_chars):
    if not text:
        return [""]
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]

def generate_pdf(request, operator_name, duty_id):
    try:
        duty_instance = get_object_or_404(duty.objects.select_related('duty_operator'), id=duty_id)
        trips = dutyTrip.objects.filter(duty=duty_instance).order_by('start_time')

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="duty.pdf"'

        p = canvas.Canvas(response, pagesize=A4)
        width, height = A4

        # Header data
        y = 725
        xColumn = 5
        columnSpacing = 195
        columnBottom = 25
        columnTop = 725

        details = duty_instance.duty_details or {}
        start_time = details.get('logon_time', 'N/A')
        end_time = details.get('logoff_time', 'N/A')
        brake_time = details.get('brake_times', '')
        brake_parts = brake_time.split(' | ')
        if len(brake_parts) > 4:
            brake_parts.insert(4, '\n')
        formatted_brake_time = ' | '.join(brake_parts).replace(' | \n | ', '\n')

        # --- Template Lines ---
        header_top_y = 800
        header_bottom_y = 750
        vertical_split_x = width / 2

        # Draw horizontal header separators
        p.setStrokeColor(colors.black)
        p.setLineWidth(1)
        p.line(0, header_top_y, width, header_top_y)
        p.line(0, header_bottom_y, width, header_bottom_y)

        # Draw vertical divider line between the two horizontal lines
        p.line(vertical_split_x, header_bottom_y, vertical_split_x, header_top_y)

        # --- Header Content ---
        # Operator title
        p.setFont("Helvetica-Bold", 24)
        p.drawCentredString(width / 2, header_top_y + 10, operator_name)

        # Left side: Duty and Day
        p.setFont("Helvetica-Bold", 16)
        p.drawString(10, 780, f"Duty: {duty_instance.duty_name}")

        p.setFont("Helvetica", 12)
        if duty_instance.duty_day.exists():
            day_names_list = [day.name for day in duty_instance.duty_day.all()]
            all_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
            weekdays = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
            weekends = {"Saturday", "Sunday"}

            day_names_set = set(day_names_list)

            if day_names_set == all_days:
                day_names = "Every Day"
            elif day_names_set == weekdays:
                day_names = "Weekdays"
            elif day_names_set == weekends:
                day_names = "Weekends"
            else:
                day_names = ", ".join(day_names_list)
        else:
            day_names = "Unknown"

        p.drawString(10, 765, f"Day(s): {day_names}")


        # Right side: Start/End and Brake times
        p.setFont("Helvetica", 12)
        p.drawString(vertical_split_x + 10, 785, f"Start Time: {start_time} - End Time: {end_time}")

        p.setFont("Helvetica-Bold", 12)
        p.drawString(vertical_split_x + 10, 765, "Brake Times:")
        p.setFont("Helvetica", 12)
        p.drawString(vertical_split_x + 10, 752, formatted_brake_time)

        # Trips
        index = 0
        for trip in trips:
            from_dest = trip.start_at or ''
            to_dest = trip.end_at or ''
            route = trip.route or ''
            depart_time = trip.start_time.strftime('%H:%M') if trip.start_time else ''
            arrive_time = trip.end_time.strftime('%H:%M') if trip.end_time else ''

            label_from = "From: "
            label_to = "To: "

            from_lines = wrap_text(from_dest, 28)
            to_lines = wrap_text(to_dest, 28)

            line_count = len(from_lines) + len(to_lines) + 2
            total_height = (line_count * 15) + 5 + 20

            if y - total_height < columnBottom:
                if xColumn + columnSpacing < width - columnSpacing:
                    xColumn += columnSpacing
                    y = columnTop
                else:
                    p.showPage()
                    xColumn = 5
                    y = columnTop

            p.setFont("Helvetica-Bold", 11)
            p.drawString(xColumn, y, label_from)
            p.setFont("Helvetica", 10)
            p.drawString(xColumn + 45, y, from_lines[0])
            y -= 10
            for line in from_lines[1:]:
                p.drawString(xColumn, y, line)
                y -= 10

            p.setFont("Helvetica-Bold", 11)
            p.drawString(xColumn, y, label_to)
            p.setFont("Helvetica", 10)
            p.drawString(xColumn + 45, y, to_lines[0])
            y -= 10
            for line in to_lines[1:]:
                p.drawString(xColumn, y, line)
                y -= 10

            y -= 10
            p.setFont("Helvetica-Bold", 11)
            p.drawString(xColumn, y, f"Route:")
            p.setFont("Helvetica", 10)
            p.drawString(xColumn + 35, y, route)

            y -= 15
            p.drawString(xColumn, y, f"Depart: {depart_time} - Arrive: {arrive_time}")
            p.drawString(xColumn + 175, y, str(index + 1))

            y -= 5
            p.setStrokeColor(colors.black)
            p.setLineWidth(1)
            p.line(xColumn, y, xColumn + 190, y)
            y -= 20

            index += 1

        p.showPage()
        p.save()
        return response

    except Exception as e:
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)

@login_required
@require_http_methods(["GET", "POST"])
def duty_add(request, operator_name):
    response = feature_enabled(request, "add_boards")
    if response:
        return response
    
    is_running_board = 'running-boards' in request.resolver_match.route

    if is_running_board:
        title = "Running Board"
        titles = "Running Boards"
        board_type = 'running-boards'
    else:
        title = "Duty"
        titles = "Duties"
        board_type = "duty"

    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add a duty for this operator.")
        return redirect(f'/operator/{operator_name}/duties/')

    days = dayType.objects.all()

    if request.method == "POST":
        duty_name = request.POST.get('duty_name')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        brake_times = request.POST.getlist('brake_times')
        selected_days = request.POST.getlist('duty_day')  # Handle multiple dayType IDs
        if is_running_board:
            board_type = 'running-boards'
        else:
            board_type = 'duty'

        formatted_brakes = " | ".join(brake_times)

        duty_details = {
            "logon_time": start_time,
            "logoff_time": end_time,
            "brake_times": formatted_brakes
        }

        duty_instance = duty.objects.create(
            duty_name=duty_name,
            duty_operator=operator,
            duty_details=duty_details,
            board_type=board_type
        )

        # Set ManyToManyField values
        if selected_days:
            duty_instance.duty_day.set(selected_days)

        messages.success(request, "Duty added successfully.")
        return redirect(f'/operator/{operator_name}/duties/add/trips/{duty_instance.id}/')

    else:
        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator_name, 'url': f'/operator/{operator_name}/'},
            {'name': titles, 'url': f'/operator/{operator_name}/{board_type}/'},
            {'name': f'Add {title}', 'url': f'/operator/{operator_name}/{board_type}/add/'}
        ]

        tabs = generate_tabs("duties", operator)

        context = {
            'operator': operator,
            'days': days,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
            'is_running_board': is_running_board,  # Pass this to your template if needed
            'titles': titles,  # Pass the plural title for the duties/running boards
            'title': title,  # Pass the singular title for the duty/running board
        }
        return render(request, 'add_duty.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def duty_add_trip(request, operator_name, duty_id):
    response = feature_enabled(request, "add_boards")
    if response:
        return response
    
    is_running_board = 'running-boards' in request.resolver_match.route

    if is_running_board:
        title = "Running Board"
        titles = "Running Boards"
        board_type = 'running-boards'
    else:
        title = "Duty"
        titles = "Duties"
        board_type = "duty"

    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    userPerms = get_helper_permissions(request.user, operator)

    duty_instance = get_object_or_404(duty, id=duty_id, duty_operator=operator)

    if request.user != operator.owner and 'Add Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add a duty for this operator.")
        return redirect(f'/operator/{operator_name}/duties/')

    if request.method == "POST":
        # Get lists of trip inputs (all arrays)
        route_nums = request.POST.getlist('route_num[]')
        start_times = request.POST.getlist('start_time[]')
        end_times = request.POST.getlist('end_time[]')
        start_ats = request.POST.getlist('start_at[]')
        end_ats = request.POST.getlist('end_at[]')

        # Validate lengths are equal
        if not (len(route_nums) == len(start_times) == len(end_times) == len(start_ats) == len(end_ats)):
            messages.error(request, "Mismatch in trip input lengths.")
            return redirect(request.path)

        trips_created = 0
        for i in range(len(route_nums)):
            # Parse times from strings (if needed)
            try:
                start_time = datetime.strptime(start_times[i], '%H:%M').time()
                end_time = datetime.strptime(end_times[i], '%H:%M').time()
            except ValueError:
                messages.error(request, f"Invalid time format for trip {i+1}.")
                continue

            # Create dutyTrip instance
            dutyTrip.objects.create(
                duty=duty_instance,
                route=route_nums[i],
                start_time=start_time,
                end_time=end_time,
                start_at=start_ats[i],
                end_at=end_ats[i]
            )
            trips_created += 1

        messages.success(request, f"Successfully added {trips_created} trip(s) to duty '{duty_instance.duty_name}'.")
        return redirect(f'/operator/{operator_name}/duties/')

    else:
        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator_name, 'url': f'/operator/{operator_name}/'},
            {'name': {titles}, 'url': f'/operator/{operator_name}/{board_type}/'},
            {'name': duty_instance.duty_name, 'url': f'/operator/{operator_name}/{board_type}/{duty_id}/'},
            {'name': 'Add Trips', 'url': request.path}
        ]

        tabs = generate_tabs("duties", operator)

        context = {
            'operator': operator,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
            'duty_instance': duty_instance,  # renamed for clarity with your template
            'title': title,  # Pass the singular title for the duty/running board
            'titles': titles,  # Pass the plural title for the duties/running boards
            'is_running_board': is_running_board,  # Pass this to your template if needed
        }
        return render(request, 'add_duty_trip.html', context)
    
@login_required
@require_http_methods(["GET", "POST"])
def duty_edit_trips(request, operator_name, duty_id):
    response = feature_enabled(request, "edit_boards")
    if response:
        return response
    
    is_running_board = 'running-boards' in request.resolver_match.route

    if is_running_board:
        title = "Running Board"
        titles = "Running Boards"
        board_type = 'running-boards'
    else:
        title = "Duty"
        titles = "Duties"
        board_type = "duty"

    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    userPerms = get_helper_permissions(request.user, operator)
    duty_instance = get_object_or_404(duty, id=duty_id, duty_operator=operator)

    if request.user != operator.owner and 'Add Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit trips for this duty.")
        return redirect(f'/operator/{operator_name}/duties/')

    if request.method == "POST":
        # Get posted trip data
        route_nums = request.POST.getlist('route_num[]')
        start_times = request.POST.getlist('start_time[]')
        end_times = request.POST.getlist('end_time[]')
        start_ats = request.POST.getlist('start_at[]')
        end_ats = request.POST.getlist('end_at[]')

        if not (len(route_nums) == len(start_times) == len(end_times) == len(start_ats) == len(end_ats)):
            messages.error(request, "Mismatch in trip input lengths.")
            return redirect(request.path)

        # Clear previous trips
        duty_instance.duty_trips.all().delete()

        trips_created = 0
        for i in range(len(route_nums)):
            try:
                start_time = datetime.strptime(start_times[i], '%H:%M').time()
                end_time = datetime.strptime(end_times[i], '%H:%M').time()
            except ValueError:
                messages.error(request, f"Invalid time format for trip {i+1}.")
                continue

            dutyTrip.objects.create(
                duty=duty_instance,
                route=route_nums[i],
                start_time=start_time,
                end_time=end_time,
                start_at=start_ats[i],
                end_at=end_ats[i]
            )
            trips_created += 1

        messages.success(request, f"Updated {trips_created} trip(s) for duty '{duty_instance.duty_name}'.")
        return redirect(f'/operator/{operator_name}/duties/')

    else:
        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator_name, 'url': f'/operator/{operator_name}/'},
            {'name': titles, 'url': f'/operator/{operator_name}/{board_type}/'},
            {'name': duty_instance.duty_name, 'url': f'/operator/{operator_name}/{board_type}/{duty_id}/'},
            {'name': 'Edit Trips', 'url': request.path}
        ]

        tabs = generate_tabs("duties", operator)

        context = {
            'operator': operator,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
            'duty_instance': duty_instance,
        }
        return render(request, 'edit_duty_trip.html', context)
    
@login_required
@require_http_methods(["GET", "POST"])
def duty_delete(request, operator_name, duty_id):
    response = feature_enabled(request, "delete_boards")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    userPerms = get_helper_permissions(request.user, operator)
    duty_instance = get_object_or_404(duty, id=duty_id, duty_operator=operator)

    if request.user != operator.owner and 'Delete Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this duty.")
        return redirect(f'/operator/{operator_name}/duties/')

    duty_instance.delete()
    messages.success(request, f"Deleted duty '{duty_instance.duty_name}'.")
    return redirect(f'/operator/{operator_name}/duties/')

@login_required
@require_http_methods(["GET", "POST"])
def duty_edit(request, operator_name, duty_id):
    response = feature_enabled(request, "edit_boards")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    userPerms = get_helper_permissions(request.user, operator)
    duty_instance = get_object_or_404(duty, id=duty_id, duty_operator=operator)

    if request.user != operator.owner and 'Edit Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this duty for this operator.")
        return redirect(f'/operator/{operator_name}/duties/')

    days = dayType.objects.all()

    if request.method == "POST":
        duty_name = request.POST.get('duty_name')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        brake_times = request.POST.getlist('brake_times')
        selected_days = request.POST.getlist('duty_day')

        # Format break times
        formatted_brakes = " | ".join(brake_times)

        # Update the duty instance
        duty_instance.duty_name = duty_name
        duty_instance.duty_details = {
            "logon_time": start_time,
            "logoff_time": end_time,
            "brake_times": formatted_brakes
        }

        duty_instance.save()

        # Update ManyToMany field for days
        if selected_days:
            duty_instance.duty_day.set(selected_days)
        else:
            duty_instance.duty_day.clear()

        messages.success(request, "Duty updated successfully.")
        return redirect(f'/operator/{operator_name}/duties/')

    else:
        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator_name, 'url': f'/operator/{operator_name}/'},
            {'name': 'Duties', 'url': f'/operator/{operator_name}/duties/'},
            {'name': f"Edit {duty_instance.duty_name}", 'url': f'/operator/{operator_name}/duties/edit/{duty_instance.id}/'}
        ]

        tabs = generate_tabs("duties", operator)

        context = {
            'operator': operator,
            'days': days,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
            'duty_instance': duty_instance,
        }
        return render(request, 'edit_duty.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def log_trip(request, operator_name, vehicle_id):
    response = feature_enabled(request, "log_trips")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    vehicle = get_object_or_404(fleet, id=vehicle_id, operator=operator)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Log Trips' not in userPerms and not request.user.is_superuser:
        return redirect(f'/operator/{operator_name}/vehicles/{vehicle_id}/')

    # Always define both forms
    timetable_form = TripFromTimetableForm(operator=operator, vehicle=vehicle)
    manual_form = ManualTripForm(operator=operator, vehicle=vehicle)

    if request.method == 'POST':
        if 'timetable_submit' in request.POST:
            timetable_form = TripFromTimetableForm(request.POST, operator=operator, vehicle=vehicle)
            print("Timetable form submitted")  # Debugging
            if timetable_form.is_valid():
                timetable_form.save()
                return redirect('vehicle_detail', operator_name=operator_name, vehicle_id=vehicle_id)
        elif 'manual_submit' in request.POST:
            manual_form = ManualTripForm(request.POST, operator=operator, vehicle=vehicle)
            print("Manual form submitted")  # Debugging
            if manual_form.is_valid():
                manual_form.save()
                return redirect('vehicle_detail', operator_name=operator_name, vehicle_id=vehicle_id)


    context = {
        'operator': operator,
        'vehicle': vehicle,
        'user_permissions': userPerms,
        'timetable_form': timetable_form,
        'manual_form': manual_form,
    }

    return render(request, 'log_trip.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_edit(request, operator_name):
    response = feature_enabled(request, "edit_operators")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)

    # Make these available to both POST and GET
    groups = group.objects.filter(Q(group_owner=request.user) | Q(private=False))
    organisations = organisation.objects.filter(organisation_owner=request.user)
    operator_types = operatorType.objects.filter(published=True).order_by('operator_type_name')

    regions = region.objects.all().order_by('region_country', 'region_name')
    grouped_regions = defaultdict(list)
    for r in regions:
        grouped_regions[r.region_country].append(r)
    regionData = dict(grouped_regions)

    if request.user != operator.owner and not request.user.is_superuser:
        return redirect(f'/operator/{operator_name}')

    if request.method == "POST":
        operator.operator_name = request.POST.get('operator_name', '').strip()
        operator.operator_code = request.POST.get('operator_code', '').strip()
        region_ids = request.POST.getlist('operator_region')
        operator.region.set(region_ids)

        if request.POST.get('group', None) == "":
            group_instance = None
        else:
            try:
                group_instance = group.objects.get(id=request.POST.get('group'))
            except group.DoesNotExist:
                group_instance = None

        operator.group = group_instance

        operator_details = {
            'website': request.POST.get('website', '').strip(),
            'twitter': request.POST.get('twitter', '').strip(),
            'game': request.POST.get('game', '').strip(),
            'type': request.POST.get('type', '').strip(),
            'transit_authorities': request.POST.get('transit_authorities', '').strip(),
        }

        operator.operator_details = operator_details
        operator.save()

        messages.success(request, "Operator updated successfully.")
        return redirect(f'/operator/{operator_name}')

    else:
        # GET request — prepare context for the form
        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator_name, 'url': f'/operator/{operator_name}/'},
            {'name': 'Edit Operator', 'url': f'/operator/{operator_name}/edit/'}
        ]

        tabs = generate_tabs("routes", operator)

        context = {
            'operator': operator,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
            'groups': groups,
            'organisations': organisations,
            'regionData': regionData,
            'operator_types': operator_types,
        }
        return render(request, 'edit_operator.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def vehicle_add(request, operator_name):
    response = feature_enabled(request, "add_vehicles")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Buses' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add a bus for this operator.")
        return redirect(f'/operator/{operator_name}/vehicles/')

    # Load dropdown/related data
    operators = MBTOperator.objects.all()
    types = vehicleType.objects.all()
    liveries_list = liverie.objects.all()
    allowed_operators = []

    helper_operator_ids = helper.objects.filter(
        helper=request.user,
        perms__perm_name="Buy Buses"
    ).values_list("operator_id", flat=True)

    # 3. Combined queryset (owners + allowed helpers)
    allowed_operators = MBTOperator.objects.filter(
        Q(id__in=helper_operator_ids) | Q(owner=request.user)
    ).distinct()

    features_path = os.path.join(settings.MEDIA_ROOT, 'JSON', 'features.json')
    with open(features_path, 'r') as f:
        features_json = json.load(f)
        features_list = features_json.get("features", [])

    if request.method == "POST":
        vehicle = fleet()  # <--- Create a new vehicle instance

        # Checkbox values
        vehicle.in_service = 'in_service' in request.POST
        vehicle.preserved = 'preserved' in request.POST
        vehicle.open_top = 'open_top' in request.POST

        # Text fields
        vehicle.fleet_number = request.POST.get('fleet_number', '').strip()
        vehicle.reg = request.POST.get('reg', '').strip()
        vehicle.type_details = request.POST.get('type_details', '').strip()
        vehicle.length = request.POST.get('length', '').strip() or None
        vehicle.colour = request.POST.get('colour', '').strip()
        vehicle.branding = request.POST.get('branding', '').strip()
        vehicle.prev_reg = request.POST.get('prev_reg', '').strip()
        vehicle.depot = request.POST.get('depot', '').strip()
        vehicle.name = request.POST.get('name', '').strip()
        vehicle.notes = request.POST.get('notes', '').strip()
        vehicle.summary = request.POST.get('summary', '').strip()

        # Foreign key lookups
        try:
            vehicle.operator = MBTOperator.objects.get(id=request.POST.get('operator'))
        except MBTOperator.DoesNotExist:
            vehicle.operator = operator  # fallback to current operator

        loan_op = request.POST.get('loan_operator')
        if loan_op == "null" or not loan_op:
            vehicle.loan_operator = None
        else:
            try:
                vehicle.loan_operator = MBTOperator.objects.get(id=loan_op)
            except MBTOperator.DoesNotExist:
                vehicle.loan_operator = None

        try:
            vehicle.vehicleType = vehicleType.objects.get(id=request.POST.get('type'))
        except vehicleType.DoesNotExist:
            vehicle.vehicleType = None

        try:
            vehicle.livery = liverie.objects.get(id=request.POST.get('livery'))
        except liverie.DoesNotExist:
            vehicle.livery = None

        # Features (as JSON)
        try:
            features_selected = json.loads(request.POST.get('features', '[]'))
        except json.JSONDecodeError:
            features_selected = []

        vehicle.features = features_selected
        vehicle.save()

        messages.success(request, "Vehicle added successfully.")
        return redirect(f'/operator/{operator_name}/vehicles/')

    else:
        # GET: Prepare blank form
        vehicle = fleet()  # Blank for add form

        features_selected = []

        user_data = [request.user]

        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator_name, 'url': f'/operator/{operator_name}/'},
            {'name': 'Vehicles', 'url': f'/operator/{operator_name}/vehicles/'},
            {'name': 'Add Vehicle', 'url': f'/operator/{operator_name}/vehicles/add/'}
        ]

        tabs = []

        context = {
            'operator_current': operator,
            'fleetData': vehicle,
            'operatorData': operators,
            'typeData': types,
            'liveryData': liveries_list,
            'features': features_list,
            'userData': user_data,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
            'allowed_operators': allowed_operators,
        }
        return render(request, 'add.html', context)
    
@login_required
@require_http_methods(["GET", "POST"])
def vehicle_mass_add(request, operator_name):
    response = feature_enabled(request, "mass_add_vehicles")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Buses' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add a bus for this operator.")
        return redirect(f'/operator/{operator_name}/vehicles/')

    # Load dropdown/related data
    operators = MBTOperator.objects.all()
    types = vehicleType.objects.all()
    liveries_list = liverie.objects.all()

    features_path = os.path.join(settings.MEDIA_ROOT, 'JSON', 'features.json')
    with open(features_path, 'r') as f:
        features_json = json.load(f)
        features_list = features_json.get("features", [])

    if request.method == "POST":
        try:
            number_of_vehicles = int(request.POST.get("number_of_vehicles", 1))
        except ValueError:
            number_of_vehicles = 1

        # Common field values (same for all vehicles)
        in_service = 'in_service' in request.POST
        preserved = 'preserved' in request.POST
        open_top = 'open_top' in request.POST
        type_details = request.POST.get('type_details', '').strip()
        length = request.POST.get('length', '').strip() or None
        colour = request.POST.get('colour', '').strip()
        branding = request.POST.get('branding', '').strip()
        prev_reg = request.POST.get('prev_reg', '').strip()
        depot = request.POST.get('depot', '').strip()
        name = request.POST.get('name', '').strip()
        notes = request.POST.get('notes', '').strip()
        summary = request.POST.get('summary', '').strip()

        try:
            operator_fk = MBTOperator.objects.get(id=request.POST.get('operator'))
        except MBTOperator.DoesNotExist:
            operator_fk = operator  # fallback to current operator

        loan_op = request.POST.get('loan_operator')
        if loan_op == "null" or not loan_op:
            loan_operator_fk = None
        else:
            try:
                loan_operator_fk = MBTOperator.objects.get(id=loan_op)
            except MBTOperator.DoesNotExist:
                loan_operator_fk = None

        try:
            type_fk = vehicleType.objects.get(id=request.POST.get('type'))
        except vehicleType.DoesNotExist:
            type_fk = None

        try:
            livery_fk = liverie.objects.get(id=request.POST.get('livery'))
        except liverie.DoesNotExist:
            livery_fk = None

        try:
            features_selected = json.loads(request.POST.get('features', '[]'))
        except json.JSONDecodeError:
            features_selected = []

        created_count = 0
        for i in range(1, number_of_vehicles + 1):
            fleet_number = request.POST.get(f'fleet_number_{i}', '').strip()
            reg = request.POST.get(f'reg_{i}', '').strip()
            if not fleet_number or not reg:
                continue  # skip incomplete rows

            vehicle = fleet()
            vehicle.fleet_number = fleet_number
            vehicle.reg = reg
            vehicle.in_service = in_service
            vehicle.preserved = preserved
            vehicle.open_top = open_top
            vehicle.type_details = type_details
            vehicle.length = length
            vehicle.colour = colour
            vehicle.branding = branding
            vehicle.prev_reg = prev_reg
            vehicle.depot = depot
            vehicle.name = name
            vehicle.notes = notes
            vehicle.summary = summary
            vehicle.operator = operator_fk
            vehicle.loan_operator = loan_operator_fk
            vehicle.vehicleType = type_fk
            vehicle.livery = livery_fk
            vehicle.features = features_selected

            vehicle.save()
            created_count += 1

        messages.success(request, f"{created_count} vehicle(s) added successfully.")
        return redirect(f'/operator/{operator_name}/vehicles/')


    else:
        # GET: Prepare blank form
        vehicle = fleet()  # Blank for add form

        features_selected = []

        user_data = [request.user]

        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator_name, 'url': f'/operator/{operator_name}/'},
            {'name': 'Vehicles', 'url': f'/operator/{operator_name}/vehicles/'},
            {'name': 'Add Vehicle', 'url': f'/operator/{operator_name}/vehicles/add/'}
        ]

        tabs = []

        context = {
            'fleetData': vehicle,
            'operator_current': operator,
            'operatorData': operators,
            'typeData': types,
            'liveryData': liveries_list,
            'features': features_list,
            'userData': user_data,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
        }
        return render(request, 'mass_add.html', context)
    
@login_required
@require_http_methods(["GET", "POST"])
def vehicle_mass_edit(request, operator_name):
    response = feature_enabled(request, "mass_edit_vehicles")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)

    userPerms = get_helper_permissions(request.user, operator)
    if request.user != operator.owner and 'Mass Edit Buses' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit vehicles for this operator.")
        return redirect(f'/operator/{operator_name}/vehicles/')

    # Parse vehicle IDs from ?ids= query param
    vehicle_ids_str = request.GET.get("ids", "")
    vehicle_ids = [int(id.strip()) for id in vehicle_ids_str.split(",") if id.strip().isdigit()]
    vehicles = list(fleet.objects.filter(id__in=vehicle_ids, operator=operator))

    if not vehicles:
        messages.error(request, "No valid vehicles selected for editing.")
        return redirect(f'/operator/{operator_name}/vehicles/')

    # Dropdown data
    operators = MBTOperator.objects.all()
    types = vehicleType.objects.all()
    liveries_list = liverie.objects.all()

    features_path = os.path.join(settings.MEDIA_ROOT, 'JSON', 'features.json')
    with open(features_path, 'r') as f:
        features_json = json.load(f)
        features_list = features_json.get("features", [])

    if request.method == "POST":
        updated_count = 0
        for i, vehicle in enumerate(vehicles, start=1):
            # Get updated fields for this vehicle
            vehicle.fleet_number = request.POST.get(f'fleet_number_{i}', vehicle.fleet_number).strip()
            vehicle.reg = request.POST.get(f'reg_{i}', vehicle.reg).strip()

            vehicle.in_service = 'in_service' in request.POST
            vehicle.preserved = 'preserved' in request.POST
            vehicle.open_top = 'open_top' in request.POST
            vehicle.type_details = request.POST.get('type_details', '').strip()
            vehicle.length = request.POST.get('length', '').strip() or None
            vehicle.colour = request.POST.get('colour', '').strip()
            vehicle.branding = request.POST.get('branding', '').strip()
            vehicle.prev_reg = request.POST.get('prev_reg', '').strip()
            vehicle.depot = request.POST.get('depot', '').strip()
            vehicle.name = request.POST.get('name', '').strip()
            vehicle.notes = request.POST.get('notes', '').strip()
            vehicle.summary = request.POST.get('summary', '').strip()

            # Foreign Keys
            try:
                vehicle.operator = MBTOperator.objects.get(id=request.POST.get('operator'))
            except MBTOperator.DoesNotExist:
                pass

            loan_op = request.POST.get('loan_operator')
            if loan_op == "null" or not loan_op:
                vehicle.loan_operator = None
            else:
                try:
                    vehicle.loan_operator = MBTOperator.objects.get(id=loan_op)
                except MBTOperator.DoesNotExist:
                    vehicle.loan_operator = None

            try:
                vehicle.vehicleType = vehicleType.objects.get(id=request.POST.get('type'))
            except vehicleType.DoesNotExist:
                vehicle.vehicleType = None

            try:
                vehicle.livery = liverie.objects.get(id=request.POST.get('livery'))
            except liverie.DoesNotExist:
                vehicle.livery = None

            try:
                features_selected = json.loads(request.POST.get('features', '[]'))
                vehicle.features = features_selected
            except json.JSONDecodeError:
                pass

            vehicle.save()
            updated_count += 1

        messages.success(request, f"{updated_count} vehicle(s) updated successfully.")
        return redirect(f'/operator/{operator_name}/vehicles/')

    else:
        # GET: pre-fill form with first vehicle for shared fields
        context = {
            'fleetData': vehicles[0],  # Used for shared fields
            'vehicles': vehicles,
            'operatorData': operators,
            'typeData': types,
            'liveryData': liveries_list,
            'features': features_list,
            'userData': [request.user],
            'vehicle_count': len(vehicles),
            'breadcrumbs': [
                {'name': 'Home', 'url': '/'},
                {'name': operator_name, 'url': f'/operator/{operator_name}/'},
                {'name': 'Vehicles', 'url': f'/operator/{operator_name}/vehicles/'},
                {'name': 'Mass Edit', 'url': request.path},
            ],
            'tabs': [],
        }
        return render(request, 'mass_edit.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def vehicle_select_mass_edit(request, operator_name):
    response = feature_enabled(request, "mass_edit_vehicles")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Mass Edit Buses' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit vehicles for this operator.")
        return redirect(f'/operator/{operator_name}/vehicles/')

    vehicles = fleet.objects.filter(operator=operator)

    if request.method == "POST":
        selected_ids = request.POST.getlist('selected_vehicles')
        if not selected_ids:
            messages.error(request, "You must select at least one vehicle.")
            return redirect(request.path)

        # Redirect to mass edit page with selected IDs in query string or session
        id_string = ",".join(selected_ids)
        return redirect(f'/operator/{operator_name}/vehicles/mass-edit-bus/?ids={id_string}')

    context = {
        'operator': operator,
        'vehicles': vehicles,
    }
    return render(request, 'mass_edit_select.html', context)
 
@login_required
@require_http_methods(["GET", "POST"])
def route_add(request, operator_name):
    response = feature_enabled(request, "add_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Routes' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add a route for this operator.")
        return redirect(f'/operator/{operator_name}/vehicles/')

    if request.method == "POST":
        # Extract form data
        route_num = request.POST.get('route_number')
        route_name = request.POST.get('route_name')
        inbound = request.POST.get('inbound_destination')
        outbound = request.POST.get('outbound_destination')
        other_dests = request.POST.get('other_destinations')
        school_service = request.POST.get('school_service') == 'on'

        # Related many-to-many fields
        linkable_routes_ids = request.POST.getlist('linkable_routes')
        related_routes_ids = request.POST.getlist('related_routes')
        payment_method_ids = request.POST.getlist('payment_methods')

        # Convert other destinations to list
        other_dest_list = [d.strip() for d in other_dests.split(',')] if other_dests else []

        # Build route_details
        route_details = {
            "route_colour": "var(--background-color)",
            "route_text_colour": "var(--text-color)",
            "details": {
                "school_service": str(school_service).lower(),
                "contactless": str('1' in payment_method_ids).lower(),
                "cash": str('2' in payment_method_ids).lower()
            }
        }

        # Create the route
        new_route = route.objects.create(
            route_num=route_num,
            route_name=route_name,
            inbound_destination=inbound,
            outbound_destination=outbound,
            other_destination=other_dest_list,
            route_details=route_details
        )
        new_route.route_operators.add(operator)

        if linkable_routes_ids:
            new_route.linked_route.set(route.objects.filter(id__in=linkable_routes_ids))
        if related_routes_ids:
            new_route.related_route.set(route.objects.filter(id__in=related_routes_ids))

        messages.success(request, "Route added successfully.")
        return redirect(f'/operator/{operator_name}/')

    # GET request
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Add Route', 'url': f'/operator/{operator_name}/add-route/'}
    ]

    class MockPaymentMethod:
        def __init__(self, id, name):
            self.id = id
            self.name = name

        def __str__(self):
            return self.name

    context = {
        'operatorData': operator,
        'userData': [request.user],  # for userData.0.id
        'breadcrumbs': breadcrumbs,
        'linkableAndRelatedRoutes': route.objects.filter(route_operators=operator).exclude(id__in=request.POST.getlist('related_routes')),
        'paymentMethods': [
            MockPaymentMethod(1, 'Contactless'),
            MockPaymentMethod(2, 'Cash')
        ]
    }

    return render(request, 'add_route.html', context)
    
@login_required
@require_http_methods(["GET", "POST"])
def route_edit(request, operator_name, route_id):
    response = feature_enabled(request, "edit_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    has_inbound_stops = routeStop.objects.filter(route=route_instance, inbound=True).exists()
    has_outbound_stops = routeStop.objects.filter(route=route_instance, inbound=False).exists()
    is_circular = routeStop.objects.filter(route=route_instance, circular=True).exists()

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Routes' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route.")
        return redirect(f'/operator/{operator_name}/routes/')

    if request.method == "POST":
        # Extract form data
        route_num = request.POST.get('route_number')
        route_name = request.POST.get('route_name')
        inbound = request.POST.get('inbound_destination')
        outbound = request.POST.get('outbound_destination')
        other_dests = request.POST.get('other_destinations')
        school_service = request.POST.get('school_service') == 'on'

        # Related many-to-many fields
        linkable_routes_ids = request.POST.getlist('linkable_routes')
        related_routes_ids = request.POST.getlist('related_routes')
        payment_method_ids = request.POST.getlist('payment_methods')

        # Convert other destinations to list
        other_dest_list = [d.strip() for d in other_dests.split(',')] if other_dests else []

        # Build route_details
        route_details = {
            "route_colour": "var(--background-color)",
            "route_text_colour": "var(--text-color)",
            "details": {
                "school_service": str(school_service).lower(),
                "contactless": str('1' in payment_method_ids).lower(),
                "cash": str('2' in payment_method_ids).lower()
            }
        }

        # Update the route instance
        route_instance.route_num = route_num
        route_instance.route_name = route_name
        route_instance.inbound_destination = inbound
        route_instance.outbound_destination = outbound
        route_instance.other_destination = other_dest_list
        route_instance.route_details = route_details
        route_instance.save()

        # Update relationships
        route_instance.route_operators.set([operator])

        if linkable_routes_ids:
            route_instance.linked_route.set(route.objects.filter(id__in=linkable_routes_ids))
        else:
            route_instance.linked_route.clear()

        if related_routes_ids:
            route_instance.related_route.set(route.objects.filter(id__in=related_routes_ids))
        else:
            route_instance.related_route.clear()

        messages.success(request, "Route updated successfully.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    # GET request - Pre-fill existing data
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Edit Route', 'url': f'/operator/{operator_name}/route/{route_id}/edit/'}
    ]

    class MockPaymentMethod:
        def __init__(self, id, name):
            self.id = id
            self.name = name

        def __str__(self):
            return self.name

    # Determine selected payment methods
    selected_payment_ids = []
    if route_instance.route_details.get("details", {}).get("contactless") == "true":
        selected_payment_ids.append('1')
    if route_instance.route_details.get("details", {}).get("cash") == "true":
        selected_payment_ids.append('2')

    context = {
        'operatorData': operator,
        'userData': [request.user],
        'breadcrumbs': breadcrumbs,
        'linkableAndRelatedRoutes': route.objects.filter(route_operators=operator).exclude(id=route_id),
        'paymentMethods': [
            MockPaymentMethod(1, 'Contactless'),
            MockPaymentMethod(2, 'Cash')
        ],
        'routeData': route_instance,
        'selectedLinkables': route_instance.linked_route.values_list('id', flat=True),
        'selectedRelated': route_instance.related_route.values_list('id', flat=True),
        'selectedPaymentMethods': selected_payment_ids,
        'has_inbound_stops': has_inbound_stops,
        'has_outbound_stops': has_outbound_stops,
        'is_circular': is_circular,
    }

    return render(request, 'edit_route.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def add_stop_names_only(request, operator_name, route_id, direction):
    response = feature_enabled(request, "add_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Stops' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add stops for this route.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    if request.method == "POST":
        direction = request.POST.get('direction', direction)
        stop_names = request.POST.getlist('stop_names')
        stop_names = [name.strip() for name in stop_names if name.strip()]

        if not stop_names:
            messages.error(request, "Please provide at least one stop name.")
            return redirect(f'/operator/{operator_name}/route/{route_id}/add-stop-names/')

        # Format stops as list of {"stop": "..."} dictionaries
        stops_json = [{"stop": name} for name in stop_names]

        # Create the routeStop instance
        routeStop.objects.create(
            route=route_instance,
            inbound=(direction == 'inbound'),
            circular=False,
            stops=stops_json
        )

        messages.success(request, "Stops added successfully.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/edit/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Add Stop Names', 'url': f'/operator/{operator_name}/route/{route_id}/add-stop-names/'}
    ]

    context = {
        'operatorData': operator,
        'userData': [request.user],
        'breadcrumbs': breadcrumbs,
        'routeData': route_instance,
        'direction': direction,
    }

    return render(request, 'add_stop_names.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def edit_stop_names_only(request, operator_name, route_id, direction):
    response = feature_enabled(request, "edit_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Stops' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit stops for this route.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    # Get the existing routeStop object for this route + direction
    stop_obj = routeStop.objects.filter(route=route_instance, inbound=(direction == 'inbound')).first()

    if not stop_obj:
        messages.error(request, f"No existing stops found for this direction.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/add-stop-names/')

    if request.method == "POST":
        direction = request.POST.get('direction', direction)
        stop_names = request.POST.getlist('stop_names')
        stop_names = [name.strip() for name in stop_names if name.strip()]

        if not stop_names:
            messages.error(request, "Please provide at least one stop name.")
            return redirect(f'/operator/{operator_name}/route/{route_id}/edit-stop-names/')

        # Format new stops and update the object
        stop_obj.stops = [{"stop": name} for name in stop_names]
        stop_obj.save()

        messages.success(request, "Stops updated successfully.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/edit/')

    # Pre-fill stop names from the existing stop_obj.stops JSON list
    prefilled_stops = [item["stop"] for item in stop_obj.stops]

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Edit Stop Names', 'url': f'/operator/{operator_name}/route/{route_id}/edit-stop-names/'}
    ]

    context = {
        'operatorData': operator,
        'userData': [request.user],
        'breadcrumbs': breadcrumbs,
        'routeData': route_instance,
        'direction': direction,
        'prefilled_stops': prefilled_stops,
    }

    return render(request, 'edit_stop_names.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def vehicle_delete(request, operator_name, vehicle_id):
    response = feature_enabled(request, "delete_vehicles")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    vehicle = get_object_or_404(fleet, id=vehicle_id)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Buses' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this vehicle.")
        return redirect(f'/operator/{operator_name}/vehicles/')

    if request.method == "POST":
        vehicle.delete()
        messages.success(request, f"Vehicle '{vehicle.fleet_number or vehicle.reg or 'unnamed'}' deleted successfully.")
        return redirect(f'/operator/{operator_name}/vehicles/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Vehicles', 'url': f'/operator/{operator_name}/vehicles/'},
        {'name': 'Delete Vehicle', 'url': f'/operator/{operator_name}/vehicle/edit/{vehicle.id}/delete/'}
    ]

    return render(request, 'confirm_delete.html', {
        'vehicle': vehicle,
        'operator': operator,
        'breadcrumbs': breadcrumbs
    })

@login_required
@require_http_methods(["GET", "POST"])
def create_operator(request):
    response = feature_enabled(request, "add_operators")
    if response:
        return response
    
    groups = group.objects.filter(Q(group_owner=request.user) | Q(private=False))
    organisations = organisation.objects.filter(organisation_owner=request.user)
    operator_types = operatorType.objects.filter(published=True).order_by('operator_type_name')
    games = game.objects.all()
    regions = region.objects.all().order_by('region_country', 'region_name')

    # Group regions by country
    grouped_regions = defaultdict(list)
    for r in regions:
        grouped_regions[r.region_country].append(r)

    # Convert to regular dict for use in template
    regionData = dict(grouped_regions)

    if request.method == "POST":
        operator_name = request.POST.get('operator_name', '').strip()
        operator_code = request.POST.get('operator_code', '').strip()
        region_ids = request.POST.getlist('operator_region')
        operator_group_id = request.POST.get('operator_group')
        if operator_group_id == 'none':
            operator_group_id = None

        operator_org_id = request.POST.get('operator_organisation')
        website = request.POST.get('website', '').strip()
        twitter = request.POST.get('twitter', '').strip()
        game_name = request.POST.get('game', '').strip()
        operator_type = request.POST.get('type', '').strip()
        transit_authorities = request.POST.get('transit_authorities', '').strip()

        if MBTOperator.objects.filter(operator_name=operator_name).exists():
            return render(request, 'create_operator.html', {
                'error': 'operator_name_exists',
                'operatorName': operator_name,
                'operatorCode': operator_code,
                'operatorRegion': region_ids,
                'operatorGroup': operator_group_id,
                'operatorOrganisation': operator_org_id,
                'operatorWebsite': website,
                'operatorTwitter': twitter,
                'operatorTransitAuthorities': transit_authorities,
                'operatorType': operator_type,
                'operatorGame': game_name,
                'groups': groups,
                'organisations': organisations,
                'operatorTypeData': operator_types,
                'gameData': games,
                'regionData': regionData,
            })

        if MBTOperator.objects.filter(operator_code=operator_code).exists():
            return render(request, 'create_operator.html', {
                'error': 'operator_code_exists',
                'operatorName': operator_name,
                'operatorCode': operator_code,
                'operatorRegion': region_ids,
                'operatorGroup': operator_group_id,
                'operatorOrganisation': operator_org_id,
                'operatorWebsite': website,
                'operatorTwitter': twitter,
                'operatorTransitAuthorities': transit_authorities,
                'operatorType': operator_type,
                'operatorGame': game_name,
                'groups': groups,
                'organisations': organisations,
                'operatorTypeData': operator_types,
                'gameData': games,
                'regionData': regionData,
            })

        operator_group = group.objects.filter(id=operator_group_id).first() if operator_group_id else None
        operator_org = organisation.objects.filter(id=operator_org_id).first() if operator_org_id else None

        new_operator = MBTOperator.objects.create(
            operator_name=operator_name,
            operator_code=operator_code,
            owner=request.user,
            group=operator_group,
            organisation=operator_org,
            operator_details={
                'website': website,
                'twitter': twitter,
                'game': game_name,
                'type': operator_type,
                'transit_authorities': transit_authorities
            }
        )


        new_operator.region.set(region_ids)
        new_operator.save()

        messages.success(request, "Operator created successfully.")
        return redirect(f'/operator/{new_operator.operator_name}/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
    ]

    context = {
        'groups': groups,
        'organisations': organisations,
        'operatorTypeData': operator_types,
        'gameData': games,
        'regionData': regionData,
        'operatorRegion': [],
        'breadcrumbs': breadcrumbs,
    }
    return render(request, 'create_operator.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def route_timetable_options(request, operator_name, route_id):
    response = feature_enabled(request, "edit_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    all_timetables = timetableEntry.objects.filter(route=route_instance).prefetch_related('day_type').order_by('id')

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Timetables' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route's timetable.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    # Get all days
    days = dayType.objects.all()

    if request.method == "POST":
        # Handle timetable editing logic here
        pass  # Placeholder for actual logic

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_name}/route/{route_id}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'route': route_instance,
        'days': days,
        'helper_permissions': userPerms,
        'all_timetables': all_timetables,
    }
    return render(request, 'timetable_options.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def route_edit_stops(request, operator_name, route_id, direction):
    response = feature_enabled(request, "edit_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Stops' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route's stops.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    # Load existing stops for this route and direction
    try:
        existing_route_stops = routeStop.objects.get(route=route_instance, inbound=(direction == "inbound"))
        existing_stops = existing_route_stops.stops
    except routeStop.DoesNotExist:
        existing_stops = []

    if request.method == "POST":
        try:
            raw_data = request.POST.get("routeData")
            if not raw_data:
                raise ValueError("Missing routeData")

            parsed_stops = json.loads(raw_data)

            # Update or create routeStop record
            routeStop.objects.update_or_create(
                route=route_instance,
                inbound=(direction == "inbound"),
                defaults={
                    "circular": False,  # Adjust if needed
                    "stops": parsed_stops
                }
            )

            messages.success(request, "Stops updated successfully.")
            return redirect(f'/operator/{operator_name}/route/{route_id}/')

        except Exception as e:
            messages.error(request, f"Failed to update stops: {e}")
            return redirect(request.path)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_name}/route/{route_id}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'route': route_instance,
        'helper_permissions': userPerms,
        'direction': direction,
        'existing_stops': existing_stops,  # Pass existing stops here
    }
    return render(request, 'route_edit_route.html', context)

def route_map(request, operator_name, route_id):
    response = feature_enabled(request, "route_map")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    context = {
        'operator': operator,
        'route': route_instance,
        'full_route_num': route_instance.route_num or "Route",
    }
    return render(request, 'route_map.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def route_add_stops(request, operator_name, route_id, direction):
    response = feature_enabled(request, "edit_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Stops' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route's stops.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    if request.method == "POST":
        try:
            raw_data = request.POST.get("routeData")
            if not raw_data:
                raise ValueError("Missing routeData")

            parsed_stops = json.loads(raw_data)

            # Delete any existing stops for this route and direction first (optional but good for edits)
            routeStop.objects.filter(route=route_instance, inbound=(direction == "inbound")).delete()

            # Create new routeStop entry
            routeStop.objects.create(
                route=route_instance,
                inbound=(direction == "inbound"),
                circular=False,  # Or True if you detect that logic elsewhere
                stops=parsed_stops  # Save raw list of dictionaries directly
            )

            messages.success(request, "Stops saved successfully.")
            return redirect(f'/operator/{operator_name}/route/{route_id}/')

        except Exception as e:
            messages.error(request, f"Failed to save stops: {e}")
            return redirect(request.path)


    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_name}/route/{route_id}/timeable/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'route': route_instance,
        'helper_permissions': userPerms,
        'direction': direction,
    }
    return render(request, 'route_add_route.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def route_timetable_add(request, operator_name, route_id, direction):
    response = feature_enabled(request, "edit_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    serialized_route = routesSerializer(route_instance).data
    full_route_num = serialized_route.get('full_searchable_name', '')

    userPerms = get_helper_permissions(request.user, operator)
    days = dayType.objects.all()

    if request.user != operator.owner and 'Edit Timetables' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route's timetable.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    stops = routeStop.objects.filter(route=route_instance, inbound=direction == "inbound").first()

    if request.method == "POST":
        stop_names = request.POST.getlist("stop_names")
        base_times_str = request.POST.get("departure_times")
        offset_minutes = request.POST.getlist("offset_minutes")
        timing_point_set = set(request.POST.getlist("timing_points"))
        selected_days = request.POST.getlist("days[]")

        try:
            # Ensure at least one day is selected
            if not selected_days:
                raise ValueError("Please select at least one day.")

            # Parse base times
            base_times = [datetime.strptime(t.strip(), "%H:%M") for t in base_times_str.split(",") if t.strip()]
            if not base_times:
                raise ValueError("No base times provided.")

            stop_times_result = {}

            for i, stop in enumerate(stop_names):
                if i == 0:
                    stop_times_result[stop] = {
                        "timing_point": True,
                        "stopname": stop,
                        "times": [t.strftime("%H:%M") for t in base_times]
                    }
                else:
                    try:
                        offset = int(offset_minutes[i - 1])
                    except (ValueError, IndexError):
                        raise ValueError(f"Invalid or missing offset for stop: {stop}")

                    prev_times = [datetime.strptime(t, "%H:%M") for t in stop_times_result[stop_names[i - 1]]["times"]]
                    new_times = [t + timedelta(minutes=offset) for t in prev_times]
                    stop_times_result[stop] = {
                        "timing_point": stop in timing_point_set,
                        "stopname": stop,
                        "times": [t.strftime("%H:%M") for t in new_times]
                    }

            # Save to DB
            entry = timetableEntry.objects.create(
                route=route_instance,
                inbound=(direction == "inbound"),
                stop_times=stop_times_result,
                operator_schedule=[],
            )
            entry.day_type.set(dayType.objects.filter(id__in=selected_days))
            entry.save()

            messages.success(request, "Timetable saved successfully.")
            return redirect(f'/operator/{operator_name}/route/{route_id}/')

        except Exception as e:
            messages.error(request, f"Error saving timetable: {e}")
            return redirect(request.path)


    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_name}/route/{route_id}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'stops': stops,
        'route': route_instance,
        'helper_permissions': userPerms,
        'days': days,
        'direction': direction,
        'full_route_num': full_route_num,
    }
    return render(request, 'timetable_add.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def route_timetable_import(request, operator_name, route_id, direction):
    response = feature_enabled(request, "edit_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    serialized_route = routesSerializer(route_instance).data
    full_route_num = serialized_route.get('full_searchable_name', '')

    userPerms = get_helper_permissions(request.user, operator)
    days = dayType.objects.all()

    if request.user != operator.owner and 'Edit Timetables' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route's timetable.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    stops = routeStop.objects.filter(route=route_instance, inbound=direction == "inbound").first()

    if request.method == "POST":
        selected_days = request.POST.getlist("days[]")
        raw_timetable = request.POST.get("AllBusTimes")  # full timetable
        raw_timing_points = request.POST.get("AllBusTimesTimingPoints")  # timing points only

        try:
            if not selected_days:
                raise ValueError("Please select at least one day.")
            if not raw_timetable:
                raise ValueError("No full timetable data submitted.")
            if not raw_timing_points:
                raise ValueError("No timing points data submitted.")

            def parse_timetable(raw_text):
                lines = [line.rstrip('\r').rstrip('\n') for line in raw_text.strip().splitlines() if line.strip()]
                result = {}
                i = 0
                while i < len(lines):
                    stop_name = lines[i].strip()
                    times_line = lines[i + 1] if (i + 1) < len(lines) else ""

                    # Remove exactly one leading tab if present
                    if times_line.startswith('\t'):
                        times_line = times_line[1:]

                    times = [time.strip() if time.strip() else "" for time in times_line.split('\t')]
                    result[stop_name] = times
                    i += 2
                return result

            full_timetable = parse_timetable(raw_timetable)
            timing_points = parse_timetable(raw_timing_points)

            timing_points_set = set(timing_points.keys())

            stop_times_result = {}
            for stop_name, times in full_timetable.items():
                stop_times_result[stop_name] = {
                    "stopname": stop_name,
                    "timing_point": stop_name in timing_points_set,
                    "times": times,
                }

            if not stop_times_result:
                raise ValueError("No valid stop/time pairs found.")

            entry = timetableEntry.objects.create(
                route=route_instance,
                inbound=(direction == "inbound"),
                stop_times=stop_times_result,
                operator_schedule=[],
            )
            entry.day_type.set(dayType.objects.filter(id__in=selected_days))
            entry.save()

            messages.success(request, "Timetable imported successfully.")
            return redirect(f'/operator/{operator_name}/route/{route_id}/')

        except Exception as e:
            messages.error(request, f"Error processing timetable: {e}")
            return redirect(request.path)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_name}/route/{route_id}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'stops': stops,
        'route': route_instance,
        'helper_permissions': userPerms,
        'days': days,
        'direction': direction,
        'full_route_num': full_route_num,
    }
    return render(request, 'import_bustimes.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def route_timetable_edit(request, operator_name, route_id, timetable_id):
    response = feature_enabled(request, "edit_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)
    timetable_instance = get_object_or_404(timetableEntry, id=timetable_id)

    serialized_route = routesSerializer(route_instance).data
    full_route_num = serialized_route.get('full_searchable_name', '')

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Timetables' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route's timetable.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    days = dayType.objects.all()

    if request.method == "POST":
        try:
            stop_times_result = {}
            stop_keys = [key for key in request.POST if key.startswith("stopname_")]
            stop_keys.sort(key=lambda x: int(x.split("_")[1]))  # sort by index

            for stop_key in stop_keys:
                index = stop_key.split("_")[1]
                stop_name = request.POST.get(f"stopname_{index}")
                raw_times = request.POST.get(f"times_{index}")
                is_timing_point = request.POST.get(f"timing_point_{index}") == "on"

                # Parse times safely
                times = [
                    t.strip().strip('"').strip("'")
                    for t in raw_times.split(",")
                    if t.strip()
                ]

                stop_times_result[stop_name] = {
                    "stopname": stop_name,
                    "timing_point": is_timing_point,
                    "times": times
                }

            selected_days = request.POST.getlist("days[]")
            if not selected_days:
                raise ValueError("Please select at least one day.")

            # Save changes
            timetable_instance.stop_times = stop_times_result
            timetable_instance.day_type.set(dayType.objects.filter(id__in=selected_days))
            timetable_instance.save()

            messages.success(request, "Timetable updated successfully.")
            return redirect(f'/operator/{operator_name}/route/{route_id}/')

        except Exception as e:
            messages.error(request, f"Error updating timetable: {e}")
            return redirect(request.path)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_name}/route/{route_id}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'route': route_instance,
        'days': days,
        'helper_permissions': userPerms,
        'timetable_entry': timetable_instance,
        'stop_times': timetable_instance.stop_times,
        'full_route_num': full_route_num,
        'direction': 'inbound' if timetable_instance.inbound else 'outbound',
        'selected_days': timetable_instance.day_type.values_list('id', flat=True),
    }
    return render(request, 'timetable_edit.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def route_timetable_delete(request, operator_name, route_id, timetable_id):
    response = feature_enabled(request, "delete_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)
    timetable_entry = get_object_or_404(timetableEntry, id=timetable_id, route=route_instance)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Delete Timetables' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this timetable entry.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    if request.method == "POST":
        timetable_entry.delete()
        messages.success(request, "Timetable entry deleted successfully.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_name}/route/{route_id}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'route': route_instance,
        'timetable_entry': timetable_entry,
        'helper_permissions': userPerms,
    }
    return render(request, 'confirm_delete_tt.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_type_add(request):
    response = feature_enabled(request, "add_operator_types")
    if response:
        return response
    
    if request.method == "POST":
        operator_type_name = request.POST.get('operator_type_name', '').strip()
        if not operator_type_name:
            messages.error(request, "Operator type name cannot be empty.")
            return redirect('/operator/create-type/')

        if operatorType.objects.filter(operator_type_name=operator_type_name).exists():
            messages.error(request, "An operator type with this name already exists.")
            return redirect('/operator/create-type/')

        new_operator_type = operatorType.objects.create(operator_type_name=operator_type_name, published=False)
        webhook_url = settings.DISCORD_TYPE_REQUEST_WEBHOOK
        message = {
            "content": f"New operator type created: **{operator_type_name}** by {request.user.username}\n[Review](https://mybustimes.cc/admin/operator-management/pending/)\n",
        }
        try:
            requests.post(webhook_url, json=message, timeout=5)
        except Exception as e:
            # Optionally log the error
            print(f"Failed to send Discord webhook: {e}")

        return redirect('/operator/types/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Add Operator Type', 'url': '/operator/create-type/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
    }
    return render(request, 'add_operator_type.html', context)

def operator_types(request):
    response = feature_enabled(request, "view_operator_types")
    if response:
        return response
    
    operator_types = operatorType.objects.filter(published=True).order_by('operator_type_name')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Operator Types', 'url': '/operator/types/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator_types': operator_types,
    }
    return render(request, 'operator_types.html', context)

def operator_type_detail(request, operator_type_name):
    response = feature_enabled(request, "view_operator_types")
    if response:
        return response
    
    operator_type = get_object_or_404(operatorType, operator_type_name=operator_type_name)

    operators = MBTOperator.objects.filter(operator_details__type=operator_type_name).order_by('operator_name')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Operator Types', 'url': '/operator/types/'},
        {'name': operator_type.operator_type_name, 'url': f'/operator/types/{operator_type.operator_type_name}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator_type': operator_type,
        'operators': operators,
    }
    return render(request, 'operator_type_detail.html', context)

def operator_updates(request, operator_name):
    response = feature_enabled(request, "view_operator_updates")
    if response:
        return response
    
    operator = MBTOperator.objects.filter(operator_name=operator_name).first()
    updates = companyUpdate.objects.filter(operator=operator).order_by('-created_at')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Operator Updates', 'url': f'/operator/{operator_name}/updates/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'updates': updates,
        'operator': operator,
    }
    return render(request, 'operator_updates.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_update_add(request, operator_name):
    response = feature_enabled(request, "add_operator_updates")
    if response:
        return response
    
    operator = MBTOperator.objects.filter(operator_name=operator_name).first()
    routes = route.objects.filter(route_operators=operator)

    userPerms = get_helper_permissions(request.user, operator)
    if request.user != operator.owner and 'Add Updates' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add this update.")
        return redirect(f'/operator/{operator_name}/')

    if request.method == "POST":
        update_text = request.POST.get('update_text', '').strip()
        selected_routes = request.POST.getlist('routes')  # this gets multiple values from multi-select

        if not update_text:
            messages.error(request, "Update text cannot be empty.")
            return redirect(f'/operator/{operator_name}/updates/add/')

        new_update = companyUpdate.objects.create(
            operator=operator,
            update_text=update_text
        )

        if selected_routes:
            new_update.routes.set(selected_routes)

        messages.success(request, "Update created successfully.")
        return redirect(f'/operator/{operator_name}/updates/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Add Update', 'url': f'/operator/{operator_name}/updates/add/'}
    ]

    return render(request, 'add_operator_update.html', {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'routes': routes,
    })

@login_required
@require_http_methods(["GET", "POST"])
def operator_update_edit(request, operator_name, update_id):
    response = feature_enabled(request, "edit_operator_updates")
    if response:
        return response
    
    update = get_object_or_404(companyUpdate, id=update_id)
    routes = route.objects.filter(route_operators=update.operator)

    userPerms = get_helper_permissions(request.user, update.operator)
    if request.user != update.operator.owner and 'Edit Updates' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this update.")
        return redirect(f'/operator/{operator_name}/')

    if request.method == "POST":
        update_text = request.POST.get('update_text', '').strip()
        selected_routes = request.POST.getlist('routes')

        if not update_text:
            messages.error(request, "Update text cannot be empty.")
            return redirect(f'/operator/{operator_name}/updates/edit/{update_id}/')

        update.update_text = update_text
        update.routes.set(selected_routes)
        update.save()

        messages.success(request, "Update edited successfully.")
        return redirect(f'/operator/{operator_name}/updates/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Edit Update', 'url': f'/operator/{operator_name}/updates/edit/{update_id}/'}
    ]

    return render(request, 'edit_operator_update.html', {
        'breadcrumbs': breadcrumbs,
        'update': update,
        'operator': update.operator,
        'routes': routes,
    })

@login_required
@require_http_methods(["GET", "POST"])
def operator_update_delete(request, operator_name, update_id):
    response = feature_enabled(request, "delete_operator_updates")
    if response:
        return response
    
    update = get_object_or_404(companyUpdate, id=update_id)

    userPerms = get_helper_permissions(request.user, update.operator)
    if request.user != update.operator.owner and 'Delete Updates' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this update.")
        return redirect(f'/operator/{operator_name}/')

    if request.method == "POST":
        update.delete()
        messages.success(request, "Update deleted successfully.")
        return redirect(f'/operator/{operator_name}/updates/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Delete Update', 'url': f'/operator/{operator_name}/updates/delete/{update_id}/'}
    ]

    return render(request, 'confirm_delete_update.html', {
        'breadcrumbs': breadcrumbs,
        'update': update,
        'operator': update.operator,
    })

def fleet_history(request):
    response = feature_enabled(request, "view_history")
    if response:
        return response
    
    vehicle_id = request.GET.get('vehicle', '').strip()
    username = request.GET.get('user', '').strip()
    operator_id = request.GET.get('operator', '').strip()
    status = request.GET.get('status', '').strip()

    changes_qs = fleetChange.objects.all()

    error = None

    # Filter by vehicle ID (exact or partial?)
    if vehicle_id:
        changes_qs = changes_qs.filter(vehicle__id=vehicle_id)

    # Filter by username (user who made the change)
    if username:
        try:
            user_obj = CustomUser.objects.get(username=username)
            changes_qs = changes_qs.filter(user=user_obj)
        except CustomUser.DoesNotExist:
            changes_qs = changes_qs.none()
            error = f"No user found with username '{username}'."

    # Filter by operator ID
    if operator_id:
        changes_qs = changes_qs.filter(operator__id=operator_id)

    # Filter by status
    if status:
        if status == 'approved':
            changes_qs = changes_qs.filter(approved=True)
        elif status == 'pending':
            changes_qs = changes_qs.filter(pending=True)
        elif status == 'disapproved':
            changes_qs = changes_qs.filter(disapproved=True)

    # Order by most recent first
    changes_qs = changes_qs.order_by('-create_at')

    # For each change, parse the JSON of changes once to send to template
    for change in changes_qs:
        try:
            change.parsed_changes = json.loads(change.changes)
        except Exception:
            change.parsed_changes = []

    for change in changes_qs:
        try:
            change.parsed_changes = json.loads(change.changes)
        except Exception:
            change.parsed_changes = []

        # Extract livery info for template convenience
        livery_name_from = None
        livery_name_to = None
        livery_css_from = None
        livery_css_to = None
        colour_from = None
        colour_to = None

        for item in change.parsed_changes:
            if item.get("item") == "livery_name":
                livery_name_from = item.get("from")
                livery_name_to = item.get("to")
            elif item.get("item") == "livery_css":
                livery_css_from = item.get("from")
                livery_css_to = item.get("to")
            elif item.get("item") == "colour":
                colour_from = item.get("from")
                colour_to = item.get("to")

        change.livery_name_from = livery_name_from
        change.livery_name_to = livery_name_to
        change.livery_css_from = livery_css_from
        change.livery_css_to = livery_css_to
        change.colour_from = colour_from
        change.colour_to = colour_to

    context = {
        'fleet_changes': changes_qs,
        'error': error,
    }

    return render(request, 'history.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_helpers(request, operator_name):
    response = feature_enabled(request, "view_helpers")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    helpers = helper.objects.filter(operator=operator)

    if request.user != operator.owner and not request.user.is_superuser:
        messages.error(request, "You do not have permission to manage helpers for this operator.")
        return redirect(f'/operator/{operator_name}/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Helpers', 'url': f'/operator/{operator_name}/helpers/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'helpers': helpers,
    }
    return render(request, 'operator_helpers.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_helper_add(request, operator_name):
    response = feature_enabled(request, "add_helpers")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_name=operator_name)

    if request.user != operator.owner and not request.user.is_superuser:
        messages.error(request, "You do not have permission to manage helpers for this operator.")
        return redirect(f'/operator/{operator_name}/')

    if request.method == "POST":
        form = OperatorHelperForm(request.POST)
        if form.is_valid():
            helper = form.save(commit=False)
            helper.operator = operator
            helper.save()
            return redirect('operator_helpers', operator_name=operator_name)
    else:
        form = OperatorHelperForm()

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Helpers', 'url': f'/operator/{operator_name}/helpers/'},
        {'name': 'Add Helper', 'url': f'/operator/{operator_name}/helpers/add/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'form': form,
    }
    return render(request, 'operator_helper_add.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_helper_edit(request, operator_name, helper_id):
    response = feature_enabled(request, "edit_helpers")
    if response:
        return response

    if request.user != operator.owner and not request.user.is_superuser:
        messages.error(request, "You do not have permission to manage helpers for this operator.")
        return redirect(f'/operator/{operator_name}/')

    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    helper = get_object_or_404(helper, id=helper_id, operator=operator)

    if request.method == "POST":
        form = OperatorHelperForm(request.POST, instance=helper)
        if form.is_valid():
            form.save()
            return redirect('operator_helpers', operator_name=operator_name)
    else:
        form = OperatorHelperForm(instance=helper)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Helpers', 'url': f'/operator/{operator_name}/helpers/'},
        {'name': 'Edit Helper', 'url': f'/operator/{operator_name}/helpers/edit/{helper_id}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'form': form,
        'helper': helper,
    }
    return render(request, 'operator_helper_edit.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_helper_delete(request, operator_name, helper_id):
    response = feature_enabled(request, "delete_helpers")
    if response:
        return response
    
    if request.user != operator.owner and not request.user.is_superuser:
        messages.error(request, "You do not have permission to manage helpers for this operator.")
        return redirect(f'/operator/{operator_name}/')

    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    helper = get_object_or_404(helper, id=helper_id, operator=operator)

    if request.method == "POST":
        helper.delete()
        messages.success(request, "Helper deleted successfully.")
        return redirect('operator_helpers', operator_name=operator_name)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Helpers', 'url': f'/operator/{operator_name}/helpers/'},
        {'name': 'Delete Helper', 'url': f'/operator/{operator_name}/helpers/remove/{helper_id}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'helper': helper,
    }
    return render(request, 'confirm_delete_helper.html', context)

def operator_tickets(request, operator_name):
    response = feature_enabled(request, "view_tickets")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    # Get all unique zone names for this operator's tickets
    zones = ticket.objects.filter(operator=operator).values_list('zone', flat=True).distinct()
    zones = list(zones)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Tickets', 'url': f'/operator/{operator_name}/tickets/'}
    ]

    context = {
        'operator': operator,
        'zones': zones,
        'breadcrumbs': breadcrumbs,
    }
    return render(request, 'operator_tickets_zones.html', context)

def operator_tickets_details(request, operator_name, zone_name):
    response = feature_enabled(request, "view_tickets")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    tickets = ticket.objects.filter(operator=operator, zone=zone_name)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Tickets', 'url': f'/operator/{operator_name}/tickets/'},
        {'name': zone_name, 'url': f'/operator/{operator_name}/tickets/{zone_name}/'}
    ]

    context = {
        'zone': zone_name,
        'operator': operator,
        'tickets': tickets,
        'breadcrumbs': breadcrumbs,
    }
    return render(request, 'operator_tickets.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_ticket_add(request, operator_name):
    response = feature_enabled(request, "add_tickets")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_name=operator_name)

    userPerms = get_helper_permissions(request.user, operator)
    if request.user != operator.owner and 'Add Tickets' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add tickets for this operator.")
        return redirect(f'/operator/{operator_name}/')

    if request.method == "POST":
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.operator = operator
            ticket.save()
            messages.success(request, "Ticket created successfully.")
            return redirect('operator_tickets', operator_name=operator_name)
    else:
        form = TicketForm()

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Tickets', 'url': f'/operator/{operator_name}/tickets/'},
        {'name': 'Add Ticket', 'url': f'/operator/{operator_name}/tickets/add/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'form': form,
    }
    return render(request, 'add_operator_ticket.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_ticket_edit(request, operator_name, ticket_id):
    response = feature_enabled(request, "edit_tickets")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    ticket = get_object_or_404(ticket, id=ticket_id, operator=operator)

    userPerms = get_helper_permissions(request.user, operator)
    if request.user != operator.owner and 'Edit Tickets' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this ticket.")
        return redirect(f'/operator/{operator_name}/')

    if request.method == "POST":
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, "Ticket updated successfully.")
            return redirect('operator_tickets', operator_name=operator_name)
    else:
        form = TicketForm(instance=ticket)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Tickets', 'url': f'/operator/{operator_name}/tickets/'},
        {'name': 'Edit Ticket', 'url': f'/operator/{operator_name}/tickets/edit/{ticket_id}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'form': form,
        'ticket': ticket,
    }
    return render(request, 'edit_operator_ticket.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_ticket_delete(request, operator_name, ticket_id):
    response = feature_enabled(request, "delete_tickets")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    ticket = get_object_or_404(ticket, id=ticket_id, operator=operator)

    userPerms = get_helper_permissions(request.user, operator)
    if request.user != operator.owner and 'Delete Tickets' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this ticket.")
        return redirect(f'/operator/{operator_name}/')

    if request.method == "POST":
        ticket.delete()
        messages.success(request, "Ticket deleted successfully.")
        return redirect('operator_tickets', operator_name=operator_name)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Tickets', 'url': f'/operator/{operator_name}/tickets/'},
        {'name': 'Delete Ticket', 'url': f'/operator/{operator_name}/tickets/delete/{ticket_id}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'ticket': ticket,
    }
    return render(request, 'confirm_delete_ticket.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def mass_log_trips(request, operator_name):
    response = feature_enabled(request, "mass_log_trips")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_name=operator_name)

    userPerms = get_helper_permissions(request.user, operator)
    if request.user != operator.owner and 'Mass Log Trips' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to log trips for this operator.")
        return redirect(f'/operator/{operator_name}/')

    if request.method == "POST":
        vehicle_id = request.POST.get("vehicle")
        duty_id = request.POST.get("duty")
        running_board_id = request.POST.get("running_board")

        vehicle = get_object_or_404(fleet, id=vehicle_id)

        # Handle Duty or Running Board logging
        if duty_id:
            selected_duty = get_object_or_404(duty, id=duty_id, board_type="duty")
            trip_set = selected_duty.duty_trips.all()
        elif running_board_id:
            selected_rb = get_object_or_404(duty, id=running_board_id, board_type="running-boards")
            trip_set = selected_rb.duty_trips.all()
        else:
            # Handle manual Mass Log
            route_id = request.POST.get("route")
            start_time_str = request.POST.get("start_time")
            trip_count = int(request.POST.get("trips", 1))
            duration = int(request.POST.get("trip_duration", 0))
            break_between = int(request.POST.get("break_between", 0))

            route_obj = get_object_or_404(route, id=route_id)

            today = datetime.today()
            start_time = datetime.strptime(start_time_str, "%H:%M")
            current_start = make_aware(datetime.combine(today.date(), start_time.time()))

            for i in range(trip_count):
                trip_start = current_start
                trip_end = trip_start + timedelta(minutes=duration)

                Trip.objects.create(
                    trip_vehicle=vehicle,
                    trip_route=route_obj,
                    trip_route_num=route_obj.route_num,
                    trip_start_location=route_obj.start_location,
                    trip_end_location=route_obj.end_location,
                    trip_start_at=trip_start,
                    trip_end_at=trip_end,
                )

                current_start = trip_end + timedelta(minutes=break_between)

            messages.success(request, "Mass trips logged successfully.")
            return redirect(request.path)

        # Handle DutyTrip-based logging
        today = datetime.today()
        for trip in trip_set:
            start_dt = make_aware(datetime.combine(today.date(), trip.start_time))
            end_dt = make_aware(datetime.combine(today.date(), trip.end_time))

            Trip.objects.create(
                trip_vehicle=vehicle,
                trip_route_num=trip.route,
                trip_start_location=trip.start_at,
                trip_end_location=trip.end_at,
                trip_start_at=start_dt,
                trip_end_at=end_dt,
            )

        messages.success(request, "Trips from duty or running board logged successfully.")
        return redirect(request.path)

    # Load data for GET
    duties = duty.objects.filter(duty_operator=operator, board_type='duty').order_by('duty_name')
    running_boards = duty.objects.filter(duty_operator=operator, board_type='running-boards').order_by('duty_name')
    vehicles = fleet.objects.filter(operator=operator).order_by('fleet_number')
    routes = route.objects.filter(route_operators=operator).order_by('route_num')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Vehicles', 'url': f'/operator/{operator_name}/vehicles/'},
        {'name': 'Mass Log Trips', 'url': f'/operator/{operator_name}/vehicles/mass-log-trips/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'duties': duties,
        'running_boards': running_boards,
        'vehicles': vehicles,
        'routes': routes,
    }
    return render(request, 'mass-log-trips.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def route_updates_options(request, operator_name, route_id):
    route_obj = get_object_or_404(route, id=route_id)
    updates = route_obj.service_updates.all()
    return render(request, 'route_updates_options.html', {
        'updates': updates,
        'route': route_obj,
        'operator_name': operator_name
    })

@login_required
@require_http_methods(["GET", "POST"])
def route_update_add(request, operator_name, route_id):
    route_obj = get_object_or_404(route, id=route_id)
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    if request.method == 'POST':
        form = ServiceUpdateForm(request.POST, operator=operator)
        if form.is_valid():
            update = form.save()
            update.effected_route.add(route_obj)
            return redirect('route_updates_options', operator_name=operator_name, route_id=route_id)
    else:
        form = ServiceUpdateForm(initial={'effected_route': [route_obj]}, operator=operator)
    return render(request, 'route_updates_form.html', {
        'form': form,
        'route': route_obj,
        'operator_name': operator_name,
        'action': 'Add'
    })

@login_required
@require_http_methods(["GET", "POST"])
def route_update_edit(request, operator_name, route_id, update_id):
    update = get_object_or_404(serviceUpdate, id=update_id)
    route_obj = get_object_or_404(route, id=route_id)
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    if request.method == 'POST':
        form = ServiceUpdateForm(request.POST, instance=update, operator=operator)
        if form.is_valid():
            form.save()
            return redirect('route_updates_options', operator_name=operator_name, route_id=route_id)
    else:
        form = ServiceUpdateForm(instance=update, operator=operator)
    return render(request, 'route_updates_form.html', {
        'form': form,
        'route': route_obj,
        'operator_name': operator_name,
        'action': 'Edit'
    })

@login_required
@require_http_methods(["GET", "POST"])
def route_update_delete(request, operator_name, route_id, update_id):
    update = get_object_or_404(serviceUpdate, id=update_id)
    if request.method == 'POST':
        update.delete()
        return redirect('route_updates_options', operator_name=operator_name, route_id=route_id)
    return render(request, 'route_updates_delete_confirm.html', {
        'update': update,
        'route_id': route_id,
        'operator_name': operator_name
    })
