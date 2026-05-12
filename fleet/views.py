# Python standard library imports
from multiprocessing import context
import calendar
import re
import os
import json
import logging
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
from collections import OrderedDict
from bs4 import BeautifulSoup
from django.db.models import Prefetch

# Django imports
from django.shortcuts import render, redirect, get_object_or_404
from django.http import StreamingHttpResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.forms.models import model_to_dict
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.core.serializers import serialize
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.timezone import now, make_aware, datetime, timedelta
from django.http import Http404
from django.core.paginator import Paginator
from django.utils.dateparse import parse_time
from simple_history.models import HistoricalRecords
from django.core.files.storage import default_storage
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

# Django REST Framework imports
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, permissions, viewsets, status
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import IntegerField, Case, When, Value, Count
from django.db.models.functions import Cast

# Project-specific imports
from mybustimes.permissions import ReadOnly, ReadOnly
from .models import *
from routes.models import *
from .filters import *
from .forms import *
from .serializers import *
from routes.serializers import *
from main.models import featureToggle, update
from tracking.models import Tracking, Trip
from gameData.models import *

import requests

DISCORD_FULL_OPERATOR_LOGS_ID = 1432690197228818482
logger = logging.getLogger(__name__)

# Vars
max_for_sale = 25


def safe_json_load(path, default=None):
    """Load JSON from default_storage at `path`, safely catching MemoryError and other IO errors.
    Returns `default` on failure to avoid blowing up the request process.
    """
    try:
        # Prefer a local MEDIA_ROOT file if it exists (e.g. /media/JSON/features.json)
        try:
            media_path = os.path.join(settings.MEDIA_ROOT, path)
        except Exception:
            media_path = None

        if media_path and os.path.exists(media_path):
            with open(media_path, "r") as f:
                return json.load(f)

        # Fallback to configured storage backend (S3, etc.)
        with default_storage.open(path, "r") as f:
            return json.load(f)

    except MemoryError:
        # Very large file; return default and let caller decide how to proceed.
        return default if default is not None else {}
    except Exception:
        return default if default is not None else {}

def send_to_discord_delete(count, channel_id, operator_name):
    content = f"**Operator Deleted: {operator_name}**\n"
    content += f"Vehicles: {count}\n"
    content += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    data = {
        'channel_id': channel_id,
        'message': content,
    }

    files = {}

    if not settings.DISABLE_JESS:
        response = requests.post(
            f"{settings.DISCORD_BOT_API_URL}/send-message-clean",
            data=data,
            files=files
        )
        response.raise_for_status()

def send_to_discord_embed(channel_id, title, message, colour=0x00BFFF):
    embed = {
        "title": title,
        "description": message,
        "color": colour,
        "fields": [
            {
                "name": "Time",
                "value": datetime.now().strftime('%Y-%m-%d %H:%M'),
                "inline": True
            }
        ],
        "footer": {
            "text": "MBT Logging System"
        },
        "timestamp": datetime.now().isoformat()
    }

    data = {
        'channel_id': channel_id,
        'embed': embed
    }

    if not settings.DISABLE_JESS:
        response = requests.post(
            f"{settings.DISCORD_BOT_API_URL}/send-embed",
            json=data
        )
        response.raise_for_status()

def send_to_discord_embed_Sales(channel_id, title, message, colour=0x00BFFF, content=None):
    embed = {
        "title": title,
        "description": message,
        "color": colour,
        "fields": [
            {
                "name": "Time",
                "value": datetime.now().strftime('%Y-%m-%d %H:%M'),
                "inline": True
            }
        ],
        "footer": {
            "text": "MBT Sales System"
        },
        "timestamp": datetime.now().isoformat()
    }

    data = {
        'channel_id': channel_id,
        'embed': embed
    }

    if content:  # <-- include ping here
        data['content'] = content

    if not settings.DISABLE_JESS:
        response = requests.post(
            f"{settings.DISCORD_BOT_API_URL}/send-embed",
            json=data
        )
        response.raise_for_status()



# API Views
class fleetListView(generics.ListAPIView):
    serializer_class = fleetSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = fleetsFilter
    permission_classes = [ReadOnly]

    def get_queryset(self):
        return fleet.objects.all()

class fleetDetailView(generics.RetrieveAPIView):
    queryset = fleet.objects.all()
    serializer_class = fleetSerializer
    permission_classes = [ReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = fleetsFilter

class operatorListView(generics.ListAPIView):
    serializer_class = operatorSerializer
    permission_classes = [ReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = operatorsFilter

    def get_serializer_class(self):
        # Use lightweight serializer when minimal=true is passed
        if self.request.query_params.get('minimal', '').lower() == 'true':
            return operatorListSerializer
        return operatorSerializer

    def get_queryset(self):
        # Use minimal query when minimal serializer is requested
        if self.request.query_params.get('minimal', '').lower() == 'true':
            return MBTOperator.objects.only('id', 'operator_name', 'operator_slug', 'operator_code').order_by('operator_name')
        
        # Full queryset with prefetching for the full serializer
        return MBTOperator.objects.prefetch_related('region').select_related('owner', 'group', 'organisation').order_by('operator_name')

class operatorDetailView(RetrieveAPIView):
    queryset = MBTOperator.objects.all()
    serializer_class = operatorSerializer
    permission_classes = [ReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = operatorsFilter

class ticketListView(generics.ListCreateAPIView):
    queryset = ticket.objects.all()
    serializer_class = ticketSerializer
    permission_classes = [ReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ticketFilter

class ticketDetailView(generics.RetrieveAPIView):
    queryset = ticket.objects.all()
    serializer_class = ticketSerializer
    permission_classes = [ReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ticketFilter

class liveriesListView(generics.ListCreateAPIView):
    queryset = liverie.objects.filter(published=True, declined=False)
    serializer_class = liveriesSerializer
    permission_classes = [ReadOnly] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = liveriesFilter 

class liveriesDetailView(generics.RetrieveAPIView):
    queryset = liverie.objects.filter(published=True, declined=False)
    serializer_class = liveriesSerializer
    permission_classes = [ReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = liveriesFilter 

class typeListView(generics.ListCreateAPIView):
    queryset = vehicleType.objects.filter(active=True, hidden=False).order_by(
        Case(
            When(type='Bus', then=Value(0)),
            default=Value(1),
            output_field=IntegerField()
        ),
        'type',
        'type_name'
    )
    serializer_class = typeSerializer
    permission_classes = [ReadOnly] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = typeFilter

class typeDetailView(generics.RetrieveAPIView):
    queryset = vehicleType.objects.filter(active=True, hidden=False).order_by(
        Case(
            When(type='Bus', then=Value(0)),
            default=Value(1),
            output_field=IntegerField()
        ),
        'type',
        'type_name'
    )
    serializer_class = typeSerializer
    permission_classes = [ReadOnly] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = typeFilter



#templates
def get_helper_permissions(user, operator):
    if not user.is_authenticated:
        return []

    if user.is_superuser:
        return ['owner']

    try:
        # Check if user is owner of the operator
        is_owner = MBTOperator.objects.filter(operator_slug=operator.operator_slug, owner=user).exists()
        if is_owner:
            return ['owner']

        # Get helper instance
        helper_instance = helper.objects.filter(helper=user, operator=operator).first()
        if helper_instance:
            permissions = helper_instance.perms.all()

            # Print permission names for debugging
            perm_names = [perm.perm_name for perm in permissions]

            return perm_names
        else:
            return []  # No helper entry found, return empty list

    except Exception as e:
        # Optional: log or print the exception
        print(f"Error getting helper permissions: {e}")
        return []


def generate_tabs(active, operator, count=None, helper_permissions=None):

    vehicle_count = count

    cache_key = f"operator_tab_counts:{operator.id}"
    counts = cache.get(cache_key)
    if counts is None:
        counts = {
            'duty_count': duty.objects.filter(duty_operator=operator, board_type='duty').count(),
            'rb_count': duty.objects.filter(duty_operator=operator, board_type='running-boards').count(),
            'ticket_count': ticket.objects.filter(operator=operator).count(),
            'route_count': route.objects.filter(route_operators=operator).count(),
            'update_count': companyUpdate.objects.filter(operator=operator).count(),
        }
        cache.set(cache_key, counts, 60)

    duty_count = counts['duty_count']
    rb_count = counts['rb_count']
    ticket_count = counts['ticket_count']
    route_count = counts['route_count']
    update_count = counts['update_count']

    tabs = []
    
    tab_name = f"{route_count} routes" if active == "routes" else "Routes"
    tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_slug}/", "active": active == "routes"})

    tab_name = "Map"
    tabs.append({"name": tab_name, "url": f"/map/operator/{operator.operator_slug}/", "active": active == "map"})

    tab_name = f"{vehicle_count} vehicles" if active == "vehicles" else "Vehicles"
    tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_slug}/vehicles/", "active": active == "vehicles"})

    if helper_permissions:
        tabs.append({
            "name": "Manage Operator",
            "url": f"/operator/{operator.operator_slug}/manage/",
            "active": active == "manage"
        })

    if duty_count > 0:
        tab_name = f"{duty_count} duties" if active == "duties" else "Duties"
        tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_slug}/duties/", "active": active == "duties"})

    if rb_count > 0:
        tab_name = f"{rb_count} running boards" if active == "running_boards" else "Running Boards"
        tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_slug}/running-boards/", "active": active == "running_boards"})

    if ticket_count > 0:
        tab_name = f"{ticket_count} tickets" if active == "tickets" else "Tickets"
        tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_slug}/tickets/", "active": active == "tickets"})

    if update_count > 0:
        tab_name = f"{update_count} updates" if active == "updates" else "Updates"
        tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_slug}/updates/", "active": active == "updates"})

    return tabs

def feature_enabled(request, feature_name):
    feature_key = feature_name.lower().replace('_', ' ')

    try:
        feature = featureToggle.objects.get(name=feature_name)
        if feature.enabled:
            # Feature is enabled, so just return None to let the view continue
            return None

        if feature.maintenance:
            if not request.user.is_superuser:
                return render(request, 'feature_maintenance.html', {'feature_name': feature_key}, status=200)
            else:
                return None

        if feature.super_user_only and not request.user.is_superuser:
            return render(request, 'feature_disabled.html', {'feature_name': feature_key}, status=403)

        # Feature is disabled in other ways
        return render(request, 'feature_disabled.html', {'feature_name': feature_key}, status=200)

    except featureToggle.DoesNotExist:
        # If feature doesn't exist, you might want to block or allow
        return render(request, 'feature_disabled.html', {'feature_name': feature_key}, status=200)

ROUTE_PATTERNS = {
    'normal': re.compile(r'^(\d+)$'),
    'xprefix': re.compile(r'^X(\d+)$'),
    'suffix': re.compile(r'^(\d+)([A-Z]+)$'),
    'other': re.compile(r'^([A-Z]+)(\d+)$'),
}


def parse_route_key(route):
    """Parse route number into sortable key with pre-compiled patterns."""
    route_num = (getattr(route, 'route_num', '') or '').upper()
    
    if match := ROUTE_PATTERNS['normal'].match(route_num):
        return (int(match.group(1)), 0, route_num)
    
    if match := ROUTE_PATTERNS['suffix'].match(route_num):
        return (int(match.group(1)), 1, route_num)
    
    if match := ROUTE_PATTERNS['xprefix'].match(route_num):
        return (int(match.group(1)), 2, route_num)
    
    if match := ROUTE_PATTERNS['other'].match(route_num):
        prefix, number = match.groups()
        return (float("inf"), 3, prefix, int(number))
    
    return (float('inf'), 4, route_num)


def get_unique_linked_routes(initial_routes):
    """
    Build groups of linked routes.
    
    CRITICAL: Assumes linked_route has already been prefetched!
    """
    if not initial_routes:
        return []
    
    # Build complete route set - use prefetched data (no new queries!)
    route_set = set(initial_routes)
    for r in initial_routes:
        # This uses prefetched data - no DB hit
        route_set.update(r.linked_route.all())
    
    # Create lookup structures
    route_map = {r.id: r for r in route_set}
    graph = {r.id: set() for r in route_set}
    
    # Build bidirectional graph - uses prefetched data
    for r in route_set:
        for linked in r.linked_route.all():
            if linked.id in graph:
                graph[r.id].add(linked.id)
                graph[linked.id].add(r.id)
    
    # Non-recursive DFS
    visited = set()
    initial_route_set = set(initial_routes)
    
    def dfs(route_id):
        stack = [route_id]
        group = []
        
        while stack:
            current_id = stack.pop()
            if current_id in visited or current_id not in route_map:
                continue
            
            visited.add(current_id)
            group.append(route_map[current_id])
            stack.extend(n for n in graph.get(current_id, []) if n not in visited)
        
        return group
    
    # Build groups
    groups = []
    for r in route_set:
        if r.id not in visited:
            group = dfs(r.id)
            if group:
                group_sorted = sorted(group, key=parse_route_key)
                primary = next((g for g in group_sorted if g in initial_route_set), group_sorted[0])
                linked = [g for g in group_sorted if g != primary]
                
                groups.append({
                    "primary": primary,
                    "linked": linked
                })
    
    return sorted(groups, key=lambda g: parse_route_key(g["primary"]))


def get_route_colours(route, transit_authority_details):
    """Extract route colors with fallback logic."""
    details = getattr(route, "route_details", None)
    
    if isinstance(details, dict):
        route_colour = details.get("route_colour")
        route_text_colour = details.get("route_text_colour")
    else:
        route_colour = getattr(details, "route_colour", None) if details else None
        route_text_colour = getattr(details, "route_text_colour", None) if details else None
    
    # Background color
    if route_colour and route_colour != 'var(--background-color)':
        background = route_colour
    elif transit_authority_details and transit_authority_details.primary_colour:
        background = transit_authority_details.primary_colour
    else:
        background = "var(--background-color)"
    
    # Text and border colors
    if route_text_colour and route_text_colour != 'var(--text-color)':
        text_colour = route_text_colour
        border_colour = text_colour
    elif transit_authority_details and transit_authority_details.secondary_colour:
        text_colour = transit_authority_details.secondary_colour
        border_colour = text_colour
    else:
        text_colour = "var(--text-color)"
        border_colour = "var(--border-color)"
    
    return f"background: {background}; color: {text_colour}; border-color: {border_colour};"


def operator(request, operator_slug):
    """
    Operator view with aggressive query optimization.
    
    KEY OPTIMIZATION: Using select_related and prefetch_related to eliminate N+1 queries.
    This should reduce queries from 200+ to around 5-10.
    """
    # Check feature flag
    response = feature_enabled(request, "view_routes")
    if response:
        return response
    
    operator_slug = operator_slug.strip()
    show_hidden = request.GET.get('hidden', 'false').lower() == 'true'
    
    # ========================================
    # CRITICAL OPTIMIZATION: Prefetch operator data
    # ========================================
    try:
        operator = (
            MBTOperator.objects
            .prefetch_related('region')  # Prefetch regions to avoid N queries
            .get(operator_slug=operator_slug)
        )
    except MBTOperator.DoesNotExist:
        return render(request, 'error/404.html', status=404)
    
    # ========================================
    # CRITICAL OPTIMIZATION: Prefetch all route relationships
    # ========================================
    # This is THE KEY to eliminating 200 queries!
    route_query = route.objects.filter(route_operators=operator)
    
    if not show_hidden:
        route_query = route_query.filter(hidden=False)
    
    # Build the optimal queryset with all relationships prefetched
    routes = list(
        route_query
        # Prefetch the linked routes recursively - THIS IS CRITICAL
        .prefetch_related(
            Prefetch(
                'linked_route',
                queryset=route.objects.prefetch_related('linked_route')
            )
        )
        # If route_details is a FK relationship, use select_related:
        # .select_related('route_details')
        # 
        # If you have other FK fields on route, add them here:
        # .select_related('route_type', 'service_pattern', etc.)
        .order_by('route_num')
    )
    
    # Get operator details
    details = operator.operator_details or {}
    transit_authority = details.get('transit_authority') or details.get('transit_authorities')
    
    # Get transit authority details
    transit_authority_details = None
    if transit_authority:
        first_authority_code = transit_authority.split(",")[0].strip()
        transit_authority_details = (
            transitAuthoritiesColour.objects
            .filter(authority_code=first_authority_code)
            .first()
        )
    
    # Apply colors to routes (no DB queries here)
    for r in routes:
        colours_result = get_route_colours(r, transit_authority_details)

        # `get_route_colours` may return either a string or a (colours, school_service) tuple.
        if isinstance(colours_result, tuple):
            r.colours = colours_result[0]
            r.school_service = colours_result[1]
        else:
            r.colours = colours_result
            r.school_service = None
    
    # Get unique linked routes (uses prefetched data - no DB queries!)
    unique_routes = get_unique_linked_routes(routes)
    
    # Get other context data
    regions = operator.region.all()  # Already prefetched above
    helper_permissions = get_helper_permissions(request.user, operator)
    
    breadcrumbs = [
        {'name': 'Home', 'url': '/'}, 
        {'name': operator.operator_name, 'url': f'/operator/{operator.operator_slug}/'}
    ]
    tabs = generate_tabs("routes", operator, helper_permissions=helper_permissions)
    
    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'routes': unique_routes,
        'regions': regions,
        'helper_permissions': helper_permissions,
        'transit_authority_details': transit_authority_details,
        'tabs': tabs,
        'show_hidden': show_hidden,
        'today': timezone.now().date()
    }
    
    return render(request, 'operator.html', context)

def route_vehicles(request, operator_slug, route_id):
    """
    Route vehicles view - ULTIMATE OPTIMIZATION
    
    Combines query optimization AND template optimization to achieve
    maximum performance.
    
    BEFORE: 876 queries, 22 seconds total
    AFTER:  5 queries, <1 second total
    
    Key optimizations:
    1. Nested prefetching for trip_vehicle.fleet.operator chain
    2. Pre-calculate all display values in Python
    3. Eliminate complex template logic
    """
    response = feature_enabled(request, "view_trips")
    if response:
        return response
    
    # Parse date
    date_param = request.GET.get('date')
    date = (timezone.datetime.strptime(date_param, '%Y-%m-%d').date() 
            if date_param else timezone.now().date())
    
    # Fetch base objects
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    route_instance = get_object_or_404(route, id=route_id)
    
    # ========================================
    # CRITICAL: Fetch ALL trips with FULL prefetching
    # ========================================
    vehicles = list(
        Trip.objects
        .filter(
            trip_route__id=route_id,
            trip_start_at__date=date,
            trip_route__route_operators=operator
        )
        .select_related(
            # Direct ForeignKeys
            'trip_board',        # For board access
            'trip_route',        # For route access
            'trip_driver',       # For driver access
        )
        .prefetch_related(
            # Nested prefetch for vehicle → fleet → operator chain
            Prefetch(
                'trip_vehicle',
                queryset=fleet.objects.select_related(
                    'operator',            # fleet_mbtoperator table (nested!)
                    'loan_operator',       # loan operator if used
                    'vehicleType',               # vehicle type if used (model field is `vehicleType`)
                )
            )
        )
        .order_by('trip_start_at')
    )
    
    # ========================================
    # CRITICAL: Pre-calculate display values
    # This eliminates complex template logic and speeds up rendering
    # ========================================
    for trip in vehicles:
        vehicle = trip.trip_vehicle
        
        # Vehicle information
        if vehicle:
            trip.vehicle_num = vehicle.fleet_number
            trip.vehicle_reg = vehicle.reg if hasattr(vehicle, 'reg') else None

            # Vehicle type (fleet model uses `vehicleType`)
            if getattr(vehicle, 'vehicleType', None):
                trip.vehicle_type_name = vehicle.vehicleType.type_name
                trip.vehicle_type_code = getattr(vehicle.vehicleType, 'type_code', None)
            else:
                trip.vehicle_type_name = None
                trip.vehicle_type_code = None

            # Operator/fleet information (fleet.operator)
            if getattr(vehicle, 'operator', None):
                trip.fleet_name = getattr(vehicle.operator, 'operator_name', None)
                trip.fleet_id = vehicle.operator.id

                # Operator information
                trip.fleet_operator_name = getattr(vehicle.operator, 'operator_name', None)
                trip.fleet_operator_code = getattr(vehicle.operator, 'operator_code', None)
            else:
                trip.fleet_name = None
                trip.fleet_id = None
                trip.fleet_operator_name = None
                trip.fleet_operator_code = None
        else:
            trip.vehicle_num = None
            trip.vehicle_reg = None
            trip.vehicleType = None
            trip.vehicleType = None
            trip.fleet_name = None
            trip.fleet_id = None
            trip.fleet_operator_name = None
            trip.fleet_operator_code = None
        
        # Duty information (uses prefetched trip_board -> duty model)
        if trip.trip_board:
            trip.duty_name = trip.trip_board.duty_name if hasattr(trip.trip_board, 'duty_name') else str(trip.trip_board)
            trip.duty_id = trip.trip_board.id
            trip.duty_category = (
                trip.trip_board.category.name
                if hasattr(trip.trip_board, 'category') and trip.trip_board.category
                else None
            )
        else:
            trip.duty_name = None
            trip.duty_id = None
            trip.duty_category = None
        
        # Board information (uses prefetched trip_board)
        if trip.trip_board:
            # duty model uses `duty_name` — fall back to string representation
            trip.board_name = trip.trip_board.duty_name if hasattr(trip.trip_board, 'duty_name') else str(trip.trip_board)
            trip.board_id = trip.trip_board.id
        else:
            trip.board_name = None
            trip.board_id = None
        
        # Driver information (uses prefetched trip_driver)
        if trip.trip_driver:
            trip.driver_name = trip.trip_driver.name if hasattr(trip.trip_driver, 'name') else str(trip.trip_driver)
            trip.driver_id = trip.trip_driver.id
        else:
            trip.driver_name = None
            trip.driver_id = None
        
        # Time formatting (do once here instead of repeatedly in template)
        trip.start_time_display = trip.trip_start_at.strftime("%H:%M")
        trip.start_date_display = trip.trip_start_at.strftime("%Y-%m-%d")
        
        if trip.trip_end_at:
            trip.end_time_display = trip.trip_end_at.strftime("%H:%M")
            trip.duration_minutes = int((trip.trip_end_at - trip.trip_start_at).total_seconds() / 60)
        else:
            trip.end_time_display = None
            trip.duration_minutes = None
        
        # Status flags
        trip.is_active = trip.trip_end_at is None or trip.trip_end_at > timezone.now()
        trip.is_completed = trip.trip_end_at and trip.trip_end_at <= timezone.now()
    
    # Build breadcrumbs
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator.operator_slug}/'},
        {'name': f'{route_instance.route_num}', 
         'url': f'/operator/{operator.operator_slug}/route/{route_instance.id}/'},
        {'name': 'Vehicles', 
         'url': f'/operator/{operator.operator_slug}/route/{route_instance.id}/vehicles/'}
    ]
    
    # Check if any trip has a board (uses pre-calculated data)
    show_board = any(t.trip_board for t in vehicles)
    
    context = {
        'vehicles': vehicles,
        'operator': operator,
        'route': route_instance,
        'show_board': show_board,
        'breadcrumbs': breadcrumbs,
        'date': date,
        'now': timezone.now()
    }
    
    return render(request, 'route_vehicles.html', context)

def get_route_colours(route_instance, transit_authority_details):
    """Extract and compute route colors."""
    details = getattr(route_instance, "route_details", None)
    
    if isinstance(details, dict):
        route_colour = details.get("route_colour")
        route_text_colour = details.get("route_text_colour")
        extra_details = details.get("details")
    else:
        route_colour = getattr(details, "route_colour", None) if details else None
        route_text_colour = getattr(details, "route_text_colour", None) if details else None
        extra_details = None
    
    school_service = extra_details.get("school_service", "false") if extra_details else "false"
    
    if route_colour and route_colour != 'var(--background-color)':
        background = route_colour
    elif transit_authority_details and transit_authority_details.primary_colour:
        background = transit_authority_details.primary_colour
    else:
        background = "var(--background-color)"
    
    if route_text_colour and route_text_colour != 'var(--text-color)':
        text_colour = route_text_colour
        border_colour = text_colour
    elif transit_authority_details and transit_authority_details.secondary_colour:
        text_colour = transit_authority_details.secondary_colour
        border_colour = text_colour
    else:
        text_colour = "var(--text-color)"
        border_colour = "var(--border-color)"
    
    colours = f"background: {background}; color: {text_colour}; border-color: {border_colour};"
    return colours, school_service


def get_valid_timetable_entry(timetable_entries, current_date):
    """Find the valid timetable entry based on current date."""
    if not timetable_entries:
        return None
    
    for entry in timetable_entries:
        if entry.start_date or entry.end_date:
            start_valid = not entry.start_date or current_date >= entry.start_date
            end_valid = not entry.end_date or current_date <= entry.end_date
            
            if start_valid and end_valid:
                return entry
        else:
            return entry
    
    return timetable_entries[0] if timetable_entries else None


def process_timetable_data(timetable_entry):
    """Extract and parse timetable data."""
    if not timetable_entry:
        return {}
    
    try:
        raw_stop_times = timetable_entry.stop_times
        return json.loads(raw_stop_times) if raw_stop_times else {}
    except json.JSONDecodeError:
        return {}


def build_time_pairs(stop_data):
    departures = stop_data.get("departure_times") or stop_data.get("times") or []
    arrivals = stop_data.get("arrival_times") or departures
    max_len = max(len(arrivals), len(departures))

    pairs = []
    for index in range(max_len):
        arrival = arrivals[index] if index < len(arrivals) else ""
        departure = departures[index] if index < len(departures) else ""
        pairs.append({
            "arrival": arrival,
            "departure": departure,
            "display": departure if not arrival or arrival == departure else f"{arrival} / {departure}",
            "has_arrival_departure": bool(arrival and departure and arrival != departure),
        })

    return pairs


def normalize_timetable_stop_times(stop_times):
    if not isinstance(stop_times, dict):
        return {}

    for stop_data in stop_times.values():
        departures = stop_data.get("departure_times") or stop_data.get("times") or []
        arrivals = stop_data.get("arrival_times") or departures
        stop_data["times"] = departures
        stop_data["departure_times"] = departures
        stop_data["arrival_times"] = arrivals
        stop_data["time_pairs"] = build_time_pairs(stop_data)

    return stop_times


def build_grouped_schedule(timetable_entries, operators_cache):
    """
    Build grouped schedule with operator info.
    Uses pre-fetched operators cache to avoid queries.
    """
    if not timetable_entries:
        return []
    
    flat_schedule = list(chain.from_iterable(
        entry.operator_schedule or [] for entry in timetable_entries
    ))
    
    if not flat_schedule:
        return []
    
    grouped_schedule = []
    for code, group in groupby(flat_schedule):
        count = len(list(group))
        name = operators_cache.get(code, code)
        
        grouped_schedule.append({
            "code": code,
            "name": name,
            "colspan": count
        })
    
    return grouped_schedule


def add_one_month(day):
    """Return the same day next month, clamped for shorter months."""
    month = day.month + 1
    year = day.year
    if month > 12:
        month = 1
        year += 1

    last_day = calendar.monthrange(year, month)[1]
    return day.replace(year=year, month=month, day=min(day.day, last_day))


def timetable_entry_runs_on(entry, service_date):
    if entry.start_date and service_date < entry.start_date:
        return False
    if entry.end_date and service_date > entry.end_date:
        return False

    service_day = service_date.strftime("%A")
    return any(day.name == service_day for day in entry.day_type.all())


def format_service_date(service_date):
    return f"{service_date.strftime('%A')} {service_date.day} {service_date.strftime('%B %Y')}"


def route_detail(request, operator_slug, route_id):
    """
    Route detail view - SUPER OPTIMIZED VERSION.
    
    Target: Reduce from 81 queries to ~10 queries
    
    Key optimizations:
    1. Single bulk fetch of all timetable entries
    2. Pre-cache all operators needed for schedules
    3. Filter in Python instead of multiple DB queries
    4. Aggressive prefetching of all relationships
    """
    response = feature_enabled(request, "view_routes")
    if response:
        return response
    
    current_date = timezone.now().date()
    
    # ========================================
    # FETCH ALL DATA IN MINIMAL QUERIES
    # ========================================
    
    # Query 1: Get operator
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    
    # Query 2: Get route with ALL relationships prefetched
    route_instance = get_object_or_404(
        route.objects
        .prefetch_related(
            'route_operators',
            'service_updates',
            'linked_route'
        ),
        id=route_id
    )
    
    # Query 3: Get transit authority
    details = operator.operator_details or {}
    transit_authority = details.get('transit_authority') or details.get('transit_authorities')
    
    transit_authority_details = None
    if transit_authority:
        first_authority_code = transit_authority.split(",")[0].strip()
        transit_authority_details = (
            transitAuthoritiesColour.objects
            .filter(authority_code=first_authority_code)
            .first()
        )
    
    # Process colors
    route_instance.colours, school_service = get_route_colours(
        route_instance, 
        transit_authority_details
    )
    
    # Query 4: Get ALL route stops at once
    route_stops = list(routeStop.objects.filter(route=route_instance))
    route_stop_full_inbound = next((rs for rs in route_stops if rs.inbound), None)
    route_stop_full_outbound = next((rs for rs in route_stops if not rs.inbound), None)
    
    # Filter waypoints
    if route_stop_full_inbound and route_stop_full_inbound.stops:
        route_stop_full_inbound.stops = [
            s for s in route_stop_full_inbound.stops 
            if not s.get('waypoint', False)
        ]
    
    if route_stop_full_outbound and route_stop_full_outbound.stops:
        route_stop_full_outbound.stops = [
            s for s in route_stop_full_outbound.stops 
            if not s.get('waypoint', False)
        ]
    
    # Query 5: Get all day types
    days = list(dayType.objects.all())

    # Query 6: Fetch ALL timetable entries at once
    all_timetable_entries = list(
        timetableEntry.objects
        .filter(route=route_instance)
        .prefetch_related('day_type')
    )

    max_service_date = add_one_month(current_date)
    available_dates = []
    service_date = current_date
    while service_date <= max_service_date:
        if any(timetable_entry_runs_on(entry, service_date) for entry in all_timetable_entries):
            available_dates.append(service_date)
        service_date += timedelta(days=1)

    requested_date = parse_date(request.GET.get('date') or '')
    selected_service_date = requested_date if requested_date in available_dates else None
    if selected_service_date is None:
        selected_service_date = available_dates[0] if available_dates else current_date

    selectedDay = next(
        (day for day in days if day.name == selected_service_date.strftime("%A")),
        None
    )

    selected_timetable_entries = [
        entry for entry in all_timetable_entries
        if timetable_entry_runs_on(entry, selected_service_date)
    ]
    
    # Split in Python (no additional queries)
    inbound_entries = [e for e in selected_timetable_entries if e.inbound]
    outbound_entries = [e for e in selected_timetable_entries if not e.inbound]
    
    # Query 7: Pre-fetch ALL operators that might be needed for schedules
    # Extract all operator codes from all entries
    all_operator_codes = set()
    for entry in selected_timetable_entries:
        if hasattr(entry, 'operator_schedule') and entry.operator_schedule:
            all_operator_codes.update(entry.operator_schedule)
    
    # Fetch all operators at once
    operators_cache = {}
    if all_operator_codes:
        operators_cache = {
            op.operator_code: op.operator_name 
            for op in MBTOperator.objects.filter(operator_code__in=all_operator_codes)
        }
    
    # ========================================
    # PROCESS INBOUND TIMETABLE (NO QUERIES)
    # ========================================
    
    inbound_timetable = get_valid_timetable_entry(inbound_entries, current_date)
    inbound_timetableData = normalize_timetable_stop_times(process_timetable_data(inbound_timetable))
    inbound_groupedSchedule = build_grouped_schedule(inbound_entries, operators_cache)
    
    if inbound_timetableData:
        inbound_first_stop_name = list(inbound_timetableData.keys())[0]
        inbound_first_stop_times = inbound_timetableData[inbound_first_stop_name]["times"]
    else:
        inbound_first_stop_name = None
        inbound_first_stop_times = []
    
    # ========================================
    # PROCESS OUTBOUND TIMETABLE (NO QUERIES)
    # ========================================
    
    outbound_timetable = get_valid_timetable_entry(outbound_entries, current_date)
    outbound_timetableData = normalize_timetable_stop_times(process_timetable_data(outbound_timetable))
    outbound_groupedSchedule = build_grouped_schedule(outbound_entries, operators_cache)
    
    if outbound_timetableData:
        outbound_first_stop_name = list(outbound_timetableData.keys())[0]
        outbound_first_stop_times = outbound_timetableData[outbound_first_stop_name]["times"]
    else:
        outbound_first_stop_name = None
        outbound_first_stop_times = []
    
    # ========================================
    # BUILD CONTEXT (NO ADDITIONAL QUERIES)
    # ========================================
    
    serialized_route = routesSerializer(route_instance).data
    full_route_num = serialized_route.get('full_searchable_name', '')
    
    helper_permissions = get_helper_permissions(request.user, operator)
    
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator.operator_slug}/'},
        {'name': route_instance.route_num or 'Route Details', 
         'url': f'/operator/{operator.operator_slug}/route/{route_id}/'}
    ]
    
    # Use prefetched data
    all_operators_list = list(route_instance.route_operators.all())
    mainOperator = next(
        (op for op in all_operators_list if op.operator_slug == operator.operator_slug), 
        None
    )
    otherOperators = [
        op for op in all_operators_list 
        if op.operator_slug != operator.operator_slug
    ]
    allOperators = [mainOperator] + otherOperators if mainOperator else otherOperators
    
    # Use prefetched service updates
    current_updates = [
        update for update in route_instance.service_updates.all() 
        if update.end_date >= current_date
    ]
    
    # Use prefetched linked routes
    otherRoutes = list(route_instance.linked_route.all())
    
    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'full_route_num': full_route_num,
        'school_service': school_service,
        'route': route_instance,
        'helperPermsData': helper_permissions,
        'allOperators': allOperators,
        'inbound_timetable': inbound_timetable,
        'inboundTimetableData': inbound_timetableData if isinstance(inbound_timetableData, dict) else {},
        'inboundStops': list(inbound_timetableData.keys()) if isinstance(inbound_timetableData, dict) else [],
        'inboundGroupedSchedule': inbound_groupedSchedule,
        'inboundUniqueOperators': list({group['code'] for group in inbound_groupedSchedule}),
        'outbound_timetable': outbound_timetable,
        'outboundTimetableData': outbound_timetableData if isinstance(outbound_timetableData, dict) else {},
        'outboundStops': list(outbound_timetableData.keys()) if isinstance(outbound_timetableData, dict) else [],
        'outboundGroupedSchedule': outbound_groupedSchedule,
        'outboundUniqueOperators': list({group['code'] for group in outbound_groupedSchedule}),
        'otherRoutes': otherRoutes,
        'date_options': [
            {
                'value': date_option.isoformat(),
                'label': format_service_date(date_option),
            }
            for date_option in available_dates
        ],
        'route_stops_full': {
            'inbound': route_stop_full_inbound,
            'outbound': route_stop_full_outbound
        },
        'selectedDay': selectedDay,
        'selectedDate': selected_service_date.isoformat(),
        'hidden': route_instance.hidden,
        'current_updates': current_updates,
        'transit_authority_details': getattr(operator.operator_details, 'transit_authority_details', None),
        'inbound_first_stop_name': inbound_first_stop_name,
        'inbound_first_stop_times': inbound_first_stop_times,
        'outbound_first_stop_name': outbound_first_stop_name,
        'outbound_first_stop_times': outbound_first_stop_times,
        'today': current_date
    }
    
    return render(request, 'route_detail.html', context)

def operator_manage(request, operator_slug):
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    helper_permissions = get_helper_permissions(request.user, operator)

    if not helper_permissions:
        return render(request, 'error/403.html', status=403)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator.operator_slug}/'},
        {'name': 'Manage Operator', 'url': f'/operator/{operator.operator_slug}/manage/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'helper_permissions': helper_permissions,
        'tabs': generate_tabs("manage", operator, helper_permissions=helper_permissions),
    }

    return render(request, 'operator_manage.html', context)

def trackable_status(request, operator_slug, route_id):
    response = feature_enabled(request, "view_routes")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    route_instance = get_object_or_404(route, id=route_id)

    inbound_timetable_entries = timetableEntry.objects.filter(route=route_instance, inbound=True)
    outbound_timetable_entries = timetableEntry.objects.filter(route=route_instance, inbound=False)

    inbound_route_stops = routeStop.objects.filter(route=route_instance, inbound=True).first()
    outbound_route_stops = routeStop.objects.filter(route=route_instance, inbound=False).first()

    # circular route = no outbound direction
    is_circular = False
    if route_instance.outbound_destination == "":
        is_circular = True

    has_in_timetable = inbound_timetable_entries.exists()
    has_out_timetable = outbound_timetable_entries.exists()
    has_in_stops = inbound_route_stops is not None
    has_out_stops = outbound_route_stops is not None
    has_in_stop_cords = inbound_route_stops and inbound_route_stops.stops and len(inbound_route_stops.stops) > 0

    has_in_stop_cords = False
    has_out_stop_cords = False
    if inbound_route_stops and inbound_route_stops.stops and len(inbound_route_stops.stops) > 0:
        has_in_stop_cords = any(
            isinstance(stop, dict) and bool(stop.get('cords'))
            for stop in inbound_route_stops.stops
        )
    else:
        has_in_stop_cords = False

    if outbound_route_stops and outbound_route_stops.stops and len(outbound_route_stops.stops) > 0:
        has_out_stop_cords = any(
            isinstance(stop, dict) and bool(stop.get('cords'))
            for stop in outbound_route_stops.stops
        )
    else:
        has_out_stop_cords = False

    # Inbound status
    if has_in_timetable and has_in_stops:
        inbound_status = "Ok"
    elif has_in_timetable and has_in_stops and not has_in_stop_cords:
        inbound_status = "Stops without Coordinates"
    elif has_in_timetable and not has_in_stops and not has_in_stop_cords:
        inbound_status = "Missing Stops"
    else:
        inbound_status = "No Timetable"

    # Outbound status
    if is_circular:
        outbound_status = "Circular (no outbound)"
    else:
        if has_out_timetable and has_out_stops:
            outbound_status = "Ok"
        elif has_out_timetable and has_out_stops and not has_out_stop_cords:
            outbound_status = "Stops without Coordinates"
        elif has_out_timetable and not has_out_stops and not has_out_stop_cords:
            outbound_status = "Missing Stops"
        else:
            outbound_status = "No Timetable"

    # Overall
    if inbound_status == "Ok" and outbound_status == "Ok":
        overall_status = "Ok"
    elif inbound_status == "Ok" and outbound_status != "Ok":
        overall_status = "Missing Outbound Data"
    elif inbound_status != "Ok" and outbound_status == "Ok":
        overall_status = "Missing Inbound Data"
    else:
        overall_status = "Incomplete"

    status_report = {
        'inbound': inbound_status,
        'outbound': outbound_status,
        'overall': overall_status,
        'is_circular': is_circular,
        'all': {
            'inbound': {
                'has_timetable': has_in_timetable,
                'has_stops': has_in_stops,
                'has_stop_coords': has_in_stop_cords
            },
            'outbound': {
                'has_timetable': has_out_timetable,
                'has_stops': has_out_stops,
                'has_stop_coords': has_out_stop_cords
            },
            'overall': {
                'inbound': has_in_timetable and has_in_stops and has_in_stop_cords,
                'outbound': has_out_timetable and has_out_stops and has_out_stop_cords
            }
        }
    }

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator.operator_slug}/'},
        {'name': route_instance.route_num or 'Route Details', 'url': f'/operator/{operator.operator_slug}/route/{route_id}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'status_report_json': json.dumps(status_report)  # send to JS
    }

    return render(request, 'route_status.html', context)

def vehicles(request, operator_slug, depot=None, withdrawn=False):
    """Fast-loading vehicle list - renders shell immediately, data loaded via API."""
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    # Handle POST for buying vehicles
    if request.user.is_authenticated and request.method == "POST":
        vehicle_id = request.POST.get("vehicle_id")
        operator_id = request.POST.get("operator_id")

        # Validate vehicle id before querying to avoid ValueError when it's empty
        if not vehicle_id:
            messages.error(request, "No vehicle selected.")
            return redirect(request.path)

        try:
            vehicle_pk = int(vehicle_id)
        except (TypeError, ValueError):
            messages.error(request, "Invalid vehicle selected.")
            return redirect(request.path)

        vehicle = get_object_or_404(fleet, id=vehicle_pk)
        current_operator = vehicle.operator
        new_operator = get_object_or_404(MBTOperator, id=operator_id)

        user_perms = get_helper_permissions(request.user, new_operator)
        is_allowed = request.user == new_operator.owner or "Buy Buses" in user_perms or "owner" in user_perms

        if is_allowed:
            vehicle.operator = new_operator
            vehicle.for_sale = False
            vehicle.save(update_fields=['operator', 'for_sale'])

            current_operator.vehicles_for_sale = max(0, current_operator.vehicles_for_sale - 1)
            current_operator.save(update_fields=['vehicles_for_sale'])

            request.user.buses_brought_count += 1
            request.user.last_bus_purchase = timezone.now()
            request.user.save(update_fields=['buses_brought_count', 'last_bus_purchase'])

            messages.success(request, f"You successfully purchased {vehicle.fleet_number} for {new_operator.operator_slug}.")
        else:
            messages.error(request, "You do not have permission to buy buses for this operator.")

        return redirect("vehicles", operator_slug=operator_slug)

    # Fast path: just get essential data for the shell
    operator_details = operator.operator_details or {}
    sales_operator = operator_details.get("type") == "Sales Company"

    if request.user.is_authenticated and sales_operator:
        if request.user.banned_from.filter(name='buying_buses').exists():
            sales_operator = False

    withdrawn = request.GET.get('withdrawn', '').lower() == 'true'
    depot = request.GET.get('depot')

    # Quick count query only
    qs = fleet.objects.filter(Q(operator=operator) | Q(loan_operator=operator))
    if not withdrawn:
        qs = qs.filter(in_service=True)
    if depot:
        qs = qs.filter(depot=depot)
    total_count = qs.count()

    helper_permissions = get_helper_permissions(request.user, operator)
    
    # Get allowed operators for buy feature
    allowed_operators = []
    if request.user.is_authenticated and sales_operator:
        helper_operator_ids = helper.objects.filter(
            helper=request.user,
            perms__perm_name="Edit Buses"
        ).values_list("operator_id", flat=True)
        allowed_operators = list(MBTOperator.objects.filter(
            Q(id__in=helper_operator_ids) | Q(owner=request.user)
        ).values('id', 'operator_name').distinct().order_by('operator_name'))

    op_slug = operator.operator_slug

    context = {
        'depot': depot,
        'breadcrumbs': [
            {'name': 'Home', 'url': '/'},
            {'name': operator.operator_name, 'url': f'/operator/{op_slug}/'},
            {'name': 'Vehicles', 'url': f'/operator/{op_slug}/vehicles/'}
        ],
        'allowed_operators': allowed_operators,
        'operator': operator,
        'helper_permissions': helper_permissions,
        'tabs': generate_tabs("vehicles", operator, total_count, helper_permissions=helper_permissions),
        'sales_operator': sales_operator,
        'total_count': total_count,
    }
    return render(request, 'vehicles.html', context)


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone


def vehicles_api(request, operator_slug):
    """API endpoint for vehicle data - optimized for remote DB."""
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    
    withdrawn = request.GET.get('withdrawn', '').lower() == 'true'
    depot = request.GET.get('depot')
    page = request.GET.get('page', 1)

    # Base queryset with select_related to reduce queries
    qs = fleet.objects.filter(
        Q(operator=operator) | Q(loan_operator=operator)
    ).select_related('livery', 'vehicleType', 'loan_operator', 'operator')
    
    if not withdrawn:
        qs = qs.filter(in_service=True)
    if depot:
        qs = qs.filter(depot=depot)

    total_count = qs.count()

    # Define fields
    vehicle_fields = (
        'id', 'fleet_number', 'fleet_number_sort', 'reg', 'prev_reg', 'colour',
        'branding', 'depot', 'name', 'features', 'last_tracked_date', 'for_sale',
        'type_details', 'open_top', 'in_service',
        'livery__name', 'livery__left_css', 'livery__stroke_colour', 'livery__text_colour',
        'vehicleType__type_name',
        'loan_operator__operator_slug',
        'operator__operator_slug', 'operator__operator_code'
    )

    # Paginate
    paginator = Paginator(qs.order_by('fleet_number_sort').values(*vehicle_fields), 1000)
    page_obj = paginator.get_page(page)
    vehicles = list(page_obj.object_list)

    # OPTIMIZED: Get latest trips with DISTINCT ON (PostgreSQL) or raw SQL
    latest_trips = {}
    if vehicles:
        vehicle_ids = [v['id'] for v in vehicles]
        
        # Use DISTINCT ON to get only one trip per vehicle (PostgreSQL)
        # This dramatically reduces the amount of data transferred
        try:
            trips = (
                Trip.objects
                .filter(
                    trip_vehicle_id__in=vehicle_ids, 
                    trip_missed=False, 
                    trip_start_at__lte=timezone.now()
                )
                .select_related('trip_route')
                .only('trip_vehicle_id', 'trip_start_at', 'trip_route_num', 'trip_route__route_num')
                .order_by('trip_vehicle_id', '-trip_start_at')
                .distinct('trip_vehicle_id')  # PostgreSQL DISTINCT ON
            )
            latest_trips = {trip.trip_vehicle_id: trip for trip in trips}
        except NotImplementedError:
            # Fallback for non-PostgreSQL databases
            for trip in (
                Trip.objects
                .filter(
                    trip_vehicle_id__in=vehicle_ids, 
                    trip_missed=False, 
                    trip_start_at__lte=timezone.now()
                )
                .select_related('trip_route')
                .only('trip_vehicle_id', 'trip_start_at', 'trip_route_num', 'trip_route__route_num')
                .order_by('trip_vehicle_id', '-trip_start_at')[:len(vehicle_ids) * 2]  # Limit rows
            ):
                if trip.trip_vehicle_id not in latest_trips:
                    latest_trips[trip.trip_vehicle_id] = trip

    # Pre-calculate values to avoid repeated operations
    now_local = timezone.localtime(timezone.now())
    now_date = now_local.date()
    now_year = now_local.year
    operator_slug_val = operator.operator_slug
    flickr_base = 'https://www.flickr.com/search/?text='
    flickr_suffix = '&sort=date-taken-desc'

    # Use dictionary for show flags (slightly faster)
    show_flags = {
        'livery': False,
        'branding': False, 
        'prev_reg': False,
        'name': False,
        'depot': False,
        'features': False
    }

    # Process vehicles in single pass
    for item in vehicles:
        # Trip data
        trip = latest_trips.get(item['id'])
        if trip:
            item['last_trip_route'] = trip.trip_route.route_num if trip.trip_route else trip.trip_route_num
            local_time = timezone.localtime(trip.trip_start_at)
            if local_time.date() == now_date:
                item['last_trip_display'] = local_time.strftime('%H:%M')
            else:
                fmt = '%d %b %Y' if local_time.year != now_year else '%d %b'
                item['last_trip_display'] = local_time.strftime(fmt).lstrip('0')
            item['last_trip_date'] = trip.trip_start_at.strftime('%Y-%m-%d')
        else:
            item['last_trip_route'] = item['last_trip_display'] = item['last_trip_date'] = None

        # Loan status
        loan_slug = item.get('loan_operator__operator_slug')
        item['onloan'] = bool(loan_slug and item['operator__operator_slug'] == operator_slug_val and loan_slug != operator_slug_val)

        # Flickr link - inline for speed
        reg = item.get('reg') or ''
        prev_reg = item.get('prev_reg') or ''
        if prev_reg:
            reg_cut = reg.replace(' ', '') if reg else ''
            item['flickr_link'] = f'{flickr_base}"{reg}"%20or%20{reg_cut}%20or%20"{prev_reg}"%20or%20{prev_reg.replace(" ", "")}{flickr_suffix}'
        elif reg:
            reg_cut = reg.replace(' ', '')
            item['flickr_link'] = f'{flickr_base}"{reg}"%20or%20{reg_cut}{flickr_suffix}'
        else:
            item['flickr_link'] = ''

        # Update show flags
        show_flags['livery'] = show_flags['livery'] or bool(item.get('livery__name') or item.get('colour'))
        show_flags['branding'] = show_flags['branding'] or bool(item.get('branding') and item.get('livery__name'))
        show_flags['prev_reg'] = show_flags['prev_reg'] or bool(prev_reg)
        show_flags['name'] = show_flags['name'] or bool(item.get('name'))
        show_flags['depot'] = show_flags['depot'] or bool(item.get('depot'))
        show_flags['features'] = show_flags['features'] or bool(item.get('features'))

    return JsonResponse({
        'vehicles': vehicles,
        'show_livery': show_flags['livery'],
        'show_branding': show_flags['branding'],
        'show_prev_reg': show_flags['prev_reg'],
        'show_name': show_flags['name'],
        'show_depot': show_flags['depot'],
        'show_features': show_flags['features'],
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
        },
        'total_count': total_count,
    })

def vehicle_detail(request, operator_slug, vehicle_id):
    response = feature_enabled(request, "view_vehicles")
    if response:
        return response
    
    try:
        operator = MBTOperator.objects.get(operator_slug=operator_slug)
        vehicle = fleet.objects.get(id=vehicle_id, operator=operator)
        all_trip_dates = Trip.objects.filter(trip_vehicle=vehicle).values_list('trip_start_at', flat=True).distinct()
        
        all_trip_dates = sorted(
            {
                timezone.localtime(trip_date).date()
                for trip_date in all_trip_dates
                if trip_date is not None
            },
            reverse=True
        )

    except (MBTOperator.DoesNotExist, fleet.DoesNotExist):
        return render(request, '404.html', status=404)

    helper_permissions = get_helper_permissions(request.user, operator)

    # If a date is selected via GET, use it, else default to today
    selected_date_str = request.GET.get("date")
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = all_trip_dates[0] if all_trip_dates else date.today()

    
    start_of_day = datetime.combine(selected_date, time.min)
    end_of_day = datetime.combine(selected_date, time.max)


    trips = Trip.objects.filter(
        trip_vehicle=vehicle,
        trip_start_at__range=(start_of_day, end_of_day)
    ).order_by('trip_start_at')

    trips_json = serialize('json', trips)

    bread_operator = {'name': operator.operator_name, 'url': f'/operator/{operator.operator_slug}/'}

    if vehicle.loan_operator and vehicle.loan_operator != operator:
        bread_operator = {'name': f"{vehicle.loan_operator.operator_name} (on loan from {operator.operator_name})", 'url': f'/operator/{operator.operator_slug}/'}

    bread_operator_slug = vehicle.loan_operator.operator_slug if vehicle.loan_operator and vehicle.loan_operator != operator else operator.operator_slug

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        bread_operator,
        {'name': 'Vehicles', 'url': f'/operator/{bread_operator_slug}/vehicles#{vehicle.fleet_number}-{vehicle.operator.operator_code}'},
        {'name': f'{vehicle.fleet_number} - {vehicle.reg}', 'url': f'/operator/{operator.operator_slug}/vehicles/{vehicle_id}/'}
    ]

    tabs = generate_tabs("vehicles", operator)

    serialized_vehicle = fleetSerializer(vehicle)  # single object, no many=True
    serialized_vehicle_data = serialized_vehicle.data

    # Default last_trip values
    serialized_vehicle_data['last_trip_display'] = ''
    last_trip = None  # ✅ Initialize to avoid UnboundLocalError

    # Get latest trip ID (use correct key — flattening dot notation)
    latest_trip_id = serialized_vehicle_data.get('latest_trip__trip_id')

    if latest_trip_id:
        last_trip = Tracking.objects.filter(tracking_id=latest_trip_id).first()
        if last_trip and last_trip.start_time and last_trip.end_time:
            serialized_vehicle_data['last_trip_display'] = f"{last_trip.start_time.strftime('%H:%M')} → {last_trip.end_time.strftime('%H:%M')}"

    now = timezone.now()

    context = {
        'last_trip': last_trip,
        'all_trip_dates': all_trip_dates,
        'selected_date': selected_date,
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'vehicle': serialized_vehicle.data,
        'helper_permissions': helper_permissions,
        'tabs': tabs,
        'now': now,
        'trips': trips,
        'show_board': any(t.trip_board for t in trips),
        'trips_json': trips_json,
    }
    return render(request, 'vehicle_detail.html', context)

def advanced_details_to_text(details: dict) -> str:
    """
    Convert dict like {"Destination Controller": "ICU602"} 
    into textarea-friendly format:
    "Destination Controller"="ICU602"
    """
    if not details:
        return ""

    lines = []
    for key, value in details.items():
        lines.append(f'"{key}"="{value}"')
    return "\n".join(lines)

@login_required
@require_http_methods(["GET", "POST"])
def vehicle_edit(request, operator_slug, vehicle_id):
    response = feature_enabled(request, "edit_vehicles")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    vehicle = get_object_or_404(fleet, id=vehicle_id, operator=operator)

    vehicle = get_object_or_404(fleet, id=vehicle_id)

    if operator != vehicle.operator:
        messages.error(request, "This vehicle does not belong to the specified operator.")
        return redirect(f'/operator/{operator_slug}/')

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Buses' not in userPerms and not request.user.is_superuser:
        return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/')

    # Load related data needed for selects and checkboxes
    operators = MBTOperator.objects.all()
    types = vehicleType.objects.all()
    liveries_list = liverie.objects.all()
    allowed_operators = []

    if request.user.is_authenticated:
        helper_operator_ids = helper.objects.filter(
            helper=request.user,
            perms__perm_name="Edit Buses"
        ).values_list("operator_id", flat=True)

        # 3. Combined queryset (owners + allowed helpers)
        allowed_operators = MBTOperator.objects.filter(
            Q(id__in=helper_operator_ids) | Q(owner=request.user)
        ).distinct().order_by('operator_name')

    path = "JSON/features.json"
    data = safe_json_load(path, default={})
    features_list = data.get("features", [])

    if request.method == "POST":
        current_operator = vehicle.operator
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

        custom = request.POST.get('custom', '').strip()

        json_custom = {}
        for line in custom.splitlines():
            # Match "Key"="Value"
            match = re.match(r'^\s*"?(.+?)"?\s*[:=]\s*"?(.+?)"?\s*$', line)
            if match:
                key, value = match.groups()
                json_custom[key.strip()] = value.strip()

        vehicle.advanced_details = json_custom

        if MBTOperator.objects.get(id=request.POST.get('operator')) != current_operator:
            vehicle.for_sale = False

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

        # Vehicle category (ensure it belongs to the current operator)
        try:
            from routes.models import board_category as BoardCategory
            vc_id = request.POST.get('vehicle_category')
            if vc_id:
                try:
                    cat = BoardCategory.objects.get(id=vc_id)
                    # Ensure category operator matches vehicle.operator
                    if cat.operator and vehicle.operator and cat.operator.id == vehicle.operator.id:
                        vehicle.vehicle_category = cat
                    else:
                        vehicle.vehicle_category = None
                except BoardCategory.DoesNotExist:
                    vehicle.vehicle_category = None
            else:
                vehicle.vehicle_category = None
        except Exception:
            # If anything goes wrong, don't block saving
            pass

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
        return redirect('vehicle_detail', operator_slug=vehicle.operator.operator_slug, vehicle_id=vehicle_id)

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
            {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
            {'name': 'Vehicles', 'url': f'/operator/{operator_slug}/vehicles/'},
            {'name': f'{vehicle.fleet_number} - {vehicle.reg}', 'url': f'/operator/{operator_slug}/vehicles/{vehicle_id}/edit/'}
        ]

        tabs = []  # populate as needed or reuse your generate_tabs method

        if request.user.is_authenticated and request.user.banned_from.filter(name='selling_buses').exists():
            hide_sell_button = True
        else:
            hide_sell_button = False

        # Categories for this operator
        try:
            from routes.models import board_category as BoardCategory
            category_list = BoardCategory.objects.filter(operator=vehicle.operator)
        except Exception:
            category_list = []

        context = {
            'hide_sell_button': hide_sell_button,
            'fleetData': vehicle,
            'operatorData': operators,
            'typeData': types,
            'liveryData': liveries_list,
            'categoryData': category_list,
            'features': features_list,
            'userData': user_data,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
            "custom": advanced_details_to_text(vehicle.advanced_details),
            'allowed_operators': allowed_operators,
        }
        return render(request, 'edit.html', context)

def vehicles_trip_manage(request, operator_slug, vehicle_id):
    response = feature_enabled(request, "manage_trips")
    if response:
        return response
    
    
    try:
        operator = MBTOperator.objects.get(operator_slug=operator_slug)
        vehicle = fleet.objects.get(id=vehicle_id, operator=operator)
        all_trip_dates = Trip.objects.filter(trip_vehicle=vehicle).values_list('trip_start_at', flat=True).distinct()

        all_trip_dates = sorted(
            {
                timezone.localtime(trip_date).date()
                for trip_date in all_trip_dates
                if trip_date is not None
            },
            reverse=True
        )
        
    except (MBTOperator.DoesNotExist, fleet.DoesNotExist):
        return render(request, '404.html', status=404)
    
    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Trips' not in userPerms and not request.user.is_superuser:
        return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/')


    # If a date is selected via GET, use it, else default to today
    selected_date_str = request.GET.get("date")
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = all_trip_dates[0] if all_trip_dates else date.today()

    
    start_of_day = datetime.combine(selected_date, time.min)
    end_of_day = datetime.combine(selected_date, time.max)


    trips = Trip.objects.filter(
        trip_vehicle=vehicle,
        trip_start_at__range=(start_of_day, end_of_day)
    ).order_by('trip_start_at')

    trips_json = serialize('json', trips)
    # Handle the trip management logic here

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator.operator_slug}/'},
        {'name': 'Vehicles', 'url': f'/operator/{operator.operator_slug}/vehicles#{vehicle.fleet_number}-{vehicle.operator.operator_code}'},
        {'name': f'{vehicle.fleet_number} - {vehicle.reg}', 'url': f'/operator/{operator.operator_slug}/vehicles/{vehicle_id}/'}
    ]

    tabs = generate_tabs("vehicles", operator)

    serialized_vehicle = fleetSerializer(vehicle)  # single object, no many=True
    serialized_vehicle_data = serialized_vehicle.data

    # Default last_trip values
    serialized_vehicle_data['last_trip_display'] = ''
    last_trip = None  # ✅ Initialize to avoid UnboundLocalError

    # Get latest trip ID (use correct key — flattening dot notation)
    latest_trip_id = serialized_vehicle_data.get('latest_trip__trip_id')

    if latest_trip_id:
        last_trip = Tracking.objects.filter(tracking_id=latest_trip_id).first()
        if last_trip and last_trip.start_time and last_trip.end_time:
            serialized_vehicle_data['last_trip_display'] = f"{last_trip.start_time.strftime('%H:%M')} → {last_trip.end_time.strftime('%H:%M')}"

    context = {
        'last_trip': last_trip,
        'all_trip_dates': all_trip_dates,
        'selected_date': selected_date,
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'vehicle': serialized_vehicle.data,
        'helper_permissions': userPerms,
        'tabs': tabs,
        'trips': trips,
        'trips_json': trips_json,
    }
    return render(request, 'vehicles_trip_manage.html', context)

def vehicles_trip_miss(request, operator_slug, vehicle_id, trip_id):
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    vehicle = get_object_or_404(fleet, id=vehicle_id, operator=operator)
    trip = get_object_or_404(Trip, trip_id=trip_id, trip_vehicle=vehicle)

    if trip.trip_missed:
        trip_miss = False
    else:
        trip_miss = True

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Miss Trips' not in userPerms and not request.user.is_superuser:
        return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/')

    trip.trip_missed = trip_miss
    trip.save()
    if trip_miss:
        missed = "Missed"
    else:
        missed = "Unmissed"
    messages.success(request, f"Trip marked as {missed}.")
    return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/trips/manage/')

def remove_all_trips(request, operator_slug, vehicle_id):
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    vehicle = get_object_or_404(fleet, id=vehicle_id, operator=operator)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Delete Trips' not in userPerms and not request.user.is_superuser:
        return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/')

    deleted_trips = Trip.objects.filter(
        trip_vehicle=vehicle,
    ).count()

    Trip.objects.filter(
        trip_vehicle=vehicle,
    ).delete()

    messages.success(request, f"{deleted_trips} trip(s) deleted successfully.")
    return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/trips/manage/')

def remove_other_trips(request, operator_slug, vehicle_id):
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    vehicle = get_object_or_404(fleet, id=vehicle_id, operator=operator)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Delete Trips' not in userPerms and not request.user.is_superuser:
        return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/')

    deleted_trips = Trip.objects.filter(
        trip_vehicle=vehicle,
    ).exclude(
        Q(trip_route__route_operators=operator)
        | Q(trip_route__isnull=True)
    ).count()

    Trip.objects.filter(
        trip_vehicle=vehicle,
    ).exclude(
        Q(trip_route__route_operators=operator)
        | Q(trip_route__isnull=True)
    ).delete()

    messages.success(request, f"{deleted_trips} trip(s) deleted successfully.")
    return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/trips/manage/')

def vehicles_trip_edit(request, operator_slug, vehicle_id, trip_id):
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    vehicle = get_object_or_404(fleet, id=vehicle_id, operator=operator)
    trip = get_object_or_404(Trip, trip_id=trip_id, trip_vehicle=vehicle)

    userPerms = get_helper_permissions(request.user, operator)

    operator = trip.trip_vehicle.operator

    if trip.trip_vehicle.loan_operator != trip.trip_vehicle.operator and trip.trip_vehicle.loan_operator is not None:
        operator = trip.trip_vehicle.loan_operator

    allRoutes = route.objects.filter(route_operators=operator).order_by('route_num')
    allVehicles = fleet.objects.filter(Q(operator=operator) | Q(loan_operator=operator)).order_by('fleet_number_sort')

    if request.user != operator.owner and 'Edit Trips' not in userPerms and not request.user.is_superuser:
        return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/')

    if request.method == "POST":
        if request.POST.get("trip_start_at"):
            trip.trip_start_at = datetime.fromisoformat(request.POST.get("trip_start_at"))
        else:
            trip.trip_start_at = None

        if request.POST.get("trip_end_at"):
            trip.trip_end_at = datetime.fromisoformat(request.POST.get("trip_end_at"))
        else:
            trip.trip_end_at = None


        trip.trip_start_location = request.POST.get('trip_start_location') or None
        trip.trip_end_location = request.POST.get('trip_end_location') or None
        trip.trip_display_id = request.POST.get('trip_display_id') or None

        vehicle_id = request.POST.get('trip_vehicle')
        trip.trip_vehicle = fleet.objects.get(id=vehicle_id) if vehicle_id else None
        route_id = request.POST.get('trip_route')
        trip.trip_route = route.objects.get(id=route_id) if route_id else None
        trip.trip_route_num = request.POST.get('trip_route_num') or None
        trip.trip_inbound = 'inbound' in request.POST
        
        trip.save()

        date = trip.trip_start_at.date().strftime("%Y-%m-%d")

        return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/trips/manage/?date={date}')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Vehicles', 'url': f'/operator/{operator_slug}/vehicles#{vehicle.fleet_number}-{vehicle.operator.operator_code}'},
        {'name': f'{vehicle.fleet_number} - {vehicle.reg}', 'url': f'/operator/{operator_slug}/vehicles/{vehicle_id}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'vehicle': vehicle,
        'trip': trip,
        'allRoutes': allRoutes,
        'allVehicles': allVehicles,
        'userPerms': userPerms
    }

    return render(request, 'vehicles_trip_edit.html', context)


def vehicles_trip_delete(request, operator_slug, vehicle_id, trip_id):
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    vehicle = get_object_or_404(fleet, id=vehicle_id, operator=operator)
    trip = get_object_or_404(Trip, trip_id=trip_id, trip_vehicle=vehicle)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Delete Trips' not in userPerms and not request.user.is_superuser:
        return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/')

    # Format date in Python instead of template syntax
    date = trip.trip_start_at.strftime("%Y-%m-%d") if trip.trip_start_at else ""

    trip.delete()
    messages.success(request, "Trip deleted successfully.")
    return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/trips/manage/?date={date}')

def flip_all_trip_directions(request, operator_slug, vehicle_id, selected_date):
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    vehicle = get_object_or_404(fleet, id=vehicle_id, operator=operator)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Trips' not in userPerms and not request.user.is_superuser:
        return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/')

    start_of_day = datetime.combine(datetime.fromisoformat(selected_date).date(), time.min)
    end_of_day = datetime.combine(datetime.fromisoformat(selected_date).date(), time.max)

    trips = Trip.objects.filter(
        trip_vehicle=vehicle,
        trip_start_at__range=(start_of_day, end_of_day)
    )

    for trip in trips:
        trip.trip_inbound = not trip.trip_inbound
        trip.save()

    messages.success(request, "All trip directions flipped successfully.")
    return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/trips/manage/?date={selected_date}')


def remove_todays_trips(request, operator_slug, vehicle_id, selected_date):
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    vehicle = get_object_or_404(fleet, id=vehicle_id, operator=operator)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Delete Trips' not in userPerms and not request.user.is_superuser:
        return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/')

    start_of_day = datetime.combine(datetime.fromisoformat(selected_date).date(), time.min)
    end_of_day = datetime.combine(datetime.fromisoformat(selected_date).date(), time.max)

    deleted_trips = Trip.objects.filter(
        trip_vehicle=vehicle,
        trip_start_at__range=(start_of_day, end_of_day)
    ).count()

    Trip.objects.filter(
        trip_vehicle=vehicle,
        trip_start_at__range=(start_of_day, end_of_day)
    ).delete()

    messages.success(request, f"{deleted_trips} trip(s) deleted successfully.")
    return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/trips/manage/?date={selected_date}')

#def send_discord_webhook_embed(
#    title: str,
#    description: str,
#    color: int = 0x00ff00,
#    fields: list = None,
#    image_url: str = None,
#    content: str = None
#):
#    webhook_url = settings.DISCORD_FOR_SALE_WEBHOOK
#
#    embed = {
#        "title": title,
#        "description": description,
#        "color": color,
#        "fields": fields or []
#    }
#
#    if image_url:
#        embed["image"] = {"url": image_url}
#    
#    data = {"embeds": [embed]}
#    if content:
#        data["content"] = content  # <-- include ping here
#    while True:  # retry loop
#        response = requests.post(webhook_url, json=data)
#
#        if response.status_code == 429:  # rate limited
#            retry_after = response.json().get("retry_after", 1)
#            import time
#            time.sleep(retry_after)
#            continue  # try again after waiting
#
#        response.raise_for_status()  # raises for 400/500 errors
#        break  # success → exit loop

def send_to_discord_for_sale_embed(channel_id, title, message, colour=0x00BFFF, image_url=None, fields=None, content=None):
    """Send a message+embed to the Discord bot API.

    Returns (True, None) on success or (False, error_string) on failure.
    """
    embed = {
        "title": title,
        "description": message,
        "color": colour,
        "fields": fields or [
            {
                "name": "Time",
                "value": datetime.now().strftime('%Y-%m-%d %H:%M'),
                "inline": True
            }
        ],
        "footer": {
            "text": "MBT For Sale Notifications"
        },
        "timestamp": datetime.now().isoformat()
    }

    if image_url:
        embed["image"] = {"url": image_url}

    data = {
        'channel_id': int(channel_id),
        'embed': embed
    }

    if settings.DISABLE_JESS:
        return True, None

    # send optional plain content first (role ping)
    try:
        if content:
            message_data = {
                'channel_id': channel_id,
                'message': content
            }
            response_message = requests.post(
                f"{settings.DISCORD_BOT_API_URL}/send-message-clean",
                data=message_data,
                files=None,
                timeout=5,
            )
            # raise for bad status codes
            response_message.raise_for_status()
    except requests.exceptions.RequestException as e:
        return False, f"Failed to send Discord message: {e}"

    # now send the embed
    try:
        response = requests.post(
            f"{settings.DISCORD_BOT_API_URL}/send-embed",
            json=data,
            timeout=5,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return False, f"Failed to send Discord embed: {e}"

    return True, None


@login_required
@require_http_methods(["GET", "POST"])
def vehicle_sell(request, operator_slug, vehicle_id):
    if request.user.is_authenticated and request.user.banned_from.filter(name='selling_buses').exists():
        return redirect('selling_buses_banned')
    
    response = feature_enabled(request, "sell_vehicles")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    vehicle = get_object_or_404(fleet, id=vehicle_id, operator=operator)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Sell Buses' not in userPerms and not request.user.is_superuser:
        return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/')

    if vehicle.for_sale:
        vehicle.for_sale = False
        operator.vehicles_for_sale = max(operator.vehicles_for_sale - 1, 0)  # prevent negative
        message = "removed"
    else:
        if request.user.is_authenticated and request.user.banned_from.filter(name='selling_buses').exists():
            return redirect('selling_buses_banned')
        
        if operator.vehicles_for_sale >= max_for_sale:
            messages.error(request, f"You can only list {max_for_sale} vehicles for sale.")
            vehicle.for_sale = False
            vehicle.save()
            return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/')
        else:
            vehicle.for_sale = True
            operator = MBTOperator.objects.get(id=operator.id)
            for_sale_count = fleet.objects.filter(operator=operator, for_sale=True).count()
            operator.vehicles_for_sale = for_sale_count
            operator.save()
            
            message = "listed"

            encoded_operator_slug = quote(operator_slug)

            title = "Vehicle Listed for Sale"
            description = f"**{operator.operator_name}** has listed {vehicle.fleet_number} - {vehicle.reg} for sale."
            fields = [
                {"name": "Fleet Number", "value": vehicle.fleet_number if hasattr(vehicle, 'fleet_number') else 'N/A', "inline": True},
                {"name": "Registration", "value": vehicle.reg if hasattr(vehicle, 'reg') else 'N/A', "inline": True},
                {"name": "Type", "value": getattr(vehicle.vehicleType, 'type_name', 'N/A'), "inline": False},
                {"name": "View", "value": f"https://www.mybustimes.cc/operator/{encoded_operator_slug}/vehicles/{vehicle.id}/?v={random.randint(1000,9999)}", "inline": False}
            ]

            success, err = send_to_discord_for_sale_embed(
                channel_id=settings.DISCORD_FOR_SALE_CHANNEL_ID,
                title=title,
                message=description,
                colour=0xFFA500,
                fields=fields,
                image_url=f"https://www.mybustimes.cc/operator/vehicle_image/{vehicle.id}/?v={random.randint(1000,9999)}",
                content="<@&1348490878024679424>"  # <-- role ping included here
            )
            if not success:
                messages.error(request, f"Vehicle listed but failed to notify Discord: {err}")
    vehicle.save()
    operator.save()

    messages.success(request, f"Vehicle {message} for sale successfully.")
    # Redirect back to the vehicle detail page or wherever you want
    return redirect('vehicle_detail', operator_slug=operator_slug, vehicle_id=vehicle_id)

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
    # Validate vehicle id before querying the DB
    try:
        vehicle_pk = int(vehicle_id)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': "Invalid vehicle id."}, status=400)

    vehicle = get_object_or_404(fleet, id=vehicle_pk)

    # Safely get the vehicle type name
    vehicle_type_name = getattr(vehicle.vehicleType, 'type_name', 'N/A')

    img = generate_vehicle_card(
        vehicle.fleet_number,
        vehicle.reg,
        vehicle_type_name,
        "For Sale" if vehicle.for_sale else "Sold"
    )

    buffer = BytesIO()
    img.save(buffer, format='PNG') 
    buffer.seek(0)

    return HttpResponse(buffer, content_type='image/png')


def vehicle_status_preview(request, vehicle_id):
    # Validate vehicle id before querying the DB
    try:
        vehicle_pk = int(vehicle_id)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': "Invalid vehicle id."}, status=400)

    vehicle = get_object_or_404(fleet, id=vehicle_pk)

    if not vehicle.for_sale:
        link = "Sold" if vehicle.for_sale else "Not for Sale"
    else:
        link = f"https://www.mybustimes.cc/for_sale#vehicle_{vehicle.id}"

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
        "image_url": f"https://www.mybustimes.cc/operator/vehicle_image/{vehicle.id}?v={random.randint(1000,9999)}",
        "breadcrumbs": [
            {'name': 'Home', 'url': '/'},
            {'name': 'For Sale', 'url': '/for_sale/'},
        ]
    }

    return render(request, "discord_preview.html", embed)

def duties(request, operator_slug):
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
        operator = MBTOperator.objects.get(operator_slug=operator_slug)
        duties_queryset = duty.objects.filter(duty_operator=operator, board_type=board_type).prefetch_related('duty_day', 'category').order_by('duty_name')
    except MBTOperator.DoesNotExist:
        return render(request, '404.html', status=404)

    userPerms = get_helper_permissions(request.user, operator)

    # Check grouping preference from query param (default to 'category')
    group_by = request.GET.get('group_by', 'category')

    # Get categories for this operator
    qs = board_category.objects.filter(
        operator=operator,
        board_type=board_type
    ).prefetch_related('subcategories')

    # Numeric-aware sort key (same as routes)
    def parse_name_key(name):
        rn = (name or '').upper()

        normal = re.match(r'^([0-9]+)$', rn)
        xprefix = re.match(r'^X([0-9]+)$', rn)
        suffix = re.match(r'^([0-9]+)([A-Z]+)$', rn)
        other = re.match(r'^([A-Z]+)([0-9]+)$', rn)

        if normal:
            return (0, int(normal.group(1)), "")
        if suffix:
            return (1, int(suffix.group(1)), suffix.group(2))
        if xprefix:
            return (2, int(xprefix.group(1)), "X")
        if other:
            return (3, other.group(1), int(other.group(2)))
        return (4, rn, 0)

    try:
        categories = list(qs)
        categories.sort(key=lambda c: parse_name_key(c.name))
    except Exception:
        categories = qs.order_by('name')

    if group_by == 'category':
        # Group duties by category
        grouped_duties = defaultdict(list)
        uncategorized = []
        
        for d in duties_queryset:
            if d.category:
                # Use full category path as key
                if d.category.parent_category:
                    key = f"{d.category.parent_category.name} > {d.category.name}"
                else:
                    key = d.category.name
                grouped_duties[key].append(d)
            else:
                uncategorized.append(d)
        
        # Sort categories using numeric-aware ordering like routes
        grouped_duties_ordered = dict(sorted(
            grouped_duties.items(),
            key=lambda kv: parse_name_key(kv[0].split(' > ')[-1])
        ))
        if uncategorized:
            grouped_duties_ordered['Uncategorised'] = uncategorized
    else:
        # Group duties by day name (default)
        grouped_duties = defaultdict(list)
        for d in duties_queryset:
            for day in d.duty_day.all():
                grouped_duties[day.name].append(d)

        # Sort by weekday order
        weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        grouped_duties_ordered = {day: grouped_duties[day] for day in weekday_order if day in grouped_duties}

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': titles, 'url': f'/operator/{operator_slug}/{board_type}/'}
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
        'group_by': group_by,
        'categories': categories,
        'board_type': board_type,
    }
    return render(request, 'duties.html', context)

def duty_detail(request, operator_slug, duty_id):
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

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
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
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': titles, 'url': f'/operator/{operator_slug}/{board_type}/'},
        {'name': duty_instance.duty_name or 'Duty Details', 'url': f'/operator/{operator_slug}/duty/{duty_id}/'}
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

def generate_pdf(request, operator_slug, duty_id):
    try:
        duty_instance = get_object_or_404(duty.objects.select_related('duty_operator'), id=duty_id)
        trips = dutyTrip.objects.filter(duty=duty_instance).order_by('start_time')
        operator = duty_instance.duty_operator

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
        p.drawCentredString(width / 2, header_top_y + 10, operator.operator_name)

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
        p.drawString(vertical_split_x + 10, 765, "Break Times:")
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
def duty_add(request, operator_slug):
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

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, f"You do not have permission to add a {titles} for this operator.")
        return redirect(f'/operator/{operator_slug}/{board_type}/')

    days = dayType.objects.all()
    
    # Get categories for this operator and board type
    categories = board_category.objects.filter(
        operator=operator,
        board_type=board_type
    ).select_related('parent_category')

    if request.method == "POST":
        action = request.POST.get('action', 'manual')
        
        if is_running_board:
            board_type = 'running-boards'
            board_types = 'running-boards'
        else:
            board_type = 'duty'
            board_types = 'duties'

        if action == 'generate':
            # Handle generate from timetable
            route_id = request.POST.get('route_id')
            pattern = request.POST.get('pattern', 'XX/01')
            direction = request.POST.get('direction', 'both')
            gen_days = request.POST.get('gen_days', '')
            gen_category_id = request.POST.get('gen_category', '')
            
            if not route_id:
                messages.error(request, "Please select a route.")
                return redirect(f'/operator/{operator_slug}/{board_type}/add/')
            
            selected_route = get_object_or_404(route, id=route_id)
            
            # Get category if selected
            selected_category = None
            if gen_category_id:
                try:
                    selected_category = board_category.objects.get(id=gen_category_id, operator=operator)
                except board_category.DoesNotExist:
                    pass
            
            # Get timetable entries for this route
            timetables = timetableEntry.objects.filter(route=selected_route)
            
            # Collect all trips with location info for vehicle blocking
            all_trips = []
            for tt in timetables:
                stop_times = tt.stop_times
                if not stop_times:
                    continue
                
                # Parse if it's a string
                if isinstance(stop_times, str):
                    try:
                        stop_times = json.loads(stop_times)
                    except (json.JSONDecodeError, TypeError):
                        continue
                
                if not isinstance(stop_times, dict):
                    continue
                    
                # Get sorted stops by order
                sorted_stops = sorted(stop_times.items(), key=lambda x: x[1].get('order', 0) if isinstance(x[1], dict) else 0)
                if len(sorted_stops) < 2:
                    continue
                    
                first_stop_data = sorted_stops[0][1]
                last_stop_data = sorted_stops[-1][1]
                
                if not isinstance(first_stop_data, dict) or not isinstance(last_stop_data, dict):
                    continue

                first_stop_name = first_stop_data.get('stopname', 'Start')
                last_stop_name = last_stop_data.get('stopname', 'End')
                first_times = first_stop_data.get('times', [])
                last_times = last_stop_data.get('times', [])
                is_inbound = tt.inbound
                
                # Skip if direction filter doesn't match
                if direction == 'inbound' and not is_inbound:
                    continue
                if direction == 'outbound' and is_inbound:
                    continue
                
                for i, start_time in enumerate(first_times):
                    if not start_time:
                        continue
                    end_time = last_times[i] if i < len(last_times) else None
                    if not end_time:
                        continue
                    
                    # Convert times to minutes for comparison
                    try:
                        start_parts = start_time.split(':')
                        end_parts = end_time.split(':')
                        start_mins = int(start_parts[0]) * 60 + int(start_parts[1])
                        end_mins = int(end_parts[0]) * 60 + int(end_parts[1])
                    except:
                        continue
                    
                    # Use logical location: outbound ends at 'far', inbound ends at 'home'
                    if is_inbound:
                        start_loc = 'far'
                        end_loc = 'home'
                    else:
                        start_loc = 'home'
                        end_loc = 'far'
                    
                    all_trips.append({
                        'start_time': start_time,
                        'end_time': end_time,
                        'start_location': start_loc,
                        'end_location': end_loc,
                        'start_stop': first_stop_name,
                        'end_stop': last_stop_name,
                        'direction': 'inbound' if is_inbound else 'outbound',
                        'start_minutes': start_mins,
                        'end_minutes': end_mins
                    })
            
            # Sort all trips by start time
            all_trips.sort(key=lambda x: x['start_minutes'])
            
            if not all_trips:
                messages.error(request, "No trips found in the timetable for this route/direction.")
                return redirect(f'/operator/{operator_slug}/{board_type}/add/')
            
            # Vehicle blocking algorithm - assign trips to vehicles
            vehicles = []  # List of vehicle blocks
            
            for trip in all_trips:
                # Find a vehicle that can do this trip
                best_vehicle = None
                best_wait_time = float('inf')
                
                for v in vehicles:
                    # Check if vehicle is available and at the right location
                    if v['end_minutes'] <= trip['start_minutes']:
                        if v['end_location'] == trip['start_location']:
                            wait_time = trip['start_minutes'] - v['end_minutes']
                            if wait_time < best_wait_time:
                                best_vehicle = v
                                best_wait_time = wait_time
                
                if best_vehicle:
                    # Assign trip to existing vehicle
                    best_vehicle['trips'].append(trip)
                    best_vehicle['end_minutes'] = trip['end_minutes']
                    best_vehicle['end_location'] = trip['end_location']
                else:
                    # Need a new vehicle
                    vehicles.append({
                        'trips': [trip],
                        'end_minutes': trip['end_minutes'],
                        'end_location': trip['end_location']
                    })
            
            # Parse selected days
            selected_days = [int(d) for d in gen_days.split(',') if d]
            
            if not selected_days:
                messages.error(request, "Please select at least one day.")
                return redirect(f'/operator/{operator_slug}/{board_type}/add/')
            
            # Create duties - one per vehicle block
            created_count = 0
            for i, vehicle in enumerate(vehicles):
                if not vehicle['trips']:
                    continue
                    
                board_num = str(i + 1).zfill(2)
                duty_name = pattern.replace('XX', board_num)
                
                first_trip = vehicle['trips'][0]
                last_trip = vehicle['trips'][-1]
                
                duty_details = {
                    "logon_time": first_trip['start_time'],
                    "logoff_time": last_trip['end_time'],
                    "brake_times": "",
                    "trip_count": len(vehicle['trips'])
                }
                
                duty_instance = duty.objects.create(
                    duty_name=duty_name,
                    duty_operator=operator,
                    duty_details=duty_details,
                    board_type=board_type,
                    category=selected_category
                )
                
                duty_instance.duty_day.set(selected_days)
                
                # Create dutyTrip records for each trip in this vehicle block
                for trip in vehicle['trips']:
                    dutyTrip.objects.create(
                        duty=duty_instance,
                        route=selected_route.route_num,
                        route_link=selected_route,
                        start_time=trip['start_time'],
                        end_time=trip['end_time'],
                        start_at=trip.get('start_stop', ''),
                        end_at=trip.get('end_stop', ''),
                        inbound=(trip['direction'] == 'inbound')
                    )
                
                created_count += 1
            
            trips_created = len(all_trips)
            messages.success(request, f"Successfully created {created_count} {titles.lower()} with {trips_created} trips from timetable.")
            return redirect(f'/operator/{operator_slug}/{board_type}/')
        
        else:
            # Handle manual add
            duty_name = request.POST.get('duty_name')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            brake_times = request.POST.getlist('brake_times')
            selected_days = request.POST.getlist('duty_day')  # Handle multiple dayType IDs
            category_id = request.POST.get('category')

            formatted_brakes = " | ".join(brake_times)

            duty_details = {
                "logon_time": start_time,
                "logoff_time": end_time,
                "brake_times": formatted_brakes
            }

            # Get category if selected
            selected_category = None
            if category_id:
                selected_category = board_category.objects.filter(id=category_id, operator=operator).first()

            duty_instance = duty.objects.create(
                duty_name=duty_name,
                duty_operator=operator,
                duty_details=duty_details,
                board_type=board_type,
                category=selected_category
            )

            # Set ManyToManyField values
            if selected_days:
                duty_instance.duty_day.set(selected_days)

            messages.success(request, f"{title} added successfully.")
            return redirect(f'/operator/{operator_slug}/{board_types}/add/trips/{duty_instance.id}/')

    else:
        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
            {'name': titles, 'url': f'/operator/{operator_slug}/{board_type}/'},
            {'name': f'Add {title}', 'url': f'/operator/{operator_slug}/{board_type}/add/'}
        ]

        tabs = generate_tabs("duties", operator)

        # Get routes for this operator for the generator
        operator_routes = route.objects.filter(route_operators=operator).values(
            'id', 'route_num', 'inbound_destination', 'outbound_destination', 'route_details'
        )
        
        routes_json = json.dumps([
            {
                'id': r['id'],
                'route_num': r['route_num'] or '',
                'inbound_destination': r['inbound_destination'] or '',
                'outbound_destination': r['outbound_destination'] or '',
                'colours': r['route_details'].get('colours', '') if r['route_details'] else ''
            }
            for r in operator_routes
        ])

        context = {
            'operator': operator,
            'days': days,
            'categories': categories,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
            'is_running_board': is_running_board,  # Pass this to your template if needed
            'titles': titles,  # Pass the plural title for the duties/running boards
            'title': title,  # Pass the singular title for the duty/running board
            'board_type': board_type,
            'routes_json': routes_json,
        }
        return render(request, 'add_duty.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def duty_add_trip(request, operator_slug, duty_id):
    """
    Handle adding trips to a duty or running board for an operator.
    
    On GET, renders a form to add multiple trips to the specified duty/running board, providing available routes and context.
    On POST, validates permission and posted trip arrays, parses times, creates dutyTrip records (associating an existing route object when found), counts successful creations, and redirects back to the duties/running-boards list with success or error messages.
    
    Parameters:
        request (HttpRequest): The incoming request object.
        operator_slug (str): Slug identifying the operator.
        duty_id (int): Primary key of the duty or running board to which trips will be added.
    
    Returns:
        HttpResponse: A redirect after POST (success or error) or a rendered template ('add_duty_trip.html') on GET.
    """
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
        board_type = "duties"

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)

    duty_instance = get_object_or_404(duty, id=duty_id, duty_operator=operator)
    available_routes_qs = route.objects.filter(route_operators=operator).order_by('route_num')
    available_routes = [
        {
            "id": r.id,
            "route_num": r.route_num,
            "route_name": r.route_name,
            "route_inbound_destination": r.inbound_destination,
            "route_outbound_destination": r.outbound_destination,
        } for r in available_routes_qs
    ]

    if request.user != operator.owner and 'Add Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, f"You do not have permission to add a {title} for this operator.")
        return redirect(f'/operator/{operator_slug}/{board_type}/')

    if request.method == "POST":
        # Get lists of trip inputs (all arrays)
        route_nums = request.POST.getlist('route_num[]')
        start_times = request.POST.getlist('start_time[]')
        end_times = request.POST.getlist('end_time[]')
        start_ats = request.POST.getlist('start_at[]')
        end_ats = request.POST.getlist('end_at[]')
        inbound_trips = request.POST.getlist('inbound_trip[]')  # Now this will always have values

        # Validate lengths are equal
        if not (len(route_nums) == len(start_times) == len(end_times) == len(start_ats) == len(end_ats) == len(inbound_trips)):
            messages.error(request, "Mismatch in trip input lengths.")
            return redirect(request.path)

        trips_created = 0

        for i in range(len(route_nums)):
            try:
                start_time = datetime.strptime(start_times[i], '%H:%M').time()
                end_time = datetime.strptime(end_times[i], '%H:%M').time()
            except ValueError:
                messages.error(request, f"Invalid time format for trip {i+1}.")
                continue

            route_num = route_nums[i]

            # Lookup the actual route object
            try:
                route_obj = route.objects.filter(route_operators=operator, route_num=route_num).first()
            except route.DoesNotExist:
                route_obj = None

            # Create dutyTrip instance
            dutyTrip.objects.create(
                duty=duty_instance,
                route=route_num,
                route_link=route_obj,
                start_time=start_time,  
                end_time=end_time,
                start_at=start_ats[i],
                end_at=end_ats[i],
                inbound=(inbound_trips[i] == 'true')
            )
            trips_created += 1

        messages.success(request, f"Successfully added {trips_created} trip(s) to duty '{duty_instance.duty_name}'.")
        return redirect(f'/operator/{operator_slug}/{board_type}/')

    else:
        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
            {'name': titles, 'url': f'/operator/{operator_slug}/{board_type}/'},
            {'name': duty_instance.duty_name, 'url': f'/operator/{operator_slug}/{board_type}/{duty_id}/'},
            {'name': 'Add Trips', 'url': request.path}
        ]

        tabs = generate_tabs("duties", operator)

        context = {
            'available_routes': available_routes,  # Pass available routes for trip selection
            'operator': operator,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
            'duty_instance': duty_instance,  # renamed for clarity with your template
            'title': title,  # Pass the singular title for the duty/running board
            'titles': titles,  # Pass the plural title for the duties/running boards
            'is_running_board': is_running_board,  # Pass this to your template if needed
        }
        return render(request, 'add_duty_trip.html', context)
    
def get_timetable_trips(request, route_id):
    """
    Return a list of vehicle blocks (duties) calculated from timetable entries.
    Each block represents one vehicle's work for the day, chaining inbound/outbound trips.
    
    Parameters:
        request: Django HttpRequest with optional GET parameter `direction` (inbound/outbound/both).
        route_id (int): Primary key of the route to query.
    
    Returns:
        JSON response with array of vehicle blocks, each containing trips and overall times.
    """
    direction = request.GET.get('direction', 'both')
    
    r = route.objects.filter(pk=route_id).first()
    if not r:
        return JsonResponse({"error": "Route not found", "trips": []}, status=400)
    
    # Get all timetable entries for this route
    all_trips = []
    
    # Use a set to track unique trips and prevent duplicates
    seen_trips = set()
    
    timetables = timetableEntry.objects.filter(route=r)
    
    for tt in timetables:
        stop_times = tt.stop_times
        if not stop_times:
            continue
        
        # Parse if it's a string
        if isinstance(stop_times, str):
            try:
                stop_times = json.loads(stop_times)
            except (json.JSONDecodeError, TypeError):
                continue
        
        if not isinstance(stop_times, dict):
            continue
        
        # Sort stops by order
        sorted_stops = sorted(stop_times.items(), key=lambda x: x[1].get('order', 0) if isinstance(x[1], dict) else 0)
        if len(sorted_stops) < 2:
            continue
        
        first_stop_data = sorted_stops[0][1]
        last_stop_data = sorted_stops[-1][1]
        
        if not isinstance(first_stop_data, dict) or not isinstance(last_stop_data, dict):
            continue
        
        first_stop_name = first_stop_data.get('stopname', 'Start')
        last_stop_name = last_stop_data.get('stopname', 'End')
        first_times = first_stop_data.get('times', [])
        last_times = last_stop_data.get('times', [])
        
        is_inbound = tt.inbound
        
        # Skip if direction filter doesn't match
        if direction == 'inbound' and not is_inbound:
            continue
        if direction == 'outbound' and is_inbound:
            continue
        
        for i, start_time in enumerate(first_times):
            # Skip empty strings and None values
            if not start_time or start_time.strip() == '':
                continue
            end_time = last_times[i] if i < len(last_times) else None
            if not end_time or end_time.strip() == '':
                continue
            
            # Create unique identifier for this trip
            trip_direction = 'inbound' if is_inbound else 'outbound'
            trip_key = f"{start_time}|{end_time}|{trip_direction}|{first_stop_name}|{last_stop_name}"
            
            # Skip if we've already seen this exact trip
            if trip_key in seen_trips:
                continue
            
            seen_trips.add(trip_key)
            
            # Use logical location: outbound ends at 'far', inbound ends at 'home'
            # This allows proper chaining regardless of actual stop names
            if is_inbound:
                start_loc = 'far'
                end_loc = 'home'
            else:
                start_loc = 'home'
                end_loc = 'far'
            
            all_trips.append({
                'start_time': start_time,
                'end_time': end_time,
                'start_location': start_loc,
                'end_location': end_loc,
                'origin': first_stop_name,
                'destination': last_stop_name,
                'direction': trip_direction,
                'start_minutes': time_to_minutes(start_time),
                'end_minutes': time_to_minutes(end_time)
            })
    
    # Sort all trips by start time
    all_trips.sort(key=lambda x: x['start_minutes'])
    
    # Debug: Print all trips
    #print(f"\n===== ALL TRIPS FOR ROUTE {r.route_num} (direction={direction}) =====")
    #print(f"Total trips found: {len(all_trips)}")
    #for idx, trip in enumerate(all_trips):
    #    print(f"Trip {idx}: {trip['start_time']} → {trip['end_time']} | {trip['direction']} | {trip['origin']} → {trip['destination']} | start_loc={trip['start_location']}, end_loc={trip['end_location']}")
    #print("=" * 80)
    #
    # Vehicle blocking algorithm - minimize number of vehicles by maximizing trips per vehicle
    # Strategy: Always try to assign to the FIRST vehicle that can do it, no matter the wait time
    vehicles = []  # List of vehicle blocks, each is {'trips': [], 'end_minutes': int, 'end_location': str}
    
    # For single-direction mode, we need to account for deadhead time back to start
    single_direction_mode = direction in ['inbound', 'outbound']
    
    for trip in all_trips:
        # Try to assign to existing vehicles first, starting from vehicle 0
        assigned = False
        
        for v in vehicles:
            can_do_trip = False
            
            if single_direction_mode:
                # In single direction mode, estimate deadhead time as the trip duration
                # Vehicle needs time to get back to start point after completing the trip
                last_trip = v['trips'][-1] if v['trips'] else None
                if last_trip:
                    trip_duration = last_trip['end_minutes'] - last_trip['start_minutes']
                    deadhead_time = trip_duration  # Assume similar time to deadhead back
                    # Vehicle becomes available at: end time + deadhead time
                    available_time = v['end_minutes'] + deadhead_time
                else:
                    available_time = v['end_minutes']
                
                # Check if vehicle can complete deadhead and be ready for next trip
                # No maximum wait time - accept any gap
                if available_time <= trip['start_minutes']:
                    can_do_trip = True
            else:
                # In both directions mode, check location matching
                # No maximum wait time - accept any gap
                if v['end_minutes'] <= trip['start_minutes']:
                    if v['end_location'] == trip['start_location']:
                        can_do_trip = True
            
            if can_do_trip:
                # Assign trip to this vehicle
                v['trips'].append(trip)
                v['end_minutes'] = trip['end_minutes']
                v['end_location'] = trip['end_location']
                assigned = True
                break  # Stop at first vehicle that can do it
        
        if not assigned:
            # Need a new vehicle - no existing vehicle can do this trip
            vehicles.append({
                'trips': [trip],
                'end_minutes': trip['end_minutes'],
                'end_location': trip['end_location']
            })
    
    # Format response - each vehicle becomes a duty/board
    result = []
    for i, v in enumerate(vehicles):
        if v['trips']:
            first_trip = v['trips'][0]
            last_trip = v['trips'][-1]
            
            # Double-check for any duplicate trips within this vehicle block
            unique_trips = []
            trip_keys_in_block = set()
            
            for t in v['trips']:
                t_key = f"{t['start_time']}|{t['end_time']}|{t['direction']}"
                if t_key not in trip_keys_in_block:
                    trip_keys_in_block.add(t_key)
                    unique_trips.append(t)
            
            result.append({
                'vehicle_num': i + 1,
                'start_time': first_trip['start_time'],
                'end_time': last_trip['end_time'],
                'trip_count': len(unique_trips),
                'trips': unique_trips
            })
    
    # Sort by first trip start time
    result.sort(key=lambda x: time_to_minutes(x['start_time']))
    
    return JsonResponse({"trips": result, "vehicle_count": len(result)})

def time_to_minutes(time_str):
    """Convert HH:MM to minutes since midnight."""
    try:
        parts = time_str.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except:
        return 0


@login_required
@require_http_methods(["POST"])
def create_duty_from_timetable_api(request, operator_slug):
    """
    API endpoint to create a single duty with its trips from timetable data.
    Called via AJAX to avoid timeouts when creating many duties.
    """
    try:
        operator = MBTOperator.objects.get(operator_slug=operator_slug)
    except MBTOperator.DoesNotExist:
        return JsonResponse({"success": False, "error": "Operator not found"}, status=404)
    
    # Check permissions
    user = request.user
    is_owner = operator.owner == user
    is_helper = helper.objects.filter(operator=operator, helper=user).exists()
    if not (is_owner or is_helper or user.is_superuser):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)
    
    # Parse request data
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    
    duty_name = data.get('duty_name')
    board_type = data.get('board_type', 'duty')
    route_id = data.get('route_id')
    category_id = data.get('category_id')
    days = data.get('days', [])
    trips = data.get('trips', [])
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    if not duty_name or not route_id or not days:
        return JsonResponse({"success": False, "error": "Missing required fields"}, status=400)
    
    # Get the route
    try:
        selected_route = route.objects.get(id=route_id)
    except route.DoesNotExist:
        return JsonResponse({"success": False, "error": "Route not found"}, status=404)
    
    # Get category if specified
    selected_category = None
    if category_id:
        try:
            selected_category = board_category.objects.get(id=category_id, operator=operator)
        except board_category.DoesNotExist:
            pass
    
    # Build duty details
    duty_details = {
        "logon_time": start_time,
        "logoff_time": end_time,
        "brake_times": "",
        "trip_count": len(trips)
    }
    
    # Create the duty
    duty_instance = duty.objects.create(
        duty_name=duty_name,
        duty_operator=operator,
        duty_details=duty_details,
        board_type=board_type,
        category=selected_category
    )
    
    # Set days
    duty_instance.duty_day.set(days)
    
    # Create trips
    trips_created = 0
    for trip in trips:
        dutyTrip.objects.create(
            duty=duty_instance,
            route=selected_route.route_num,
            route_link=selected_route,
            start_time=trip.get('start_time'),
            end_time=trip.get('end_time'),
            start_at=trip.get('origin', ''),
            end_at=trip.get('destination', ''),
            inbound=(trip.get('direction') == 'inbound')
        )
        trips_created += 1
    
    return JsonResponse({
        "success": True,
        "duty_id": duty_instance.id,
        "duty_name": duty_name,
        "trips_created": trips_created,
        "message": f"Created {duty_name} with {trips_created} trips"
    })

    
def get_timetable(request, route_id, direction):
    """
    Return a sequence of vehicle trips (timetable) for the given route starting at the specified time.
    
    Expects the request to include a GET parameter `start_time` in "HH:MM" format. The function looks up the route by `route_id`, parses inbound and outbound timetable entries (if present), and builds an alternating sequence of trips starting with inbound when `direction == "inbound"`. Each trip object in the returned JSON array contains:
    - `times`: list of `{ "stop": <stopname>, "time": <HH:MM> }`
    - `start_time`, `end_time`: string times for the trip endpoints
    - `start_minutes`, `end_minutes`: endpoint times converted to minutes past midnight
    - `start_stop`, `end_stop`: endpoint stop names
    - `direction`: `"inbound"` or `"outbound"`
    
    Parameters:
        request: Django HttpRequest containing GET parameter `start_time` (required).
        route_id (int): Primary key of the route to query.
        direction (str): If `"inbound"`, the generated sequence begins with inbound trips; otherwise it begins with outbound.
    
    Returns:
        JSON response containing an array of trip objects as described above on success. Returns a JSON error object with HTTP 400 when `start_time` is missing or invalid, the route is not found, or on other processing errors.
    """
    import json
    import sys

    def log(*args):
        print(*args)

    try:
        log("REQUEST route_id=", route_id, "direction=", direction)

        inbound_first = (direction == "inbound")

        start_time_str = request.GET.get("start_time", None)
        log("START TIME RAW =", start_time_str)

        if not start_time_str:
            return JsonResponse({"error": "start_time is required (HH:MM)"}, status=400)

        def to_minutes(t):
            """
            Convert an "HH:MM" time string to the total number of minutes since midnight.
            
            Parameters:
                t (str): Time in "HH:MM" format (hours and minutes).
            
            Returns:
                int: Total minutes since midnight (hours * 60 + minutes).
            """
            h, m = map(int, t.split(":"))
            return h * 60 + m

        start_minutes = to_minutes(start_time_str)
        log("START TIME MINUTES =", start_minutes)

        # -------- GET ROUTE --------
        r = route.objects.filter(pk=route_id).first()
        log("ROUTE FOUND =", bool(r))

        if not r:
            return JsonResponse({"error": "Route not found"}, status=400)

        inbound_entry = timetableEntry.objects.filter(route=r, inbound=True).first()
        outbound_entry = timetableEntry.objects.filter(route=r, inbound=False).first()

        one_way_inbound_only = False
        if outbound_entry is None:
            log("OUTBOUND MISSING → ONE-WAY MODE ENABLED (INBOUND ONLY)")
            one_way_inbound_only = True

        # -------- PARSE TIMETABLE ENTRY --------
        def parse_entry(entry, label):
            log(f"Parsing entry for {label}")

            data = entry.stop_times
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception as e:
                    log(f"JSON LOAD ERROR IN {label}:", str(e))
                    return []

            stops_list = list(data.values())
            if not stops_list:
                return []

            # Determine TRUE number of trips from max times length
            trip_count = max(len(stop.get("times", [])) for stop in stops_list)
            log(f"{label}: detected trip_count = {trip_count}")

            trips = []

            # Build each trip individually
            for trip_index in range(trip_count):
                trip_stops = []

                for stop in stops_list:
                    stopname = stop["stopname"]
                    times = stop.get("times", [])

                    # If this stop has a time for this trip index → use it
                    if trip_index < len(times):
                        t = times[trip_index]
                        if t and t.strip():
                            trip_stops.append({"stop": stopname, "time": t})
                        else:
                            # Blank or missing time in the middle
                            continue
                    else:
                        # Stop has no time for this trip (early terminated / skipped)
                        continue

                # Must have at least 2 stops to be a valid trip
                if len(trip_stops) < 2:
                    continue

                start_t = trip_stops[0]["time"]
                end_t = trip_stops[-1]["time"]

                trips.append({
                    "times": trip_stops,
                    "start_time": start_t,
                    "end_time": end_t,
                    "start_minutes": to_minutes(start_t),
                    "end_minutes": to_minutes(end_t),
                    "start_stop": trip_stops[0]["stop"],
                    "end_stop": trip_stops[-1]["stop"],
                    "direction": label.lower()
                })

            # Sort by actual time
            trips.sort(key=lambda x: x["start_minutes"])
            return trips

        inbound_trips = parse_entry(inbound_entry, "INBOUND")
        outbound_trips = parse_entry(outbound_entry, "OUTBOUND") if outbound_entry else []

        # -------- BUILD VEHICLE RUN SEQUENCE --------

        result = []
        current_time = start_minutes
        doing_inbound = inbound_first

        iteration = 0
        while True:
            iteration += 1
            if iteration > 5000:
                break

            pool = inbound_trips if doing_inbound else outbound_trips

            next_trip = None
            for t in pool:
                if t["start_minutes"] >= current_time:
                    next_trip = t
                    break

            if not next_trip:
                break

            if next_trip["end_minutes"] <= current_time:
                break

            result.append(next_trip)
            current_time = next_trip["end_minutes"]

            if not one_way_inbound_only:
                doing_inbound = not doing_inbound

        return JsonResponse(result, safe=False)

    except Exception as e:
        log("ERROR:", str(e))
        return JsonResponse({"error": str(e)}, status=400)

@login_required
@require_http_methods(["GET", "POST"])
def duty_edit_trips(request, operator_slug, duty_id):
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

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)
    duty_instance = get_object_or_404(duty, id=duty_id, duty_operator=operator)

    available_routes_qs = route.objects.filter(route_operators=operator).order_by('route_num')
    available_routes = [
        {
            "route_num": r.route_num,
            "route_name": r.route_name,
            "route_inbound_destination": r.inbound_destination,
            "route_outbound_destination": r.outbound_destination,
            
        } for r in available_routes_qs
    ]

    if request.user != operator.owner and 'Add Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, f"You do not have permission to edit trips for this {title}.")
        return redirect(f'/operator/{operator_slug}/{board_type}/')

    if request.method == "POST":
        # Get posted trip data
        route_nums = request.POST.getlist('route_num[]')
        start_times = request.POST.getlist('start_time[]')
        end_times = request.POST.getlist('end_time[]')
        start_ats = request.POST.getlist('start_at[]')
        end_ats = request.POST.getlist('end_at[]')
        inbound_trips = request.POST.getlist('inbound_trip[]')


        if not (len(route_nums) == len(start_times) == len(end_times) == len(start_ats) == len(end_ats) == len(inbound_trips)):
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

            route_num = route_nums[i]

            # Lookup the actual route object
            try:
                route_obj = route.objects.filter(route_operators=operator, route_num=route_num).first()
            except route.DoesNotExist:
                route_obj = None

            dutyTrip.objects.create(
                duty=duty_instance,
                route=route_num,
                route_link=route_obj,
                start_time=start_time,
                end_time=end_time,
                start_at=start_ats[i],
                end_at=end_ats[i],
                inbound=(inbound_trips[i] == 'true') 
            )
            trips_created += 1

        messages.success(request, f"Updated {trips_created} trip(s) for duty '{duty_instance.duty_name}'.")
        return redirect(f'/operator/{operator_slug}/{board_type}/')

    else:
        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
            {'name': titles, 'url': f'/operator/{operator_slug}/{board_type}/'},
            {'name': duty_instance.duty_name, 'url': f'/operator/{operator_slug}/{board_type}/{duty_id}/'},
            {'name': 'Edit Trips', 'url': request.path}
        ]

        tabs = generate_tabs("duties", operator)

        context = {
            'available_routes': available_routes,  # Pass available routes for trip selection
            'operator': operator,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
            'duty_instance': duty_instance,
        }
        return render(request, 'edit_duty_trip.html', context)
    
@login_required
@require_http_methods(["POST"])
def flip_all_duty_trip_directions(request, operator_slug, board_id):
    response = feature_enabled(request, "edit_boards")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)
    duty_instance = get_object_or_404(duty, id=board_id, duty_operator=operator)

    is_running_board = duty_instance.board_type == 'running-boards'

    if is_running_board:
        title = "Running Board"
        titles = "Running Boards"
        board_type = 'running-boards'
    else:
        title = "Duty"
        titles = "Duties"
        board_type = "duty"

    if request.user != operator.owner and 'Edit Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, f"You do not have permission to edit this {title} for this operator.")
        return redirect(f'/operator/{operator_slug}/{board_type}/')

    trips = dutyTrip.objects.filter(duty=duty_instance)
    for trip in trips:
        trip.inbound = not trip.inbound
        trip.save()

    messages.success(request, f"Flipped directions for all trips on {title} '{duty_instance.duty_name}'.")
    return redirect(f'/operator/{operator_slug}/{board_type}/edit/{duty_instance.id}/trips/')

@login_required
@require_http_methods(["GET", "POST"])
def duty_delete(request, operator_slug, duty_id):
    response = feature_enabled(request, "delete_boards")
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
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)
    duty_instance = get_object_or_404(duty, id=duty_id, duty_operator=operator)

    if request.user != operator.owner and 'Delete Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, f"You do not have permission to delete this {title}.")
        return redirect(f'/operator/{operator_slug}/{board_type}/')

    duty_instance.delete()
    messages.success(request, f"Deleted {title} '{duty_instance.duty_name}'.")
    return redirect(f'/operator/{operator_slug}/{board_type}/')

@login_required
@require_http_methods(["GET", "POST"])
def duty_edit(request, operator_slug, duty_id):
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
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)
    duty_instance = get_object_or_404(duty, id=duty_id, duty_operator=operator)

    if request.user != operator.owner and 'Edit Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, f"You do not have permission to edit this {title} for this operator.")
        return redirect(f'/operator/{operator_slug}/{board_type}/')

    days = dayType.objects.all()
    
    # Get categories for this operator and board type
    qs = board_category.objects.filter(
        operator=operator,
        board_type=board_type
    ).prefetch_related('subcategories')

    # Numeric-aware sort key (same as routes)
    def parse_name_key(name):
        rn = (name or '').upper()

        normal = re.match(r'^([0-9]+)$', rn)
        xprefix = re.match(r'^X([0-9]+)$', rn)
        suffix = re.match(r'^([0-9]+)([A-Z]+)$', rn)
        other = re.match(r'^([A-Z]+)([0-9]+)$', rn)

        if normal:
            return (0, int(normal.group(1)), "")
        if suffix:
            return (1, int(suffix.group(1)), suffix.group(2))
        if xprefix:
            return (2, int(xprefix.group(1)), "X")
        if other:
            return (3, other.group(1), int(other.group(2)))
        return (4, rn, 0)

    try:
        categories = list(qs)
        categories.sort(key=lambda c: parse_name_key(c.name))
    except Exception:
        categories = qs.order_by('name')

    if request.method == "POST":
        duty_name = request.POST.get('duty_name')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        brake_times = request.POST.getlist('brake_times')
        selected_days = request.POST.getlist('duty_day')
        category_id = request.POST.get('category')

        # Format break times
        formatted_brakes = " | ".join(brake_times)

        # Get category if selected
        selected_category = None
        if category_id:
            selected_category = board_category.objects.filter(id=category_id, operator=operator).first()

        # Update the duty instance
        duty_instance.duty_name = duty_name
        duty_instance.duty_details = {
            "logon_time": start_time,
            "logoff_time": end_time,
            "brake_times": formatted_brakes
        }
        duty_instance.category = selected_category

        duty_instance.save()

        # Update ManyToMany field for days
        if selected_days:
            duty_instance.duty_day.set(selected_days)
        else:
            duty_instance.duty_day.clear()

        messages.success(request, f"{title} updated successfully.")
        return redirect(f'/operator/{operator_slug}/{board_type}/')

    else:
        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
            {'name': titles, 'url': f'/operator/{operator_slug}/{board_type}/'},
            {'name': f"Edit {duty_instance.duty_name}", 'url': f'/operator/{operator_slug}/{board_type}/edit/{duty_instance.id}/'}
        ]

        tabs = generate_tabs("duties", operator)

        context = {
            'operator': operator,
            'days': days,
            'categories': categories,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
            'duty_instance': duty_instance,
            'board_type': board_type,
        }
        return render(request, 'edit_duty.html', context)

@login_required
def board_categories(request, operator_slug):
    """View and manage board categories for an operator."""
    response = feature_enabled(request, "view_boards")
    if response:
        return response
    
    is_running_board = 'running-boards' in request.resolver_match.route
    board_type = 'running-boards' if is_running_board else 'duty'
    title = "Running Board" if is_running_board else "Duty"
    titles = "Running Boards" if is_running_board else "Duties"

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)

    # Get top-level categories (no parent) for this operator
    qs = board_category.objects.filter(
        operator=operator,
        board_type=board_type,
        parent_category__isnull=True
    ).prefetch_related('subcategories')

    # Numeric-aware ordering (same system as routes)
    try:
        def parse_name_key(name):
            rn = (name or '').upper()

            normal = re.match(r'^([0-9]+)$', rn)
            xprefix = re.match(r'^X([0-9]+)$', rn)
            suffix = re.match(r'^([0-9]+)([A-Z]+)$', rn)
            other = re.match(r'^([A-Z]+)([0-9]+)$', rn)

            if normal:
                return (0, int(normal.group(1)), "")
            if suffix:
                return (1, int(suffix.group(1)), suffix.group(2))
            if xprefix:
                return (2, int(xprefix.group(1)), "X")
            if other:
                return (3, other.group(1), int(other.group(2)))
            return (4, rn, 0)

        categories = list(qs)
        categories.sort(key=lambda c: parse_name_key(c.name))
    except Exception:
        categories = qs.order_by('name')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': titles, 'url': f'/operator/{operator_slug}/{board_type}/'},
        {'name': 'Categories', 'url': f'/operator/{operator_slug}/{board_type}/categories/'}
    ]

    tabs = generate_tabs("duties", operator)

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'categories': categories,
        'tabs': tabs,
        'user_perms': userPerms,
        'title': title,
        'titles': titles,
        'board_type': board_type,
    }
    return render(request, 'board_categories.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def board_category_add(request, operator_slug):
    """Add a new board category."""
    response = feature_enabled(request, "add_boards")
    if response:
        return response
    
    is_running_board = 'running-boards' in request.resolver_match.route
    board_type = 'running-boards' if is_running_board else 'duty'
    title = "Running Board" if is_running_board else "Duty"
    titles = "Running Boards" if is_running_board else "Duties"

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add categories for this operator.")
        return redirect(f'/operator/{operator_slug}/{board_type}/categories/')

    # Get existing categories for parent selection
    existing_categories = board_category.objects.filter(
        operator=operator,
        board_type=board_type,
        parent_category__isnull=True  # Only top-level categories can be parents
    )

    if request.method == "POST":
        name = request.POST.get('name')
        parent_id = request.POST.get('parent_category')
        
        parent = None
        if parent_id:
            parent = get_object_or_404(board_category, id=parent_id, operator=operator)

        board_category.objects.create(
            name=name,
            operator=operator,
            board_type=board_type,
            parent_category=parent
        )

        messages.success(request, "Category added successfully.")
        return redirect(f'/operator/{operator_slug}/{board_type}/categories/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': titles, 'url': f'/operator/{operator_slug}/{board_type}/'},
        {'name': 'Categories', 'url': f'/operator/{operator_slug}/{board_type}/categories/'},
        {'name': 'Add Category', 'url': f'/operator/{operator_slug}/{board_type}/categories/add/'}
    ]

    tabs = generate_tabs("duties", operator)

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'existing_categories': existing_categories,
        'tabs': tabs,
        'user_perms': userPerms,
        'title': title,
        'titles': titles,
        'board_type': board_type,
    }
    return render(request, 'board_category_add.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def board_category_edit(request, operator_slug, category_id):
    """Edit an existing board category."""
    response = feature_enabled(request, "edit_boards")
    if response:
        return response
    
    is_running_board = 'running-boards' in request.resolver_match.route
    board_type = 'running-boards' if is_running_board else 'duty'
    title = "Running Board" if is_running_board else "Duty"
    titles = "Running Boards" if is_running_board else "Duties"

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    category_instance = get_object_or_404(board_category, id=category_id, operator=operator)
    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit categories for this operator.")
        return redirect(f'/operator/{operator_slug}/{board_type}/categories/')

    # Get existing categories for parent selection (exclude self and children)
    existing_categories = board_category.objects.filter(
        operator=operator,
        board_type=board_type,
        parent_category__isnull=True
    ).exclude(id=category_id)

    if request.method == "POST":
        name = request.POST.get('name')
        parent_id = request.POST.get('parent_category')
        
        parent = None
        if parent_id:
            parent = get_object_or_404(board_category, id=parent_id, operator=operator)

        category_instance.name = name
        category_instance.parent_category = parent
        category_instance.save()

        messages.success(request, "Category updated successfully.")
        return redirect(f'/operator/{operator_slug}/{board_type}/categories/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': titles, 'url': f'/operator/{operator_slug}/{board_type}/'},
        {'name': 'Categories', 'url': f'/operator/{operator_slug}/{board_type}/categories/'},
        {'name': f'Edit {category_instance.name}', 'url': f'/operator/{operator_slug}/{board_type}/categories/edit/{category_id}/'}
    ]

    tabs = generate_tabs("duties", operator)

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'category_instance': category_instance,
        'existing_categories': existing_categories,
        'tabs': tabs,
        'user_perms': userPerms,
        'title': title,
        'titles': titles,
        'board_type': board_type,
    }
    return render(request, 'board_category_edit.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def board_category_delete(request, operator_slug, category_id):
    """Delete a board category."""
    response = feature_enabled(request, "edit_boards")
    if response:
        return response
    
    is_running_board = 'running-boards' in request.resolver_match.route
    board_type = 'running-boards' if is_running_board else 'duty'

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    category_instance = get_object_or_404(board_category, id=category_id, operator=operator)
    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete categories for this operator.")
        return redirect(f'/operator/{operator_slug}/{board_type}/categories/')

    if request.method == "POST":
        # Clear category from any duties that use it
        duty.objects.filter(category=category_instance).update(category=None)
        category_instance.delete()
        messages.success(request, "Category deleted successfully.")
        return redirect(f'/operator/{operator_slug}/{board_type}/categories/')

    return redirect(f'/operator/{operator_slug}/{board_type}/categories/')

@login_required
@require_http_methods(["GET", "POST"])
def log_trip(request, operator_slug, vehicle_id):
    response = feature_enabled(request, "log_trips")
    if response:
        return response

    vehicle = get_object_or_404(fleet, id=vehicle_id)

    operator = None

    if vehicle.operator != vehicle.loan_operator and vehicle.loan_operator is not None:
        operator = get_object_or_404(MBTOperator, operator_slug=vehicle.loan_operator.operator_slug)
    else:
        operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Log Trips' not in userPerms and not request.user.is_superuser:
        return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/')

    # Always define both forms
    timetable_form = TripFromTimetableForm(operator=operator, vehicle=vehicle)
    manual_form = ManualTripForm(operator=operator, vehicle=vehicle)

    if request.method == 'POST':
        if 'timetable_submit' in request.POST:
            timetable_form = TripFromTimetableForm(request.POST, operator=operator, vehicle=vehicle)
            if timetable_form.is_valid():
                timetable_form.save()
                return redirect('vehicle_detail', operator_slug=operator_slug, vehicle_id=vehicle_id)
        elif 'manual_submit' in request.POST:
            manual_form = ManualTripForm(request.POST, operator=operator, vehicle=vehicle)
            if manual_form.is_valid():
                manual_form.save()
                return redirect('vehicle_detail', operator_slug=operator_slug, vehicle_id=vehicle_id)
            else:
                for field, errors in manual_form.errors.items():
                    for error in errors:
                        if field == '__all__':
                            messages.error(request, error)
                        else:
                            messages.error(request, f"{field}: {error}")

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
def operator_edit(request, operator_slug):
    response = feature_enabled(request, "edit_operators")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    # Make these available to both POST and GET
    groups = group.objects.filter(Q(group_owner=request.user) | Q(private=False)).order_by('group_name')
    games = game.objects.filter(active=True).order_by('game_name')
    if request.user.is_superuser:
        organisations = organisation.objects.all().order_by('organisation_name')
    else:
        organisations = organisation.objects.filter(organisation_owner=request.user).order_by('organisation_name')
    operator_types = operatorType.objects.filter(published=True).order_by('operator_type_name')
    try:
        current_map = operator.mapTile.id
    except:
        current_map = 1

    mapTileSetAll = mapTileSet.objects.all()

    regions = region.objects.all().order_by('region_country', 'region_name')
    grouped_regions = defaultdict(list)
    for r in regions:
        grouped_regions[r.region_country].append(r)
    regionData = dict(grouped_regions)

    if request.user != operator.owner and not request.user.is_superuser:
        return redirect(f'/operator/{operator_slug}')

    if request.method == "POST":
        old_operator_data = MBTOperator.objects.get(id=operator.id)
        mapTile_id = request.POST.get('map', None)
        if mapTile_id:
            try:
                mapTileSet_instance = mapTileSet.objects.get(id=mapTile_id)
            except mapTileSet.DoesNotExist:
                mapTileSet_instance = mapTileSet.objects.get(id=1)
                print(f"MapTileSet with ID {mapTile_id} does not exist.")
        else:
            mapTileSet_instance = mapTileSet.objects.get(id=1)
            print("No mapTileSet ID provided in POST data.")

        original_operator_name = operator.operator_name
        original_operator_code = operator.operator_code

        new_operator_name = request.POST.get('operator_name', '').strip()
        new_operator_code = request.POST.get('operator_code', '').strip()

        if original_operator_name != new_operator_name:
            check_name = MBTOperator.objects.filter(operator_name__iexact=new_operator_name).exclude(id=operator.id)
            if check_name.exists():
                messages.error(request, "An operator with this name already exists.")
                return redirect(f'/operator/{operator_slug}/edit/')

        if original_operator_code != new_operator_code:
            check_code = MBTOperator.objects.filter(operator_code__iexact=new_operator_code).exclude(id=operator.id)
            if check_code.exists():
                messages.error(request, "An operator with this code already exists.")
                return redirect(f'/operator/{operator_slug}/edit/')

        operator.operator_name = new_operator_name
        operator.operator_code = new_operator_code
        operator.mapTile = mapTileSet_instance
        region_ids = request.POST.getlist('operator_region')
        operator.region.set(region_ids)

        operator.show_livery_border = request.POST.get('show_livery_border') == 'on'

        if request.POST.get('group', None) == "":
            group_instance = None
        else:
            try:
                group_instance = group.objects.get(id=request.POST.get('group'))
            except group.DoesNotExist:
                group_instance = None

        operator.group = group_instance

        organisation_instance = operator.organisation
        if request.user.is_superuser:
            if request.POST.get('organisation', None) == "":
                organisation_instance = None
            else:
                try:
                    organisation_instance = organisation.objects.get(id=request.POST.get('organisation'))
                except (organisation.DoesNotExist, ValueError, TypeError):
                    organisation_instance = operator.organisation

        operator.group = group_instance
        operator.organisation = organisation_instance

        operator_details = {
            'website': request.POST.get('website', '').strip(),
            'twitter': request.POST.get('twitter', '').strip(),
            'game': request.POST.get('game', '').strip(),
            'type': request.POST.get('type', '').strip(),
            'transit_authorities': request.POST.get('transit_authorities', '').strip(),
        }

        operator.operator_details = operator_details

        new_operator_data = operator

        changes = []  # collect all field change messages here

        for field in ['operator_name', 'operator_code', 'mapTile', 'region', 'group', 'organisation', 'operator_details']:
            old_value = getattr(old_operator_data, field)
            new_value = getattr(new_operator_data, field)

            # Handle ManyToMany field (region)
            if field == 'region':
                old_value_set = set(old_value.all())
                new_value_set = set(new_value.all())
                if old_value_set != new_value_set:
                    old_names = ', '.join([r.region_name for r in old_value_set]) or 'None'
                    new_names = ', '.join([r.region_name for r in new_value_set]) or 'None'
                    changes.append(f"**{field}** changed from {old_names} → {new_names}")

            # Handle JSON/dict field (operator_details)
            elif field == 'operator_details':
                for key in set(list(old_value.keys()) + list(new_value.keys())):
                    old_detail = old_value.get(key, '')
                    new_detail = new_value.get(key, '')
                    if old_detail != new_detail:
                        changes.append(f"**{field}.{key}** changed from '{old_detail}' → '{new_detail}'")

            # Handle normal fields
            else:
                if old_value != new_value:
                    old_val = old_value or 'None'
                    new_val = new_value or 'None'
                    changes.append(f"**{field}** changed from '{old_val}' → '{new_val}'")

        # Send ONE Discord message if there were any changes
        if changes:
            message = "\n".join(changes)
            send_to_discord_embed(
                DISCORD_FULL_OPERATOR_LOGS_ID,
                f"Operator edited",
                message,
                0x3498DB  # int, not string
            )

        # Finally save the operator
        operator.save()

        messages.success(request, "Operator updated successfully.")
        return redirect(f'/operator/{operator_slug}')

    else:
        # GET request — prepare context for the form
        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
            {'name': 'Edit Operator', 'url': f'/operator/{operator_slug}/edit/'}
        ]

        tabs = generate_tabs("routes", operator)

        operatorGame = operator.operator_details.get('game', None)

        context = {
            'currentMap': current_map,
            'mapTileSets': mapTileSetAll,
            'operator': operator,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
            'groups': groups,
            'games': games,
            'organisations': organisations,
            'regionData': regionData,
            'operatorGame': operatorGame,
            'operator_types': operator_types,
        }
        return render(request, 'edit_operator.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_delete(request, operator_slug):
    response = feature_enabled(request, "delete_operators")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    if request.user != operator.owner and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this operator.")
        return redirect(f'/operator/{operator_slug}/')

    if request.method == "POST":
        count = fleet.objects.filter(operator=operator).count()
        if (count > 10):
           send_to_discord_delete(count, settings.DISCORD_OPERATOR_LOGS_ID, operator.operator_name)

        send_to_discord_embed(DISCORD_FULL_OPERATOR_LOGS_ID, f"Operator deleted", f"**{operator.operator_name}** has been deleted by {request.user.username}.", 0xED4245)

        operator.delete()
        messages.success(request, f"Operator '{operator.operator_slug}' deleted successfully.")
        return redirect('/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Delete Operator', 'url': f'/operator/{operator_slug}/delete/'}
    ]

    tabs = generate_tabs("routes", operator)

    context = {
        'operator': operator,
        'breadcrumbs': breadcrumbs,
        'tabs': tabs,
    }
    return render(request, 'delete_operator.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_reset(request, operator_slug):
    response = feature_enabled(request, "reset_operators")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    if request.user != operator.owner and not request.user.is_superuser:
        messages.error(request, "You do not have permission to reset this operator.")
        return redirect(f'/operator/{operator_slug}/')

    if request.method == "POST":
       
        vehicles = fleet.objects.filter(operator=operator)

        for vehicle in vehicles:
            vehicle.operator = MBTOperator.objects.filter(operator_code="UC").first()
            vehicle.save() 

        messages.success(request, f"Operator '{operator.operator_slug}' has successfully been reset.")
        return redirect(f'/operator/{operator_slug}/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Reset Operator', 'url': f'/operator/{operator_slug}/reset/'}
    ]

    tabs = generate_tabs("routes", operator)

    context = {
        'operator': operator,
        'breadcrumbs': breadcrumbs,
        'tabs': tabs,
    }
    return render(request, 'reset_operator.html', context)



@login_required
@require_http_methods(["GET", "POST"])
def vehicle_add(request, operator_slug):
    response = feature_enabled(request, "add_vehicles")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Buses' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add a bus for this operator.")
        return redirect(f'/operator/{operator_slug}/vehicles/')

    # Load dropdown/related data
    operators = MBTOperator.objects.all()
    types = vehicleType.objects.all()
    liveries_list = liverie.objects.all()
    allowed_operators = []

    if request.user.is_authenticated:
        helper_operator_ids = helper.objects.filter(
            helper=request.user,
            perms__perm_name="Buy Buses"
        ).values_list("operator_id", flat=True)

        # 3. Combined queryset (owners + allowed helpers)
        allowed_operators = MBTOperator.objects.filter(
            Q(id__in=helper_operator_ids) | Q(owner=request.user)
        ).distinct().order_by('operator_name')

    path = "JSON/features.json"

    data = safe_json_load(path, default={})
    features_list = data.get("features", [])

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

        custom = request.POST.get('custom', '').strip()

        json_custom = {}
        for line in custom.splitlines():
            # Match "Key"="Value"
            match = re.match(r'^\s*"?(.+?)"?\s*[:=]\s*"?(.+?)"?\s*$', line)
            if match:
                key, value = match.groups()
                json_custom[key.strip()] = value.strip()

        vehicle.advanced_details = json_custom

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

        try:
            from routes.models import board_category as BoardCategory
            vc_id = request.POST.get('vehicle_category')
            if vc_id:
                try:
                    cat = BoardCategory.objects.get(id=vc_id)
                    if cat.operator and vehicle.operator and cat.operator.id == vehicle.operator.id:
                        vehicle.vehicle_category = cat
                    else:
                        vehicle.vehicle_category = None
                except BoardCategory.DoesNotExist:
                    vehicle.vehicle_category = None
            else:
                vehicle.vehicle_category = None
        except Exception:
            pass

        vehicle.features = features_selected
        vehicle.save()

        messages.success(request, "Vehicle added successfully.")
        return redirect(f'/operator/{operator_slug}/vehicles/')

    else:
        # GET: Prepare blank form
        vehicle = fleet()  # Blank for add form

        features_selected = []

        user_data = [request.user]

        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
            {'name': 'Vehicles', 'url': f'/operator/{operator_slug}/vehicles/'},
            {'name': 'Add Vehicle', 'url': f'/operator/{operator_slug}/vehicles/add/'}
        ]

        tabs = []

        try:
            from routes.models import board_category as BoardCategory
            category_list = BoardCategory.objects.filter(operator=operator)
        except Exception:
            category_list = []

        context = {
            'operator_current': operator,
            'fleetData': vehicle,
            'operatorData': operators,
            'typeData': types,
            'liveryData': liveries_list,
            'features': features_list,
            'userData': user_data,
            'breadcrumbs': breadcrumbs,
            'category_list': category_list,
            'tabs': tabs,
            'allowed_operators': allowed_operators,
        }
        return render(request, 'add.html', context)
    
@login_required
@require_http_methods(["GET", "POST"])
def vehicle_mass_add(request, operator_slug):
    response = feature_enabled(request, "mass_add_vehicles")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Mass Add Buses' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add a bus for this operator.")
        return redirect(f'/operator/{operator_slug}/vehicles/')

    # Load dropdown/related data
    operators = MBTOperator.objects.all()
    types = vehicleType.objects.all()
    liveries_list = liverie.objects.all()
    allowed_operators = []

    if request.user.is_authenticated:
        helper_operator_ids = helper.objects.filter(
            helper=request.user,
            perms__perm_name="Mass Add Buses"
        ).values_list("operator_id", flat=True)

        # 3. Combined queryset (owners + allowed helpers)
        allowed_operators = MBTOperator.objects.filter(
            Q(id__in=helper_operator_ids) | Q(owner=request.user)
        ).distinct().order_by('operator_name')


    path = "JSON/features.json"
    data = safe_json_load(path, default={})
    features_list = data.get("features", [])

    if request.method == 'POST':
        now = timezone.now()
        last_add = request.session.get('last_mass_add')

        if last_add:
            last_add_time = timezone.datetime.fromisoformat(last_add)
            if now - last_add_time < timedelta(minutes=2):
                request.session['last_mass_add'] = now.isoformat()
                remaining = 120 - int((now - last_add_time).total_seconds())
                return JsonResponse({
                    'error': f'Rate limited. Try again in {remaining} seconds.'
                }, status=429)

        request.session['last_mass_add'] = now.isoformat()

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

        custom = request.POST.get('custom', '').strip()

        json_custom = {}
        for line in custom.splitlines():
            # Match "Key"="Value"
            match = re.match(r'^\s*"?(.+?)"?\s*[:=]\s*"?(.+?)"?\s*$', line)
            if match:
                key, value = match.groups()
                json_custom[key.strip()] = value.strip()

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

        try:
            from routes.models import board_category as BoardCategory
            vc_id = request.POST.get('vehicle_category')
            if vc_id:
                try:
                    cat = BoardCategory.objects.get(id=vc_id)
                    if cat.operator and vehicle.operator and cat.operator.id == vehicle.operator.id:
                        vehicle.vehicle_category = cat
                    else:
                        vehicle.vehicle_category = None
                except BoardCategory.DoesNotExist:
                    vehicle.vehicle_category = None
            else:
                vehicle.vehicle_category = None
        except Exception:
            pass

        created_count = 0
        for i in range(1, number_of_vehicles + 1):
            fleet_number = request.POST.get(f'fleet_number_{i}', '').strip()
            reg = request.POST.get(f'reg_{i}', '').strip()

            if fleet_number == "":
                fleet_number = ""
                
            if reg == "":
                reg = ""

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
            vehicle.advanced_details = json_custom

            vehicle.save()
            created_count += 1

        messages.success(request, f"{created_count} vehicle(s) added successfully.")
        return redirect(f'/operator/{operator_slug}/vehicles/')


    else:
        # GET: Prepare blank form
        vehicle = fleet()  # Blank for add form

        features_selected = []

        user_data = [request.user]

        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
            {'name': 'Vehicles', 'url': f'/operator/{operator_slug}/vehicles/'},
            {'name': 'Add Vehicle', 'url': f'/operator/{operator_slug}/vehicles/add/'}
        ]

        tabs = []

        try:
            from routes.models import board_category as BoardCategory
            category_list = BoardCategory.objects.filter(operator=operator)
        except Exception:
            category_list = []

        context = {
            'fleetData': vehicle,
            'operator_current': operator,
            'operatorData': allowed_operators,
            'typeData': types,
            'liveryData': liveries_list,
            'features': features_list,
            'userData': user_data,
            'breadcrumbs': breadcrumbs,
            'categoryData': category_list,
            'tabs': tabs,
        }
        return render(request, 'mass_add.html', context)

def deduplicate_queryset(queryset):
    seen = {}
    duplicates = []

    for obj in queryset:
        key = (obj.reg.strip().upper(), obj.fleet_number.strip().upper())
        if key in seen:
            duplicates.append(obj)
        else:
            seen[key] = obj

    for dup in duplicates:
        dup.delete()

    return len(duplicates)

@login_required
def deduplicate_operator_fleet(request, operator_slug):
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    queryset = fleet.objects.filter(operator=operator)  # or however your relation works

    if request.user != operator.owner and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit vehicles for this operator.")
        return redirect(f'/operator/{operator_slug}/vehicles/') # or raise PermissionDenied

    removed = deduplicate_queryset(queryset)
    messages.success(request, f"{removed} duplicate vehicles removed from {operator.operator_slug}.")
    
    return redirect(f'/operator/{operator_slug}/vehicles/')

def deduplicate_routes_queryset(queryset):
    seen = {}
    duplicates = []

    for obj in queryset:
        key = (
            obj.route_num.strip().upper() if obj.route_num else '',
            obj.inbound_destination.strip().upper() if obj.inbound_destination else '',
            obj.outbound_destination.strip().upper() if obj.outbound_destination else ''
        )
        if key in seen:
            duplicates.append(obj)
        else:
            seen[key] = obj

    for dup in duplicates:
        dup.delete()

    return len(duplicates)


@login_required
def deduplicate_operator_routes(request, operator_slug):
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    queryset = route.objects.filter(route_operators=operator)  # or however your relation works

    if request.user != operator.owner and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit vehicles for this operator.")
        return redirect(f'/operator/{operator_slug}/')  # adjust field as needed

    removed = deduplicate_routes_queryset(queryset)
    messages.success(request, f"{removed} duplicate routes removed from {operator.operator_slug}.")
    
    return redirect(f'/operator/{operator_slug}/')

@login_required
@require_http_methods(["GET", "POST"])
def vehicle_mass_edit(request, operator_slug):
    response = feature_enabled(request, "mass_edit_vehicles")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    userPerms = get_helper_permissions(request.user, operator)
    if request.user != operator.owner and 'Mass Edit Buses' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit vehicles for this operator.")
        return redirect(f'/operator/{operator_slug}/vehicles/')

    # Parse vehicle IDs from ?ids= query param
    vehicle_ids_str = request.GET.get("ids", "")
    vehicle_ids = [int(id.strip()) for id in vehicle_ids_str.split(",") if id.strip().isdigit()]
    vehicles = list(fleet.objects.filter(id__in=vehicle_ids, operator=operator))

    # If some requested IDs were filtered out (i.e. mismatched operator or missing), fail fast.
    if len(vehicles) != len(vehicle_ids):
        messages.error(request, "One or more selected vehicles do not belong to the specified operator or could not be found.")
        return redirect(f'/operator/{operator_slug}/vehicles/')

    if not vehicles:
        messages.error(request, "No valid vehicles selected for editing.")
        return redirect(f'/operator/{operator_slug}/vehicles/')

    # Dropdown data
    operators = MBTOperator.objects.all()
    types = vehicleType.objects.all()
    liveries_list = liverie.objects.all()
    allowed_operators = []

    if request.user.is_authenticated:
        helper_operator_ids = helper.objects.filter(
            helper=request.user,
            perms__perm_name="Mass Edit Buses"
        ).values_list("operator_id", flat=True)

        # 3. Combined queryset (owners + allowed helpers)
        allowed_operators = MBTOperator.objects.filter(
            Q(id__in=helper_operator_ids) | Q(owner=request.user)
        ).distinct().order_by('operator_name')

    path = "JSON/features.json"
    features_json = safe_json_load(path, default={})
    features_list = features_json.get("features", [])

    if request.method == "POST":
        updated_count = 0
        currently_for_sale = fleet.objects.filter(operator=operator, for_sale=True).count()
        total_vehicles = len(vehicles)
        for i, vehicle in enumerate(vehicles, start=1):
            # Get updated fields for this vehicle
            vehicle.fleet_number = request.POST.get(f'fleet_number_{i}', vehicle.fleet_number).strip()
            vehicle.reg = request.POST.get(f'reg_{i}', vehicle.reg).strip()

            delete = 'delete' in request.POST

            vehicle.in_service = 'in_service' in request.POST
            vehicle.preserved = 'preserved' in request.POST
            vehicle.open_top = 'open_top' in request.POST
            vehicle.for_sale = 'for_sale' in request.POST
            vehicle.type_details = request.POST.get('type_details', '').strip()
            vehicle.length = request.POST.get('length', '').strip() or None
            vehicle.colour = request.POST.get('colour', '').strip()
            vehicle.branding = request.POST.get('branding', '').strip()
            vehicle.prev_reg = request.POST.get('prev_reg', '').strip()
            vehicle.depot = request.POST.get('depot', '').strip()
            vehicle.name = request.POST.get('name', '').strip()
            vehicle.notes = request.POST.get('notes', '').strip()
            vehicle.summary = request.POST.get('summary', '').strip()

            custom = request.POST.get('custom', '').strip()

            json_custom = {}
            for line in custom.splitlines():
                # Match "Key"="Value"
                match = re.match(r'^\s*"?(.+?)"?\s*[:=]\s*"?(.+?)"?\s*$', line)
                if match:
                    key, value = match.groups()
                    json_custom[key.strip()] = value.strip()

            vehicle.advanced_details = json_custom

            current_operator = vehicle.operator

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

            # Vehicle category (shared field in the form) — ensure it belongs to the operator
            try:
                from routes.models import board_category as BoardCategory
                vc_id = request.POST.get('vehicle_category')
                if vc_id:
                    try:
                        cat = BoardCategory.objects.get(id=vc_id)
                        if cat.operator and vehicle.operator and cat.operator.id == vehicle.operator.id:
                            vehicle.vehicle_category = cat
                        else:
                            vehicle.vehicle_category = None
                    except BoardCategory.DoesNotExist:
                        vehicle.vehicle_category = None
                else:
                    vehicle.vehicle_category = None
            except Exception:
                pass

            try:
                features_selected = json.loads(request.POST.get('features', '[]'))
                vehicle.features = features_selected
            except json.JSONDecodeError:
                pass

            delete_all = 'delete' in request.POST
            for_sale = 'for_sale' in request.POST

            if vehicle.operator != current_operator:
                for_sale = False
                vehicle.for_sale = False

            if delete_all:
                for vehicle in vehicles:
                    vehicle.delete()
                messages.success(request, f"{len(vehicles)} vehicle(s) deleted successfully.")
                return redirect(f'/operator/{operator_slug}/vehicles/')
            else:
                if for_sale:
                    if request.user.is_authenticated and request.user.banned_from.filter(name='selling_buses').exists():
                        return redirect('selling_buses_banned')

                    total_for_sale = currently_for_sale + total_vehicles

                    if total_for_sale >= max_for_sale:
                        messages.error(request, f"You can only list {max_for_sale} vehicles for sale.")
                        vehicle.for_sale = False
                        vehicle.save()
                        return redirect(f'/operator/{operator_slug}/vehicles/')
                    else:
                        vehicle.for_sale = True
                        encoded_operator_slug = quote(operator_slug)
                    title = "Vehicle Listed for Sale"
                    description = f"**{operator.operator_name}** has listed {vehicle.fleet_number} - {vehicle.reg} for sale."
                    fields = [
                        {"name": "Fleet Number", "value": vehicle.fleet_number if hasattr(vehicle, 'fleet_number') else 'N/A', "inline": True},
                        {"name": "Registration", "value": vehicle.reg if hasattr(vehicle, 'reg') else 'N/A', "inline": True},
                        {"name": "Type", "value": getattr(vehicle.vehicleType, 'type_name', 'N/A'), "inline": False},
                        {"name": "View", "value": f"https://www.mybustimes.cc/operator/{encoded_operator_slug}/vehicles/{vehicle.id}/?v={random.randint(1000,9999)}", "inline": False}
                    ]

                    if request.user.is_authenticated and request.user.banned_from.filter(name='selling_buses').exists():
                        return redirect('selling_buses_banned')

                    send_to_discord_for_sale_embed(
                        channel_id=settings.DISCORD_FOR_SALE_CHANNEL_ID,
                        title=title,
                        message=description,
                        colour=0xFFA500,
                        fields=fields,
                        image_url=f"https://www.mybustimes.cc/operator/vehicle_image/{vehicle.id}/?v={random.randint(1000,9999)}",
                        content="<@&1348490878024679424>"  # <-- role ping included here
                    )

                    vehicle.save()

                    operator = MBTOperator.objects.get(id=operator.id)
                    for_sale_count = fleet.objects.filter(operator=operator, for_sale=True).count()
                    operator.vehicles_for_sale = for_sale_count
                    operator.save()

                    updated_count += 1
                else:
                    vehicle.save()
                    for_sale_count = fleet.objects.filter(operator=operator, for_sale=True).count()
                    operator.vehicles_for_sale = for_sale_count
                    operator.save()
                    updated_count += 1

        messages.success(request, f"{updated_count} vehicle(s) updated successfully.")
        return redirect(f'/operator/{operator_slug}/vehicles/')

    else:

        if request.user.is_authenticated and request.user.banned_from.filter(name='selling_buses').exists():
            hide_sell_button = True
        else:
            hide_sell_button = False
        # GET: pre-fill form with first vehicle for shared fields
        # categories for this operator
        try:
            from routes.models import board_category as BoardCategory
            category_list = BoardCategory.objects.filter(operator=operator)
        except Exception:
            category_list = []

        context = {
            'hide_sell_button': hide_sell_button,
            'fleetData': vehicles[0],  # Used for shared fields
            'vehicles': vehicles,
            'operatorData': allowed_operators,
            'typeData': types,
            'liveryData': liveries_list,
            'categoryData': category_list,
            'features': features_list,
            'userData': [request.user],
            'vehicle_count': len(vehicles),
            "custom": advanced_details_to_text(vehicles[0].advanced_details),
            'breadcrumbs': [
                {'name': 'Home', 'url': '/'},
                {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
                {'name': 'Vehicles', 'url': f'/operator/{operator_slug}/vehicles/'},
                {'name': 'Mass Edit', 'url': request.path},
            ],
            'tabs': [],
        }
        return render(request, 'mass_edit.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def vehicle_select_mass_edit(request, operator_slug):
    response = feature_enabled(request, "mass_edit_vehicles")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Mass Edit Buses' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit vehicles for this operator.")
        return redirect(f'/operator/{operator_slug}/vehicles/')
    
    vehicles = (
        fleet.objects.filter(operator=operator)
        .select_related('vehicleType', 'livery')
        .only(
            'id',
            'fleet_number',
            'reg',
            'fleet_number_sort',
            'branding',
            'colour',
            'vehicleType__type_name',
            'livery__name',
            'livery__left_css',
        )
        .order_by('fleet_number_sort', 'fleet_number')
    )

    if request.method == "POST":
        selected_ids = request.POST.getlist('selected_vehicles')
        if not selected_ids:
            messages.error(request, "You must select at least one vehicle.")
            return redirect(request.path)

        # Redirect to mass edit page with selected IDs in query string or session
        id_string = ",".join(selected_ids)
        return redirect(f'/operator/{operator_slug}/vehicles/mass-edit-bus/?ids={id_string}')

    context = {
        'operator': operator,
        'vehicles': vehicles,
    }
    return render(request, 'mass_edit_select.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def duty_select_mass_edit(request, operator_slug):
    response = feature_enabled(request, "mass_edit_boards")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Mass Edit Boards' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to mass edit boards for this operator.")
        return redirect(f'/operator/{operator_slug}/')

    def alphanum_key(name):
        key_parts = []

        for text in re.split(r'([0-9]+)', name or ''):
            if not text:
                continue
            if text.isdigit():
                key_parts.append((0, int(text)))
            else:
                key_parts.append((1, text.lower()))

        return tuple(key_parts)

    duties_qs = list(duty.objects.filter(duty_operator=operator))
    duties_qs.sort(key=lambda d: alphanum_key(d.duty_name))

    if request.method == "POST":
        selected_ids = request.POST.getlist('selected_duties')
        if not selected_ids:
            messages.error(request, "You must select at least one board.")
            return redirect(request.path)

        id_string = ",".join(selected_ids)
        return redirect(f'/operator/{operator_slug}/duties/mass-edit/?ids={id_string}')

    context = {
        'operator': operator,
        'duties': duties_qs,
    }
    return render(request, 'mass_edit_select_boards.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def duty_mass_edit(request, operator_slug):
    response = feature_enabled(request, "mass_edit_boards")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)
    if request.user != operator.owner and 'Mass Edit Boards' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to mass edit boards for this operator.")
        return redirect(f'/operator/{operator_slug}/duties/')

    ids = request.GET.get('ids', '')
    duty_ids = [int(x) for x in ids.split(',') if x.strip().isdigit()]
    duties = list(duty.objects.filter(id__in=duty_ids, duty_operator=operator))

    if not duties:
        messages.error(request, "No valid boards selected for editing.")
        return redirect(f'/operator/{operator_slug}/duties/')

    # Categories for this operator (numeric-aware ordered)
    try:
        qs_categories = board_category.objects.filter(operator=operator)
        def _parse_name_key(name):
            rn = (name or '').upper()
            normal = re.match(r'^([0-9]+)$', rn)
            xprefix = re.match(r'^X([0-9]+)$', rn)
            suffix = re.match(r'^([0-9]+)([A-Z]+)$', rn)
            other = re.match(r'^([A-Z]+)([0-9]+)$', rn)
            if normal:
                return (0, int(normal.group(1)), "")
            if suffix:
                return (1, int(suffix.group(1)), suffix.group(2))
            if xprefix:
                return (2, int(xprefix.group(1)), "X")
            if other:
                return (3, other.group(1), int(other.group(2)))
            return (4, rn, 0)

        category_list = list(qs_categories)
        category_list.sort(key=lambda c: _parse_name_key(c.name))
    except Exception:
        category_list = board_category.objects.filter(operator=operator).order_by('name')

    if request.method == 'POST':
        updated = 0
        for i, bd in enumerate(duties, start=1):
            name = request.POST.get(f'duty_name_{i}', bd.duty_name).strip()
            cat_id = request.POST.get(f'category_{i}')
            board_type_val = request.POST.get(f'board_type_{i}', bd.board_type)

            bd.duty_name = name

            if cat_id:
                try:
                    c = board_category.objects.get(id=cat_id)
                    if c.operator and bd.duty_operator and c.operator.id == bd.duty_operator.id:
                        bd.category = c
                    else:
                        bd.category = None
                except board_category.DoesNotExist:
                    bd.category = None
            else:
                bd.category = None

            if board_type_val in ['duty', 'running-boards']:
                bd.board_type = board_type_val

            bd.save()
            updated += 1

        messages.success(request, f"{updated} board(s) updated successfully.")
        return redirect(f'/operator/{operator_slug}/duties/')

    context = {
        'duties': duties,
        'categoryData': category_list,
        'breadcrumbs': [
            {'name': 'Home', 'url': '/'},
            {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
            {'name': 'Duties', 'url': f'/operator/{operator_slug}/duties/'},
            {'name': 'Mass Edit Boards', 'url': request.path},
        ],
        'tabs': generate_tabs('duties', operator),
        'operator': operator,
    }
    return render(request, 'mass_edit_boards.html', context)
 
@login_required
@require_http_methods(["GET", "POST"])
def route_add(request, operator_slug):
    response = feature_enabled(request, "add_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Routes' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add a route for this operator.")
        return redirect(f'/operator/{operator_slug}/vehicles/')

    if request.method == "POST":
        # Extract form data
        route_depot = request.POST.get('route_depot')
        route_num = request.POST.get('route_number')
        route_name = request.POST.get('route_name')
        inbound = request.POST.get('inbound_destination')
        outbound = request.POST.get('outbound_destination')
        other_dests = request.POST.get('other_destinations')
        school_service = request.POST.get('school_service') == 'on'
        hidden = request.POST.get('hidden_service') == 'on'
        start_date = request.POST.get('start_date')

        # Related many-to-many fields
        linkable_routes_ids = request.POST.getlist('linkable_routes')
        related_routes_ids = request.POST.getlist('related_routes')
        payment_method_ids = request.POST.getlist('payment_methods')

        #route colouring
        route_text_color = request.POST.get('route_text_color')
        route_background_color = request.POST.get('route_background_color')
        route_text_color_enabled = request.POST.get('route_text_color_enabled') == 'on'
        route_background_color_enabled = request.POST.get('route_background_color_enabled') == 'on'

        # Convert other destinations to list
        other_dest_list = [d.strip() for d in other_dests.split(',')] if other_dests else []

        if route_text_color_enabled:
            text_colour = route_text_color
        else:
            text_colour = "var(--text-color)"

        if route_background_color_enabled:
            background_colour = route_background_color
        else:
            background_colour = "var(--background-color)"

        # Build route_details
        route_details = {
            "route_colour": background_colour,
            "route_text_colour": text_colour,
            "details": {
                "school_service": str(school_service).lower(),
                "contactless": str('1' in payment_method_ids).lower(),
                "cash": str('2' in payment_method_ids).lower()
            }
        }

        if start_date:
            start_date = start_date
        else:
            start_date = None

        # Create the route
        new_route = route.objects.create(
            route_num=route_num,
            route_name=route_name,
            inbound_destination=inbound,
            outbound_destination=outbound,
            other_destination=other_dest_list,
            start_date=start_date,
            route_details=route_details,
            route_depot=route_depot,
            hidden=hidden
        )
        new_route.route_operators.add(operator)

        if linkable_routes_ids:
            new_route.linked_route.set(route.objects.filter(id__in=linkable_routes_ids))
        if related_routes_ids:
            new_route.related_route.set(route.objects.filter(id__in=related_routes_ids))

        messages.success(request, "Route added successfully.")
        return redirect(f'/operator/{operator_slug}/route/{new_route.id}/stops/add/inbound/')

    # GET request
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Add Route', 'url': f'/operator/{operator_slug}/add-route/'}
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
def route_mass_edit(request, operator_slug):
    response = feature_enabled(request, "edit_routes")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Routes' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit routes for this operator.")
        return redirect(f'/operator/{operator_slug}/routes/')

    route_qs = (
        route.objects
        .filter(route_operators=operator)
        .prefetch_related('route_operators', 'linked_route', 'related_route')
        .distinct()
        .order_by('route_num', 'route_name', 'id')
    )

    allowed_operators = MBTOperator.objects.none()
    if request.user.is_authenticated:
        helper_operator_ids = helper.objects.filter(
            helper=request.user,
            perms__perm_name="Edit Routes"
        ).values_list("operator_id", flat=True)

        allowed_operators = MBTOperator.objects.filter(
            Q(id__in=helper_operator_ids) | Q(owner=request.user)
        ).distinct().order_by('operator_name')

    class MockPaymentMethod:
        def __init__(self, id, name):
            self.id = id
            self.name = name

        def __str__(self):
            return self.name

    payment_methods = [
        MockPaymentMethod(1, 'Contactless'),
        MockPaymentMethod(2, 'Cash')
    ]

    if request.method == "POST":
        selected_route_ids = request.POST.getlist('selected_routes')
        selected_routes = route_qs.filter(id__in=selected_route_ids)

        if not selected_route_ids or not selected_routes.exists():
            messages.error(request, "Select at least one route to mass edit.")
            return redirect(request.path)

        apply_text_colour = request.POST.get('apply_text_colour') == 'on'
        apply_background_colour = request.POST.get('apply_background_colour') == 'on'
        apply_linked_routes = request.POST.get('apply_linked_routes') == 'on'
        apply_related_routes = request.POST.get('apply_related_routes') == 'on'
        apply_route_operators = request.POST.get('apply_route_operators') == 'on'
        apply_payment_methods = request.POST.get('apply_payment_methods') == 'on'
        apply_school_service = request.POST.get('apply_school_service') == 'on'
        apply_hidden = request.POST.get('apply_hidden') == 'on'

        if not any([
            apply_text_colour,
            apply_background_colour,
            apply_linked_routes,
            apply_related_routes,
            apply_route_operators,
            apply_payment_methods,
            apply_school_service,
            apply_hidden,
        ]):
            messages.error(request, "Choose at least one field to apply.")
            return redirect(request.path)

        route_text_colour = request.POST.get('route_text_color') or '#ffffff'
        route_text_colour_enabled = request.POST.get('route_text_color_enabled') == 'on'
        route_background_colour = request.POST.get('route_background_color') or '#ffffff'
        route_background_colour_enabled = request.POST.get('route_background_color_enabled') == 'on'
        linked_route_ids = request.POST.getlist('linkable_routes')
        related_route_ids = request.POST.getlist('related_routes')
        selected_operator_ids = request.POST.getlist('route_operators')
        payment_method_ids = request.POST.getlist('payment_methods')
        school_service = request.POST.get('school_service') == 'on'
        hidden = request.POST.get('hidden_service') == 'on'

        selected_operator_ids = list(allowed_operators.filter(id__in=selected_operator_ids).values_list('id', flat=True))
        if apply_route_operators and not selected_operator_ids:
            messages.error(request, "Select at least one route operator before applying route operators.")
            return redirect(request.path)

        updated_count = 0
        with transaction.atomic():
            for route_instance in selected_routes:
                route_details = route_instance.route_details or {}
                details = route_details.get('details') or {}

                if apply_text_colour:
                    route_details['route_text_colour'] = route_text_colour if route_text_colour_enabled else 'var(--text-color)'

                if apply_background_colour:
                    route_details['route_colour'] = route_background_colour if route_background_colour_enabled else 'var(--background-color)'

                if apply_payment_methods:
                    details['contactless'] = str('1' in payment_method_ids).lower()
                    details['cash'] = str('2' in payment_method_ids).lower()

                if apply_school_service:
                    details['school_service'] = str(school_service).lower()

                route_details['details'] = details
                route_instance.route_details = route_details

                if apply_hidden:
                    route_instance.hidden = hidden

                route_instance.save(update_fields=['route_details', 'hidden'])

                if apply_linked_routes:
                    route_instance.linked_route.set(route.objects.filter(id__in=linked_route_ids).exclude(id=route_instance.id))

                if apply_related_routes:
                    route_instance.related_route.set(route.objects.filter(id__in=related_route_ids).exclude(id=route_instance.id))

                if apply_route_operators:
                    route_instance.route_operators.set(MBTOperator.objects.filter(id__in=selected_operator_ids))

                updated_count += 1

        messages.success(request, f"Updated {updated_count} route{'s' if updated_count != 1 else ''}.")
        return redirect(f'/operator/{operator_slug}/routes/mass-edit/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Mass Edit Routes', 'url': f'/operator/{operator_slug}/routes/mass-edit/'}
    ]

    context = {
        'operator': operator,
        'breadcrumbs': breadcrumbs,
        'routes': route_qs,
        'linkableAndRelatedRoutes': route_qs,
        'allowedOperators': allowed_operators,
        'paymentMethods': payment_methods,
    }
    return render(request, 'mass_edit_routes.html', context)
    
@login_required
@require_http_methods(["GET", "POST"])
def route_edit(request, operator_slug, route_id):
    response = feature_enabled(request, "edit_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    route_instance = get_object_or_404(route, id=route_id)

    if operator not in route_instance.route_operators.all():
        messages.error(request, "This route does not belong to the specified operator.")
        return redirect(f'/operator/{operator_slug}/')

    has_inbound_stops = routeStop.objects.filter(route=route_instance, inbound=True).exists()
    has_outbound_stops = routeStop.objects.filter(route=route_instance, inbound=False).exists()
    is_circular = routeStop.objects.filter(route=route_instance, circular=True).exists()

    userPerms = get_helper_permissions(request.user, operator)

    allowed_operators = []

    if request.user.is_authenticated:
        helper_operator_ids = helper.objects.filter(
            helper=request.user,
            perms__perm_name="Edit Routes"
        ).values_list("operator_id", flat=True)

        # 3. Combined queryset (owners + allowed helpers)
        allowed_operators = MBTOperator.objects.filter(
            Q(id__in=helper_operator_ids) | Q(owner=request.user)
        ).distinct().order_by('operator_name')

    if request.user != operator.owner and 'Edit Routes' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route.")
        return redirect(f'/operator/{operator_slug}/routes/')

    if request.method == "POST":
        # Extract form data
        route_num = request.POST.get('route_number')
        route_depot = request.POST.get('route_depot')
        route_name = request.POST.get('route_name')
        inbound = request.POST.get('inbound_destination')
        outbound = request.POST.get('outbound_destination')
        other_dests = request.POST.get('other_destinations')
        school_service = request.POST.get('school_service') == 'on'
        hidden = request.POST.get('hidden_service') == 'on'
        start_date = request.POST.get('start_date')

        # Related many-to-many fields
        linkable_routes_ids = request.POST.getlist('linkable_routes')
        related_routes_ids = request.POST.getlist('related_routes')
        selected_operators = request.POST.getlist('route_operators')
        payment_method_ids = request.POST.getlist('payment_methods')

        #route colouring
        route_text_color = request.POST.get('route_text_color')
        route_background_color = request.POST.get('route_background_color')
        route_text_color_enabled = request.POST.get('route_text_color_enabled') == 'on'
        route_background_color_enabled = request.POST.get('route_background_color_enabled') == 'on'

        # Convert other destinations to list
        other_dest_list = [d.strip() for d in other_dests.split(',')] if other_dests else []

        if route_text_color_enabled:
            text_colour = route_text_color
        else:
            text_colour = "var(--text-color)"

        if route_background_color_enabled:
            background_colour = route_background_color
        else:
            background_colour = "var(--background-color)"

        # Build route_details
        route_details = {
            "route_colour": background_colour,
            "route_text_colour": text_colour,
            "details": {
                "school_service": str(school_service).lower(),
                "contactless": str('1' in payment_method_ids).lower(),
                "cash": str('2' in payment_method_ids).lower()
            }
        }

        if start_date:
            start_date = start_date
        else:
            start_date = None

        route_operators = MBTOperator.objects.filter(id__in=selected_operators)

        # Update the route instance
        route_instance.route_operators.set(route_operators)
        route_instance.route_num = route_num
        route_instance.route_name = route_name
        route_instance.inbound_destination = inbound
        route_instance.outbound_destination = outbound
        route_instance.other_destination = other_dest_list
        route_instance.route_details = route_details
        route_instance.start_date = start_date
        route_instance.route_depot = route_depot
        route_instance.hidden = hidden
        route_instance.save()

        # Update relationships
        route_instance.route_operators.set(route_operators)

        if linkable_routes_ids:
            route_instance.linked_route.set(route.objects.filter(id__in=linkable_routes_ids))
        else:
            route_instance.linked_route.clear()

        if related_routes_ids:
            route_instance.related_route.set(route.objects.filter(id__in=related_routes_ids))
        else:
            route_instance.related_route.clear()

        messages.success(request, "Route updated successfully.")
        return redirect(f'/operator/{operator_slug}/route/{route_id}/')

    # GET request - Pre-fill existing data
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Edit Route', 'url': f'/operator/{operator_slug}/route/{route_id}/edit/'}
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

    if route_instance.route_details.get("route_colour") != "var(--background-color)":
        enable_route_colours = True
    else:
        enable_route_colours = False

    if route_instance.route_details.get("route_text_colour") != "var(--text-color)":
        enable_route_text_colours = True
    else:
        enable_route_text_colours = False

    context = {
        'operatorData': operator,
        'userData': [request.user],
        'breadcrumbs': breadcrumbs,
        'linkableAndRelatedRoutes': route.objects.filter(route_operators=operator).exclude(id=route_id),
        'paymentMethods': [
            MockPaymentMethod(1, 'Contactless'),
            MockPaymentMethod(2, 'Cash')
        ],
        'allowedOperators': allowed_operators,
        'routeData': route_instance,
        'selectedLinkables': route_instance.linked_route.values_list('id', flat=True),
        'selectedRelated': route_instance.related_route.values_list('id', flat=True),
        'selectedOperators': route_instance.route_operators.values_list('id', flat=True),
        'selectedPaymentMethods': selected_payment_ids,
        'has_inbound_stops': has_inbound_stops,
        'has_outbound_stops': has_outbound_stops,
        'is_circular': is_circular,
        'enable_route_colours': enable_route_colours,
        'enable_route_text_colours': enable_route_text_colours,
    }

    return render(request, 'edit_route.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def route_delete(request, operator_slug, route_id):
    response = feature_enabled(request, "edit_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    route_instance = get_object_or_404(route, id=route_id)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Delete Routes' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this route.")
        return redirect(f'/operator/{operator_slug}/')
    
    if request.method == "POST":
        route_instance.delete()
        messages.success(request, "Route deleted successfully.")
        return redirect(f'/operator/{operator_slug}/')
    
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Delete Route', 'url': f'/operator/{operator_slug}/route/{route_id}/delete/'}
    ]

    context = {
        'operatorData': operator,
        'userData': [request.user],
        'breadcrumbs': breadcrumbs,
        'routeData': route_instance,
    }

    return render(request, 'confirm_delete_route.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def add_stop_names_only(request, operator_slug, route_id, direction):
    response = feature_enabled(request, "add_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    route_instance = get_object_or_404(route, id=route_id)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Stops' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add stops for this route.")
        return redirect(f'/operator/{operator_slug}/route/{route_id}/')

    if request.method == "POST":
        direction = request.POST.get('direction', direction)
        stop_names = request.POST.getlist('stop_names')
        stop_names = [name.strip() for name in stop_names if name.strip()]

        if not stop_names:
            messages.error(request, "Please provide at least one stop name.")
            return redirect(f'/operator/{operator_slug}/route/{route_id}/stops/add/{direction}/stop-names-only/')

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
        return redirect(f'/operator/{operator_slug}/route/{route_id}/edit/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Add Stop Names', 'url': f'/operator/{operator_slug}/route/{route_id}/stops/add/{direction}/stop-names-only/'}
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
def edit_stop_names_only(request, operator_slug, route_id, direction):
    response = feature_enabled(request, "edit_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    route_instance = get_object_or_404(route, id=route_id)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Stops' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit stops for this route.")
        return redirect(f'/operator/{operator_slug}/route/{route_id}/')

    # Get the existing routeStop object for this route + direction
    stop_obj = routeStop.objects.filter(route=route_instance, inbound=(direction == 'inbound')).first()

    if not stop_obj:
        messages.error(request, f"No existing stops found for this direction.")
        return redirect(f'/operator/{operator_slug}/route/{route_id}/stops/add/{direction}/stop-names-only/')

    if request.method == "POST":
        direction = request.POST.get('direction', direction)
        stop_names = request.POST.getlist('stop_names')
        stop_names = [name.strip() for name in stop_names if name.strip()]

        if not stop_names:
            messages.error(request, "Please provide at least one stop name.")
            return redirect(f'/operator/{operator_slug}/route/{route_id}/stops/edit/{direction}/stop-names-only/')

        # Format new stops and update the object
        stop_obj.stops = [{"stop": name} for name in stop_names]
        stop_obj.save()

        messages.success(request, "Stops updated successfully.")
        return redirect(f'/operator/{operator_slug}/route/{route_id}/edit/')

    # Pre-fill stop names from the existing stop_obj.stops JSON list
    prefilled_stops = [item["stop"] for item in stop_obj.stops]

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Edit Stop Names', 'url': f'/operator/{operator_slug}/route/{route_id}/stops/edit/{direction}/stop-names-only'}
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
def vehicle_delete(request, operator_slug, vehicle_id):
    response = feature_enabled(request, "delete_vehicles")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    vehicle = get_object_or_404(fleet, id=vehicle_id)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Buses' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this vehicle.")
        return redirect(f'/operator/{operator_slug}/vehicles/')

    if request.method == "POST":
        vehicle.delete()
        messages.success(request, f"Vehicle '{vehicle.fleet_number or vehicle.reg or 'unnamed'}' deleted successfully.")
        return redirect(f'/operator/{operator_slug}/vehicles/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Vehicles', 'url': f'/operator/{operator_slug}/vehicles/'},
        {'name': 'Delete Vehicle', 'url': f'/operator/{operator_slug}/vehicle/edit/{vehicle.id}/delete/'}
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
    
    groups = group.objects.filter(Q(group_owner=request.user) | Q(private=False)).order_by('group_name')
    organisations = organisation.objects.filter(organisation_owner=request.user)
    operator_types = operatorType.objects.filter(published=True).order_by('operator_type_name')
    games = game.objects.filter(active=True).order_by('game_name')
    regions = region.objects.all().order_by('region_country', 'region_name')
    mapTileSetAll = mapTileSet.objects.all()

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

        mapTile_id = request.POST.get('map', '1')
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
        mapTileSet_selected = mapTileSet.objects.filter(id=mapTile_id).first() if mapTile_id else mapTileSet.objects.filter(id=1).first()

        new_operator = MBTOperator.objects.create(
            operator_name=operator_name,
            operator_code=operator_code,
            owner=request.user,
            group=operator_group,
            mapTile=mapTileSet_selected,
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

        send_to_discord_embed(DISCORD_FULL_OPERATOR_LOGS_ID, f"Operator created", f"**{new_operator.operator_name}** has been created by {request.user.username}.", 0x1F8B4C)

        messages.success(request, "Operator created successfully.")
        return redirect(f'/operator/{new_operator.operator_slug}/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
    ]

    context = {
        'mapTileSets': mapTileSetAll,
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
def route_timetable_options(request, operator_slug, route_id):
    response = feature_enabled(request, "edit_timetable")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    route_instance = get_object_or_404(route, id=route_id)

    all_timetables = timetableEntry.objects.filter(route=route_instance).prefetch_related('day_type').order_by('id')

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Timetables' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route's timetable.")
        return redirect(f'/operator/{operator_slug}/route/{route_id}/')

    # Get all days
    days = dayType.objects.all()

    if request.method == "POST":
        # Handle timetable editing logic here
        pass  # Placeholder for actual logic

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_slug}/route/{route_id}/'}
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
def route_edit_stops(request, operator_slug, route_id, direction):
    response = feature_enabled(request, "edit_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    mapTiles = operator.mapTile if operator.mapTile else mapTileSet.objects.filter(is_default=True).first()
    route_instance = get_object_or_404(route, id=route_id)

    userPerms = get_helper_permissions(request.user, operator)

    if mapTiles is None:
        mapTiles = mapTileSet.objects.get(id=1)

    if request.user != operator.owner and 'Edit Stops' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route's stops.")
        return redirect(f'/operator/{operator_slug}/route/{route_id}/')

    # Load existing stops + snapped geometry
    try:
        existing_route_stops = routeStop.objects.filter(
            route=route_instance,
            inbound=(direction == "inbound")
        ).first()

        existing_stops = existing_route_stops.stops if existing_route_stops else []
        existing_snapped = existing_route_stops.snapped_route if existing_route_stops else None

    except routeStop.DoesNotExist:
        existing_stops = []
        existing_snapped = None

    # -----------------------------
    #          HANDLE POST
    # -----------------------------
    if request.method == "POST":
        try:
            raw_data = request.POST.get("routeData")
            snapped_raw = request.POST.get("snappedGeometry")

            if not raw_data:
                raise ValueError("Missing routeData")

            parsed_stops = json.loads(raw_data)

            # Optional snapped route data
            if snapped_raw:
                try:
                    parsed_snapped = json.loads(snapped_raw)
                except:
                    parsed_snapped = None
            else:
                parsed_snapped = None

            # Save everything
            routeStop.objects.update_or_create(
                route=route_instance,
                inbound=(direction == "inbound"),
                defaults={
                    "circular": False,
                    "stops": parsed_stops,
                    "snapped_route": parsed_snapped,
                }
            )

            messages.success(request, "Stops & snapped route saved.")
            return redirect(f'/operator/{operator_slug}/route/{route_id}/')

        except Exception as e:
            messages.error(request, f"Failed to update stops: {e}")
            return redirect(request.path)

    # -----------------------------
    #           RENDER PAGE
    # -----------------------------
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_slug}/route/{route_id}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'route': route_instance,
        'helper_permissions': userPerms,
        'direction': direction,
        'mapTile': mapTiles,
        'mapTileSets': mapTileSet.objects.all().order_by('name'),
        'existing_stops': existing_stops,  # Pass existing stops here
        'existing_snapped': existing_snapped,  # Pass existing snapped geometry here
    }
    return render(request, 'route_edit_route.html', context)

@login_required
@require_POST
@csrf_protect
def valhalla_proxy(request):
    url = settings.ROUTEING_URL
    headers = {"Content-Type": "application/json"}

    valhalla_user = getattr(settings, "VALHALLA_USER", None)
    valhalla_pass = getattr(settings, "VALHALLA_PASS", None)
    auth = (valhalla_user, valhalla_pass) if valhalla_user and valhalla_pass else None

    try:
        r = requests.post(url, data=request.body, headers=headers, auth=auth, timeout=30)
    except Exception as e:
        return JsonResponse({"error": f"Proxy request failed: {e}"}, status=500)

    try:
        return JsonResponse(r.json(), safe=False, status=r.status_code)
    except ValueError:
        return HttpResponse(r.text, status=r.status_code)

@login_required
@require_http_methods(["GET", "POST"])
def route_add_stops(request, operator_slug, route_id, direction):
    response = feature_enabled(request, "edit_routes")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    mapTiles = operator.mapTile if operator.mapTile else mapTileSet.objects.filter(is_default=True).first()
    route_instance = get_object_or_404(route, id=route_id)

    userPerms = get_helper_permissions(request.user, operator)

    if mapTiles == None:
        mapTiles = mapTileSet.objects.get(id=1)

    if request.user != operator.owner and 'Add Stops' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route's stops.")
        return redirect(f'/operator/{operator_slug}/route/{route_id}/edit/')

    if request.method == "POST":
        try:
            raw_data = request.POST.get("routeData")
            parsed = json.loads(raw_data)

            stops = parsed["stops"]
            snapped = parsed.get("snapped_geometry", [])

            routeStop.objects.filter(
                route=route_instance,
                inbound=(direction == "inbound")
            ).delete()

            routeStop.objects.create(
                route=route_instance,
                inbound=(direction == "inbound"),
                circular=False,
                stops=stops,
                snapped_route=json.dumps(snapped)
            )

            messages.success(request, "Stops saved successfully.")
            return redirect(f'/operator/{operator_slug}/route/{route_id}/')

        except Exception as e:
            messages.error(request, f"Failed to save stops: {e}")
            return redirect(request.path)


    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_slug}/route/{route_id}/timeable/'}
    ]

    # Fetch inbound route data to show as reference when creating outbound
    inbound_route_geometry = None
    if direction == "outbound":
        inbound_route_stop = routeStop.objects.filter(
            route=route_instance,
            inbound=True
        ).first()
        if inbound_route_stop and inbound_route_stop.snapped_route:
            inbound_route_geometry = inbound_route_stop.snapped_route

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'route': route_instance,
        'helper_permissions': userPerms,
        'direction': direction,
        'mapTile': mapTiles,
        'mapTileSets': mapTileSet.objects.all().order_by('name'),
        'inbound_route_geometry': inbound_route_geometry,
    }
    return render(request, 'route_add_route.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def route_timetable_add(request, operator_slug, route_id, direction):
    response = feature_enabled(request, "add_timetable")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    route_instance = get_object_or_404(route, id=route_id)

    serialized_route = routesSerializer(route_instance).data
    full_route_num = serialized_route.get('full_searchable_name', '')

    userPerms = get_helper_permissions(request.user, operator)
    days = dayType.objects.all()

    if request.user != operator.owner and 'Add Timetables' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route's timetable.")
        return redirect(f'/operator/{operator_slug}/route/{route_id}/')

    stops = routeStop.objects.filter(route=route_instance, inbound=direction == "inbound").first()

    # Filter out waypoints from stops for timetable
    if stops and stops.stops:
        stops.stops = [s for s in stops.stops if not s.get('waypoint', False)]

    if request.method == "POST":
        base_times_str = request.POST.get("departure_times")
        selected_days = request.POST.getlist("days[]")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        if start_date == "":
            start_date = None

        if end_date == "":
            end_date = None
        
        try:
            # Ensure at least one day is selected
            if not selected_days:
                raise ValueError("Please select at least one day.")

            # Parse base times
            base_times = [datetime.strptime(t.strip(), "%H:%M") for t in base_times_str.split(",") if t.strip()]
            if not base_times:
                raise ValueError("No base times provided.")

            stop_times_json = request.POST.get("stop_times_json")

            # Save to DB
            entry = timetableEntry.objects.create(
                route=route_instance,
                inbound=(direction == "inbound"),
                stop_times=stop_times_json,
                operator_schedule=[],
            )
            entry.day_type.set(dayType.objects.filter(id__in=selected_days))
            entry.start_date = start_date
            entry.end_date = end_date
            entry.save()

            messages.success(request, "Timetable saved successfully.")
            return redirect(f'/operator/{operator_slug}/route/{route_id}/')

        except Exception as e:
            messages.error(request, f"Error saving timetable: {e}")
            return redirect(request.path)


    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_slug}/route/{route_id}/'}
    ]

    has_inbound_stops = routeStop.objects.filter(route=route_instance, inbound=True).exists()
    has_outbound_stops = routeStop.objects.filter(route=route_instance, inbound=False).exists()
    
    if not has_inbound_stops and direction == "inbound":
        messages.error(request, "You must add inbound stops to this route before editing the timetable.")
        return redirect(f'/operator/{operator_slug}/route/{route_id}/stops/add/inbound/')

    if not has_outbound_stops and direction == "outbound":
        messages.error(request, "You must add outbound stops to this route before editing the timetable.")
        return redirect(f'/operator/{operator_slug}/route/{route_id}/stops/add/outbound/')

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
def route_timetable_import(request, operator_slug, route_id, direction):
    response = feature_enabled(request, "import_bustimes_timetable")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    route_instance = get_object_or_404(route, id=route_id)
    serialized_route = routesSerializer(route_instance).data
    full_route_num = serialized_route.get('full_searchable_name', '')

    userPerms = get_helper_permissions(request.user, operator)
    days = dayType.objects.all()

    if request.user != operator.owner and 'Edit Timetables' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route's timetable.")
        return redirect(f'/operator/{operator_slug}/route/{route_id}/')

    stops = routeStop.objects.filter(route=route_instance, inbound=direction == "inbound").first()

    if request.method == "POST":
        timetable_url = request.POST.get("timetable_url")
        selected_days = request.POST.getlist("days[]")

        if not timetable_url:
            messages.error(request, "Please provide a BusTimes.org URL.")
            return redirect(request.path)

        if not selected_days:
            messages.error(request, "Please select at least one day.")
            return redirect(request.path)

        try:
            # Scrape the timetable from the provided URL
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(timetable_url, headers=headers)
            soup = BeautifulSoup(res.text, "html.parser")

            timetable_data = {}
            stop_order = 0
            groupings = soup.select("div.groupings div.grouping")

            # Pick first grouping if inbound, second if outbound
            grouping_index = 1 if direction == "inbound" else 0

            # If there's only one grouping, use it regardless of direction
            if len(groupings) == 1:
                selected_grouping = groupings[0]
            elif grouping_index < len(groupings):
                selected_grouping = groupings[grouping_index]
            else:
                raise ValueError("Expected direction timetable not found.")

            table = selected_grouping.find("table", class_="timetable")
            if not table:
                raise ValueError("No timetable table found in selected grouping.")

            rows = table.find_all("tr")
            timetable_data = {}
            stop_counter = {}

            for row in rows:
                stop_th = row.find("th", class_="stop-name")
                if not stop_th:
                    continue

                stop_name = stop_th.text.strip()
                timing_point = 'minor' not in row.get('class', [])
                times = [td.text.strip() if td.text.strip() else "" for td in row.find_all("td")]

                # Handle duplicate stop names
                if stop_name in stop_counter:
                    stop_counter[stop_name] += 1
                    stop_key = f"{stop_name} (Terminus)"
                else:
                    stop_counter[stop_name] = 0
                    stop_key = stop_name

                timetable_data[stop_key] = {
                    "stopname": stop_name,
                    "timing_point": timing_point,
                    "times": times,
                    "departure_times": times,
                    "arrival_times": times,
                }

            if not timetable_data:
                raise ValueError("No timetable data found on page.")

            entry = timetableEntry.objects.create(
                route=route_instance,
                inbound=(direction == "inbound"),
                stop_times=json.dumps(timetable_data, ensure_ascii=False),
                operator_schedule="",  # Still a valid JSON string for now
            )

            entry.day_type.set(dayType.objects.filter(id__in=selected_days))
            entry.save()

            messages.success(request, "Timetable imported successfully.")
            return redirect(f'/operator/{operator_slug}/route/{route_id}/')

        except Exception as e:
            messages.error(request, f"Failed to import: {e}")
            return redirect(request.path)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_slug}/route/{route_id}/'}
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
def route_timetable_edit(request, operator_slug, route_id, timetable_id):
    response = feature_enabled(request, "edit_timetable")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    route_instance = get_object_or_404(route, id=route_id)
    timetable_instance = get_object_or_404(timetableEntry, id=timetable_id)

    serialized_route = routesSerializer(route_instance).data
    full_route_num = serialized_route.get('full_searchable_name', '')

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Timetables' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route's timetable.")
        return redirect(f'/operator/{operator_slug}/route/{route_id}/')

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
                raw_arrival_times = request.POST.get(f"arrival_times_{index}") or ""
                is_timing_point = request.POST.get(f"timing_point_{index}") == "on"

                # Parse times safely
                times = [
                    t.strip().strip('"').strip("'")
                    for t in raw_times.split(",")
                    if t.strip()
                ]
                arrival_times = [
                    t.strip().strip('"').strip("'")
                    for t in raw_arrival_times.split(",")
                    if t.strip()
                ]
                if not arrival_times:
                    arrival_times = times

                # Keep the original _idx_ID key
                original_key = request.POST.get(f"original_key_{index}", f"stop_idx_{index}")
                stop_times_result[original_key] = {
                    "stopname": stop_name,
                    "timing_point": is_timing_point,
                    "times": times,
                    "departure_times": times,
                    "arrival_times": arrival_times,
                }

            selected_days = request.POST.getlist("days[]")
            if not selected_days:
                raise ValueError("Please select at least one day.")

            operator_schedule = request.POST.get("operator_schedule", "").strip()
            if operator_schedule:
                final_operator_schedule = [code.strip().strip('"').strip("'") for code in operator_schedule.split(",") if code.strip()]
                timetable_instance.operator_schedule = final_operator_schedule
            else:
                timetable_instance.operator_schedule = []

            # Save changes
            if request.POST.get("start_date"):
                start_date = request.POST.get("start_date")
            else:
                start_date = None

            if request.POST.get("end_date"):
                end_date = request.POST.get("end_date")
            else:
                end_date = None

            timetable_instance.stop_times = json.dumps(stop_times_result)
            timetable_instance.day_type.set(dayType.objects.filter(id__in=selected_days))
            timetable_instance.inbound = request.POST.get("inbound") == "on"
            timetable_instance.start_date = start_date
            timetable_instance.end_date = end_date
            timetable_instance.save()

            messages.success(request, "Timetable updated successfully.")
            return redirect(f'/operator/{operator_slug}/route/{route_id}/')

        except Exception as e:
            messages.error(request, f"Error updating timetable: {e}")
            return redirect(request.path)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_slug}/route/{route_id}/'}
    ]

    formatted_operator_schedule = str(timetable_instance.operator_schedule)
    formatted_operator_schedule = formatted_operator_schedule.strip('[').strip(']').replace("'", "").replace('"', '')

    if route_instance.route_operators.count() > 1:
        showOperatorSchedule = True
    else:
        showOperatorSchedule = False

    context = {
        'showOperatorSchedule': showOperatorSchedule,
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'route': route_instance,
        'days': days,
        'formatted_operator_schedule': formatted_operator_schedule,
        'helper_permissions': userPerms,
        'timetable_entry': timetable_instance,
        'stop_times': normalize_timetable_stop_times(json.loads(timetable_instance.stop_times)),
        'full_route_num': full_route_num,
        'direction': 'inbound' if timetable_instance.inbound else 'outbound',
        'selected_days': timetable_instance.day_type.values_list('id', flat=True),
    }
    return render(request, 'timetable_edit.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def route_timetable_delete(request, operator_slug, route_id, timetable_id):
    response = feature_enabled(request, "delete_timetable")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    route_instance = get_object_or_404(route, id=route_id)
    timetable_entry = get_object_or_404(timetableEntry, id=timetable_id, route=route_instance)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Delete Timetables' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this timetable entry.")
        return redirect(f'/operator/{operator_slug}/route/{route_id}/')

    if request.method == "POST":
        timetable_entry.delete()
        messages.success(request, "Timetable entry deleted successfully.")
        return redirect(f'/operator/{operator_slug}/route/{route_id}/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_slug}/route/{route_id}/'}
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
            "content": f"New operator type created: **{operator_type_name}** by {request.user.username}\n[Review](https://www.mybustimes.cc/admin/operator-management/pending/)\n",
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

def vehicle_types(request):
    types = vehicleType.objects.filter(hidden=False).order_by('type_name').annotate(
        vehicle_count=Count('fleet', distinct=True),
        pending_requests=Count('change_requests', filter=Q(change_requests__status='pending'))
    )
    pending_delete_ids = list(
        VehicleTypeChangeRequest.objects.filter(
            request_type='delete',
            status='pending'
        ).values_list('vehicle_type_id', flat=True)
    )

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Vehicle Types', 'url': '/operator/vehicle-types/'},
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'vehicle_types': types,
        'pending_delete_ids': pending_delete_ids,
    }
    return render(request, 'vehicle_types.html', context)

def vehicle_types_stats(request):
    types = vehicleType.objects.filter(hidden=False).order_by('type_name').annotate(
        vehicle_count=Count('fleet', distinct=True)
    )

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Vehicle Types Stats', 'url': '/operator/vehicle-types/stats/'},
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'vehicle_types': types,
    }
    return render(request, 'vehicle_types_stats.html', context)

@login_required
def vehicle_types_admin(request):
    if not request.user.is_superuser:
        messages.error(request, "Only superusers can view pending vehicle type requests.")
        return redirect('/operator/vehicle-types/')

    pending_requests = VehicleTypeChangeRequest.objects.filter(
        status='pending'
    ).select_related(
        'vehicle_type',
        'requested_by',
        'replacement_type'
    ).order_by('-created_at')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Vehicle Types', 'url': '/operator/vehicle-types/'},
        {'name': 'Pending Requests', 'url': '/operator/vehicle-types/admin/'},
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'pending_requests': pending_requests,
    }
    return render(request, 'vehicle_types_admin.html', context)


@login_required
def vehicle_types_stats(request):
    editors = (
        VehicleTypeChangeRequest.objects.filter(request_type='edit', status='approved')
        .values('requested_by__id', 'requested_by__username')
        .annotate(edits=Count('id'))
        .order_by('-edits')[:10]
    )

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Vehicle Types', 'url': '/operator/vehicle-types/'},
        {'name': 'Top Editors', 'url': '/operator/vehicle-types/stats/'},
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'editors': editors,
    }
    return render(request, 'vehicle_types_stats.html', context)

def vehicle_type_detail_view(request, type_id):
    vehicle_type = get_object_or_404(vehicleType, id=type_id)
    pending_requests = VehicleTypeChangeRequest.objects.filter(
        vehicle_type=vehicle_type,
        status='pending'
    ).order_by('-created_at')
    all_requests = VehicleTypeChangeRequest.objects.filter(
        vehicle_type=vehicle_type
    ).order_by('-created_at')

    pending_delete_ids = list(
        VehicleTypeChangeRequest.objects.filter(
            request_type='delete',
            status='pending'
        ).values_list('vehicle_type_id', flat=True)
    )
    pending_delete_exists = vehicle_type.id in pending_delete_ids
    replacement_options = vehicleType.objects.filter(active=True).exclude(
        id=vehicle_type.id
    ).exclude(
        id__in=pending_delete_ids
    ).order_by('type_name')
    vehicle_count = fleet.objects.filter(vehicleType=vehicle_type).count()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action in ['edit', 'delete'] and not request.user.is_authenticated:
            messages.error(request, "Please log in to submit a request.")
            return redirect(f'/operator/vehicle-types/{vehicle_type.id}/')

        if action == 'edit':
            proposed = {}
            text_fields = ['type_name', 'type', 'fuel', 'lengths']
            bool_fields = ['double_decker', 'active', 'hidden']
            required_fields = ['type_name', 'type', 'fuel']

            for field in text_fields:
                new_value = request.POST.get(field, '').strip()
                old_value = getattr(vehicle_type, field) or ''
                if field in required_fields and new_value == '' and old_value != '':
                    messages.error(request, f"{field.replace('_', ' ').title()} cannot be blank.")
                    return redirect(f'/operator/vehicle-types/{vehicle_type.id}/')
                if new_value != old_value:
                    proposed[field] = {'old': old_value, 'new': new_value}

            for field in bool_fields:
                new_value = field in request.POST
                old_value = bool(getattr(vehicle_type, field))
                if new_value != old_value:
                    proposed[field] = {'old': old_value, 'new': new_value}

            if not proposed:
                messages.error(request, "No changes detected.")
                return redirect(f'/operator/vehicle-types/{vehicle_type.id}/')

            VehicleTypeChangeRequest.objects.create(
                vehicle_type=vehicle_type,
                requested_by=request.user,
                request_type='edit',
                proposed_changes=proposed,
            )
            messages.success(request, "Edit request submitted.")
            return redirect(f'/operator/vehicle-types/{vehicle_type.id}/')

        if action == 'delete':
            if pending_delete_exists:
                messages.error(request, "A delete request is already pending for this type.")
                return redirect(f'/operator/vehicle-types/{vehicle_type.id}/')

            replacement_id = request.POST.get('replacement_type') or None
            replacement_type = None

            if vehicle_count > 0:
                if not replacement_id:
                    messages.error(request, "A replacement type is required when this type is in use.")
                    return redirect(f'/operator/vehicle-types/{vehicle_type.id}/')
                replacement_type = get_object_or_404(vehicleType, id=replacement_id)
                if replacement_type.id in pending_delete_ids:
                    messages.error(request, "That replacement type has a pending delete request.")
                    return redirect(f'/operator/vehicle-types/{vehicle_type.id}/')
            elif replacement_id:
                replacement_type = get_object_or_404(vehicleType, id=replacement_id)

            VehicleTypeChangeRequest.objects.create(
                vehicle_type=vehicle_type,
                requested_by=request.user,
                request_type='delete',
                replacement_type=replacement_type,
            )
            messages.success(request, "Delete request submitted.")
            return redirect(f'/operator/vehicle-types/{vehicle_type.id}/')

        if action in ['approve', 'disapprove']:
            if not request.user.is_superuser:
                messages.error(request, "Only superusers can review requests.")
                return redirect(f'/operator/vehicle-types/{vehicle_type.id}/')

            request_id = request.POST.get('request_id')
            change_request = get_object_or_404(VehicleTypeChangeRequest, id=request_id)

            if change_request.status != 'pending':
                messages.error(request, "This request has already been reviewed.")
                return redirect(f'/operator/vehicle-types/{vehicle_type.id}/')

            change_request.reviewed_by = request.user
            change_request.reviewed_at = timezone.now()

            if action == 'disapprove':
                change_request.status = 'disapproved'
                change_request.disapproved_reason = request.POST.get('disapproved_reason', '').strip()
                change_request.save()
                messages.success(request, "Request disapproved.")
                return redirect(f'/operator/vehicle-types/{vehicle_type.id}/')

            if change_request.request_type == 'edit':
                type_obj = change_request.vehicle_type
                if not type_obj:
                    messages.error(request, "Vehicle type no longer exists.")
                    return redirect('/operator/vehicle-types/')

                for field, change in (change_request.proposed_changes or {}).items():
                    setattr(type_obj, field, change.get('new'))
                type_obj.save()

                change_request.status = 'approved'
                change_request.save()
                messages.success(request, "Edit request approved.")
                return redirect(f'/operator/vehicle-types/{vehicle_type.id}/')

            if change_request.request_type == 'delete':
                type_obj = change_request.vehicle_type
                if not type_obj:
                    messages.error(request, "Vehicle type no longer exists.")
                    return redirect('/operator/vehicle-types/')

                replacement_type = change_request.replacement_type
                in_use_count = fleet.objects.filter(vehicleType=type_obj).count()

                if in_use_count > 0 and not replacement_type:
                    messages.error(request, "A replacement type is required before deletion.")
                    return redirect(f'/operator/vehicle-types/{vehicle_type.id}/')

                if replacement_type and VehicleTypeChangeRequest.objects.filter(
                    vehicle_type=replacement_type,
                    request_type='delete',
                    status='pending'
                ).exists():
                    messages.error(request, "Replacement type has a pending delete request.")
                    return redirect(f'/operator/vehicle-types/{vehicle_type.id}/')

                if replacement_type:
                    fleet.objects.filter(vehicleType=type_obj).update(vehicleType=replacement_type)

                change_request.status = 'approved'
                change_request.save()
                type_obj.delete()
                messages.success(request, "Delete request approved.")
                return redirect('/operator/vehicle-types/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Vehicle Types', 'url': '/operator/vehicle-types/'},
        {'name': vehicle_type.type_name, 'url': f'/operator/vehicle-types/{vehicle_type.id}/'},
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'vehicle_type': vehicle_type,
        'pending_requests': pending_requests,
        'all_requests': all_requests,
        'replacement_options': replacement_options,
        'vehicle_count': vehicle_count,
        'pending_delete_exists': pending_delete_exists,
    }
    return render(request, 'vehicle_type_detail.html', context)

def operator_game_detail(request, operator_game_name):
    response = feature_enabled(request, "view_operator_types")
    if response:
        return response

    operator_game = get_object_or_404(game, game_name=operator_game_name)
    operators = MBTOperator.objects.filter(operator_details__game=operator_game.game_name).order_by("operator_slug")

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Operator Games', 'url': '/operator/games/'},
        {'name': operator_game.game_name, 'url': f'/operator/games/{operator_game.game_name}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator_game': operator_game,
        'operators': operators,
    }
    return render(request, 'operator_game_detail.html', context)


def operator_updates(request, operator_slug):
    response = feature_enabled(request, "view_operator_updates")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    updates = companyUpdate.objects.filter(operator=operator).order_by('-created_at')

    perms = get_helper_permissions(request.user, operator)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Operator Updates', 'url': f'/operator/{operator_slug}/updates/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'updates': updates,
        'perms': perms,
        'operator': operator,
    }
    return render(request, 'operator_updates.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_update_add(request, operator_slug):
    response = feature_enabled(request, "add_operator_updates")
    if response:
        return response
    
    operator = MBTOperator.objects.filter(operator_slug=operator_slug).first()
    routes = route.objects.filter(route_operators=operator)

    userPerms = get_helper_permissions(request.user, operator)
    if request.user != operator.owner and 'Add Updates' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add this update.")
        return redirect(f'/operator/{operator_slug}/')

    if request.method == "POST":
        update_text = request.POST.get('update_text', '').strip()
        selected_routes = request.POST.getlist('routes')  # this gets multiple values from multi-select

        if not update_text:
            messages.error(request, "Update text cannot be empty.")
            return redirect(f'/operator/{operator_slug}/updates/add/')

        new_update = companyUpdate.objects.create(
            operator=operator,
            update_text=update_text
        )

        if selected_routes:
            new_update.routes.set(selected_routes)

        messages.success(request, "Update created successfully.")
        return redirect(f'/operator/{operator_slug}/updates/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Add Update', 'url': f'/operator/{operator_slug}/updates/add/'}
    ]

    return render(request, 'add_operator_update.html', {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'routes': routes,
    })

@login_required
@require_http_methods(["GET", "POST"])
def operator_update_edit(request, operator_slug, update_id):
    response = feature_enabled(request, "edit_operator_updates")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    update = get_object_or_404(companyUpdate, id=update_id)
    routes = route.objects.filter(route_operators=update.operator)

    userPerms = get_helper_permissions(request.user, update.operator)
    if request.user != update.operator.owner and 'Edit Updates' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this update.")
        return redirect(f'/operator/{operator_slug}/')

    if request.method == "POST":
        update_text = request.POST.get('update_text', '').strip()
        selected_routes = request.POST.getlist('routes')

        if not update_text:
            messages.error(request, "Update text cannot be empty.")
            return redirect(f'/operator/{operator_slug}/updates/edit/{update_id}/')

        update.update_text = update_text
        update.routes.set(selected_routes)
        update.save()

        messages.success(request, "Update edited successfully.")
        return redirect(f'/operator/{operator_slug}/updates/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Edit Update', 'url': f'/operator/{operator_slug}/updates/edit/{update_id}/'}
    ]

    return render(request, 'edit_operator_update.html', {
        'breadcrumbs': breadcrumbs,
        'update': update,
        'operator': update.operator,
        'routes': routes,
    })

@login_required
@require_http_methods(["GET", "POST"])
def operator_update_delete(request, operator_slug, update_id):
    response = feature_enabled(request, "delete_operator_updates")
    if response:
        return response
    
    update = get_object_or_404(companyUpdate, id=update_id)

    operator = update.operator

    userPerms = get_helper_permissions(request.user, update.operator)
    if request.user != update.operator.owner and 'Delete Updates' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this update.")
        return redirect(f'/operator/{operator_slug}/')

    if request.method == "POST":
        update.delete()
        messages.success(request, "Update deleted successfully.")
        return redirect(f'/operator/{operator_slug}/updates/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Delete Update', 'url': f'/operator/{operator_slug}/updates/delete/{update_id}/'}
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
def operator_helpers(request, operator_slug):
    response = feature_enabled(request, "view_helpers")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    helpers = helper.objects.filter(operator=operator)

    if request.user != operator.owner and not request.user.is_superuser:
        messages.error(request, "You do not have permission to manage helpers for this operator.")
        return redirect(f'/operator/{operator_slug}/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Helpers', 'url': f'/operator/{operator_slug}/helpers/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'helpers': helpers,
    }
    return render(request, 'operator_helpers.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_helper_add(request, operator_slug):
    response = feature_enabled(request, "add_helpers")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    if request.user != operator.owner and not request.user.is_superuser:
        messages.error(request, "You do not have permission to manage helpers for this operator.")
        return redirect(f'/operator/{operator_slug}/')

    if request.method == "POST":
        form = OperatorHelperForm(request.POST)
        if form.is_valid():
            helper_instance = form.save(commit=False)
            helper_instance.operator = operator
            helper_instance.save()
            # Save many-to-many perms field
            form.save_m2m()
            return redirect('operator_helpers', operator_slug=operator_slug)

    else:
        form = OperatorHelperForm()

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Helpers', 'url': f'/operator/{operator_slug}/helpers/'},
        {'name': 'Add Helper', 'url': f'/operator/{operator_slug}/helpers/add/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'form': form,
    }
    return render(request, 'operator_helper_add.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_helper_edit(request, operator_slug, helper_id):
    response = feature_enabled(request, "edit_helpers")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    helper_instance = get_object_or_404(helper, id=helper_id, operator=operator)

    if request.user != operator.owner and not request.user.is_superuser:
        messages.error(request, "You do not have permission to manage helpers for this operator.")
        return redirect(f'/operator/{operator_slug}/')

    if request.method == "POST":
        form = OperatorHelperForm(request.POST, instance=helper_instance)
        if form.is_valid():
            form.save()
            return redirect('operator_helpers', operator_slug=operator_slug)
    else:
        form = OperatorHelperForm(instance=helper_instance)


    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Helpers', 'url': f'/operator/{operator_slug}/helpers/'},
        {'name': 'Edit Helper', 'url': f'/operator/{operator_slug}/helpers/edit/{helper_id}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'form': form,
        'helper': helper_instance,
    }
    return render(request, 'operator_helper_edit.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_helper_delete(request, operator_slug, helper_id):
    response = feature_enabled(request, "delete_helpers")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    helper_instance = get_object_or_404(helper, id=helper_id, operator=operator)

    if request.user != operator.owner and not request.user.is_superuser:
        messages.error(request, "You do not have permission to manage helpers for this operator.")
        return redirect(f'/operator/{operator_slug}/')

    if request.method == "POST":
        helper_instance.delete()
        messages.success(request, "Helper deleted successfully.")
        return redirect('operator_helpers', operator_slug=operator_slug)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Helpers', 'url': f'/operator/{operator_slug}/helpers/'},
        {'name': 'Delete Helper', 'url': f'/operator/{operator_slug}/helpers/remove/{helper_id}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'helper': helper,
    }
    return render(request, 'confirm_delete_helper.html', context)

def operator_tickets(request, operator_slug):
    response = feature_enabled(request, "view_tickets")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    # Get all distinct zones (including blank/None)
    raw_zones = ticket.objects.filter(operator=operator).values_list('zone', flat=True).distinct()

    zones = []
    has_other = False

    for z in raw_zones:
        if not z or str(z).strip() == "":
            has_other = True
        else:
            zones.append(z)

    # Optionally sort zones alphabetically
    zones.sort()

    if has_other:
        zones.append("Other")

    userPerms = get_helper_permissions(request.user, operator)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Tickets', 'url': f'/operator/{operator_slug}/tickets/'}
    ]

    context = {
        'operator': operator,
        'zones': zones,
        'breadcrumbs': breadcrumbs,
        'userPerms': userPerms,
    }
    return render(request, 'operator_tickets_zones.html', context)

def operator_tickets_details(request, operator_slug, zone_name):
    response = feature_enabled(request, "view_tickets")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    if zone_name == "Other":
        tickets = ticket.objects.filter(
            operator=operator
        ).filter(
            Q(zone__isnull=True) | Q(zone__exact="") | Q(zone__regex=r"^\s*$")
        )
    else:
        tickets = ticket.objects.filter(operator=operator, zone=zone_name)

    userPerms = get_helper_permissions(request.user, operator)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Tickets', 'url': f'/operator/{operator_slug}/tickets/'},
        {'name': zone_name, 'url': f'/operator/{operator_slug}/tickets/{zone_name}/'}
    ]

    context = {
        'zone': zone_name,
        'operator': operator,
        'tickets': tickets,
        'breadcrumbs': breadcrumbs,
        'userPerms': userPerms,
    }
    return render(request, 'operator_tickets.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_ticket_add(request, operator_slug):
    response = feature_enabled(request, "add_tickets")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    userPerms = get_helper_permissions(request.user, operator)
    if request.user != operator.owner and 'Add Tickets' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add tickets for this operator.")
        return redirect(f'/operator/{operator_slug}/')

    if request.method == "POST":
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.operator = operator
            ticket.save()
            messages.success(request, "Ticket created successfully.")
            return redirect('operator_tickets', operator_slug=operator_slug)
    else:
        form = TicketForm()

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Tickets', 'url': f'/operator/{operator_slug}/tickets/'},
        {'name': 'Add Ticket', 'url': f'/operator/{operator_slug}/tickets/add/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'form': form,
    }
    return render(request, 'add_operator_ticket.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def operator_ticket_edit(request, operator_slug, ticket_id):
    response = feature_enabled(request, "edit_tickets")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    ticket_instance = get_object_or_404(ticket, id=ticket_id, operator=operator)

    userPerms = get_helper_permissions(request.user, operator)
    if request.user != operator.owner and 'Edit Tickets' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this ticket.")
        return redirect(f'/operator/{operator_slug}/')

    if request.method == "POST":
        form = TicketForm(request.POST, instance=ticket_instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Ticket updated successfully.")
            return redirect('operator_tickets', operator_slug=operator_slug)
    else:
        form = TicketForm(instance=ticket_instance)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Tickets', 'url': f'/operator/{operator_slug}/tickets/'},
        {'name': 'Edit Ticket', 'url': f'/operator/{operator_slug}/tickets/edit/{ticket_id}/'}
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
def operator_ticket_delete(request, operator_slug, ticket_id):
    response = feature_enabled(request, "delete_tickets")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    ticket_instance = get_object_or_404(ticket, id=ticket_id, operator=operator)

    userPerms = get_helper_permissions(request.user, operator)
    if request.user != operator.owner and 'Delete Tickets' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this ticket.")
        return redirect(f'/operator/{operator_slug}/')

    if request.method == "POST":
        ticket_instance.delete()
        messages.success(request, "Ticket deleted successfully.")
        return redirect('operator_tickets', operator_slug=operator_slug)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Tickets', 'url': f'/operator/{operator_slug}/tickets/'},
        {'name': 'Delete Ticket', 'url': f'/operator/{operator_slug}/tickets/delete/{ticket_id}/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'ticket': ticket,
    } 
    return render(request, 'confirm_delete_ticket.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def mass_log_trips(request, operator_slug):
    """
    Handle mass logging of Trip records for an operator from manual input, a Duty, or a Running Board.
    
    Processes POST submissions to create one or more Trip records:
    - Manual mode: generates a sequence of trips for a selected route and vehicle using provided start time, duration, count, and break interval; sets trip start/end locations and determines inbound flag based on route endpoints.
    - Duty/Running Board mode: creates trips for each DutyTrip in the selected duty or running board for a chosen date; associates created trips with the originating duty/board and propagates inbound status.
    Performs permission checks, model validation (collecting and reporting ValidationError messages), and redirects back to the page on success or error. On GET, renders the mass-log-trips page with duties, running boards, vehicles, routes, and breadcrumbs in the context.
    
    Parameters:
        request (HttpRequest): The incoming Django request object (GET or POST).
        operator_slug (str): Slug identifying the operator for which trips are being logged.
    
    Returns:
        HttpResponse: A redirect on form submission or validation error, or a rendered template response for the mass-log-trips page.
    """
    response = feature_enabled(request, "mass_log_trips")
    if response:
        return response

    end_location = None
    start_location = None
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    userPerms = get_helper_permissions(request.user, operator)
    if request.user != operator.owner and 'Mass Log Trips' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to log trips for this operator.")
        return redirect(f'/operator/{operator_slug}/')

    if request.method == "POST":
        vehicle_id = request.POST.get("vehicle")

        if request.POST.get("vehicle"):
            vehicle_id = request.POST.get("vehicle")
        elif request.POST.get("running_board_vehicle"):
            vehicle_id = request.POST.get("running_board_vehicle")
        elif request.POST.get("duty_vehicle"):
            vehicle_id = request.POST.get("duty_vehicle")
        else:
            vehicle_id = None

        duty_id = request.POST.get("duty")
        running_board_id = request.POST.get("running_board")
        start_at = request.POST.get("start_at")

        # Validate vehicle id from POST before querying
        if not vehicle_id:
            messages.error(request, "No vehicle selected.")
            return redirect(request.path)

        try:
            vehicle_pk = int(vehicle_id)
        except (TypeError, ValueError):
            messages.error(request, "Invalid vehicle selected.")
            return redirect(request.path)

        vehicle = get_object_or_404(fleet, id=vehicle_pk)

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
            start_at = request.POST.get("start_at")  # Already extracted earlier

            route_obj = get_object_or_404(route, id=route_id)

            today = datetime.today()
            start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M")
            current_start = make_aware(start_time)

            if route_obj.outbound_destination and route_obj.inbound_destination:
                if start_at == "outbound":
                    start_location = route_obj.outbound_destination
                    end_location = route_obj.inbound_destination
                else:  # inbound
                    start_location = route_obj.inbound_destination
                    end_location = route_obj.outbound_destination
            else:
                # fallback if one side missing
                start_location = route_obj.inbound_destination
                end_location = route_obj.inbound_destination


            for i in range(trip_count):
                trip_start = current_start
                trip_end = trip_start + timedelta(minutes=duration)

                trip = Trip(
                    trip_vehicle=vehicle,
                    trip_route=route_obj,
                    trip_route_num=route_obj.route_num,
                    trip_start_location=start_location,
                    trip_end_location=end_location,
                    trip_start_at=trip_start,
                    trip_end_at=trip_end,
                )

                # Determine inbound for generated trips
                trip.trip_inbound = True if start_location == route_obj.inbound_destination else False

                try:
                    trip.full_clean()  # runs model validation, including your 10-year check
                    trip.save()
                except ValidationError as e:
                    for field, errors in e.message_dict.items():
                        for error in errors:
                            if field == "__all__":
                                messages.error(request, error)
                            else:
                                messages.error(request, f"{field}: {error}")
                    return redirect(request.path)
                
                # Prepare for next trip
                current_start = trip_end + timedelta(minutes=break_between)

                # Flip start and end for next loop
                start_location, end_location = end_location, start_location


                current_start = trip_end + timedelta(minutes=break_between)

            messages.success(request, "Mass trips logged successfully.")
            return redirect(request.path)

        # Handle DutyTrip-based logging
                # Handle DutyTrip-based logging
        if duty_id:
            date_str = request.POST.get("duty_date")
        else:
            date_str = request.POST.get("running_board_date")

        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            messages.error(request, "Invalid date selected for duty/running board.")
            return redirect(request.path)

        trip_set = trip_set.order_by('id')

        first_trip = trip_set.first()
        has_trips = trip_set.exists()

        if not has_trips:
            messages.error(request, "Selected duty or running board has no trips defined.")
            return redirect(request.path)

        first_pk = first_trip.id

        first_start_time = first_trip.start_time

        for trip in trip_set:
            # Determine rollover date logic
            trip_date = selected_date
            is_past_midnight = trip.start_time < first_start_time

            if is_past_midnight and trip.id < first_pk:
                trip_date = selected_date + timedelta(days=1)

            start_dt = make_aware(datetime.combine(trip_date, trip.start_time))
            end_dt = make_aware(datetime.combine(trip_date, trip.end_time))

            routeLink = trip.route_link if trip.route_link else None

            board_obj = selected_duty if duty_id else selected_rb

            created_trip = Trip(
                trip_vehicle=vehicle,
                trip_route=routeLink,
                trip_route_num=trip.route_link.route_num if trip.route_link else trip.route,
                trip_start_location=trip.start_at,
                trip_end_location=trip.end_at,
                trip_start_at=start_dt,
                trip_end_at=end_dt,
                trip_board=board_obj,
                trip_inbound=trip.inbound,
            )

            try:
                created_trip.full_clean()
                created_trip.save()
            except ValidationError as e:
                for field, errors in e.message_dict.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
                return redirect(request.path)

        messages.success(request, "Trips from duty or running board logged successfully.")
        return redirect(request.path)

    # Load data for GET
    duties = duty.objects.filter(duty_operator=operator, board_type='duty').order_by('duty_name')
    running_boards = duty.objects.filter(duty_operator=operator, board_type='running-boards').order_by('duty_name')
    vehicles = fleet.objects.filter(Q(operator=operator ) | Q(loan_operator=operator)).order_by('fleet_number_sort')
    routes = route.objects.filter(route_operators=operator).order_by('route_num')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Vehicles', 'url': f'/operator/{operator_slug}/vehicles/'},
        {'name': 'Mass Log Trips', 'url': f'/operator/{operator_slug}/vehicles/mass-log-trips/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'duties': duties,
        'running_boards': running_boards,
        'vehicles': vehicles,
        'routes': routes,
        'current_date': timezone.now().strftime("%Y-%m-%d"),
        'current_date_time': timezone.now().strftime("%Y-%m-%d %H:%M"),
    }
    return render(request, 'mass-log-trips.html', context)

@login_required
@require_http_methods(["POST"])
def mass_assign_single_vehicle_api(request, operator_slug):
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    userPerms = get_helper_permissions(request.user, operator)
    if (
        request.user != operator.owner
        and 'Mass Log Trips' not in userPerms
        and not request.user.is_superuser
    ):
        return JsonResponse({'success': False, 'error': "Permission denied."}, status=403)

    vehicle_id = request.POST.get("vehicle_id")
    board_type = request.POST.get("board_type")
    board_id = request.POST.get("board_id")
    date_str = request.POST.get("date")
    override_existing = request.POST.get("override", "false").lower() == "true"

    if not all([vehicle_id, board_type, board_id, date_str]):
        return JsonResponse({'success': False, 'error': "Missing required fields."}, status=400)

    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({'success': False, 'error': "Invalid date format."}, status=400)

    def event_stream():
        # Send "started" immediately — this resets the upstream 502 timer
        yield f"data: {json.dumps({'type': 'started'})}\n\n"

        try:
            try:
                vehicle = fleet.objects.get(
                    Q(operator=operator) | Q(loan_operator=operator),
                    id=vehicle_id,
                )
            except fleet.DoesNotExist:
                yield f"data: {json.dumps({'type': 'done', 'success': False, 'error': 'Vehicle not found.'})}\n\n"
                return

            try:
                board_obj = duty.objects.get(
                    id=board_id,
                    board_type="duty" if board_type == "duty" else "running-boards",
                    duty_operator=operator
                )
            except duty.DoesNotExist:
                yield f"data: {json.dumps({'type': 'done', 'success': False, 'error': 'Board not found.'})}\n\n"
                return

            trip_set = board_obj.duty_trips.select_related("route_link").order_by("id")

            created_count = 0
            skipped_count = 0
            skipped_details = []
            errors = []
            overwritten_count = 0

            trip_windows = []
            day_offset = timedelta(days=0)  # Track cumulative day offset for multi-trip sequences
            for trip in trip_set:
                start_dt = make_aware(datetime.combine(selected_date, trip.start_time)) + day_offset

                # If end_time <= start_time, the trip crosses midnight to the next day
                if trip.end_time <= trip.start_time:
                    end_dt = make_aware(datetime.combine(selected_date + timedelta(days=1), trip.end_time)) + day_offset
                    # Increment day_offset for subsequent trips in sequence
                    day_offset += timedelta(days=1)
                else:
                    end_dt = make_aware(datetime.combine(selected_date, trip.end_time)) + day_offset

                trip_windows.append((trip, start_dt, end_dt))

            existing_windows = []
            pending_trips = []
            min_start = None
            max_end = None
            if trip_windows:
                min_start = min(w[1] for w in trip_windows)
                max_end = max(w[2] for w in trip_windows)

                if not override_existing:
                    existing_trips = Trip.objects.filter(
                        trip_vehicle=vehicle,
                        trip_start_at__lt=max_end,
                        trip_end_at__gt=min_start,
                    ).only("trip_start_at", "trip_end_at", "trip_route_num")
                    existing_windows = [
                        (t.trip_start_at, t.trip_end_at, t.trip_route_num) for t in existing_trips
                    ]

            for trip, start_dt, end_dt in trip_windows:
                overlapping_trip = None
                for existing_start, existing_end, existing_route_num in existing_windows:
                    if existing_start < end_dt and existing_end > start_dt:
                        overlapping_trip = existing_route_num or "existing trip"
                        break

                if overlapping_trip:
                    skipped_count += 1
                    skipped_details.append(
                        f"{trip.start_time.strftime('%H:%M')}-{trip.end_time.strftime('%H:%M')} "
                        f"(conflicts with {overlapping_trip})"
                    )
                    continue

                created_trip = Trip(
                    trip_vehicle=vehicle,
                    trip_route=trip.route_link,
                    trip_route_num=(
                        trip.route_link.route_num
                        if trip.route_link and hasattr(trip.route_link, "route_num")
                        else trip.route
                    ),
                    trip_inbound=trip.inbound,
                    trip_start_location=trip.start_at,
                    trip_end_location=trip.end_at,
                    trip_start_at=start_dt,
                    trip_end_at=end_dt,
                    trip_board=board_obj,
                )

                pending_trips.append(created_trip)

            if override_existing:
                for created_trip in pending_trips:
                    try:
                        created_trip.full_clean()
                    except ValidationError as e:
                        for field, field_errors in e.message_dict.items():
                            for error in field_errors:
                                errors.append(str(error))

                if errors:
                    yield f"data: {json.dumps({'type': 'done', 'success': False, 'error': '; '.join(errors)})}\n\n"
                    return

                if min_start is not None and max_end is not None:
                    with transaction.atomic():
                        deleted_count, _ = Trip.objects.filter(
                            trip_vehicle=vehicle,
                            trip_start_at__lt=max_end,
                            trip_end_at__gt=min_start,
                        ).delete()
                        overwritten_count = deleted_count

                        for created_trip in pending_trips:
                            created_trip.save()
                            created_count += 1
            else:
                for created_trip in pending_trips:
                    try:
                        created_trip.full_clean()
                        created_trip.save()
                        created_count += 1
                    except ValidationError as e:
                        for field, field_errors in e.message_dict.items():
                            for error in field_errors:
                                errors.append(str(error))

            if errors:
                yield f"data: {json.dumps({'type': 'done', 'success': False, 'error': '; '.join(errors)})}\n\n"
                return

            if skipped_count > 0:
                yield f"data: {json.dumps({'type': 'done', 'success': True, 'message': f'Logged {created_count} trips for {vehicle.fleet_number}. Skipped {skipped_count} due to conflicts.', 'skipped': skipped_details, 'overwritten': overwritten_count})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'done', 'success': True, 'message': f'Logged {created_count} trips for {vehicle.fleet_number}.', 'overwritten': overwritten_count})}\n\n"
        except Exception as e:
            logger.exception("Unexpected error in mass_assign_single_vehicle_api event_stream")
            yield f"data: {json.dumps({'type': 'done', 'success': False, 'error': str(e)})}\n\n"
            return

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # Disables Nginx buffering — critical for SSE
    return response

@login_required
@require_http_methods(["GET"])
def mass_assign_boards(request, operator_slug):
    """
    Render the mass assignment table.
    """
    
    # Feature flag support (if you use it)
    response = feature_enabled(request, "mass_log_trips")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    # Permissions
    userPerms = get_helper_permissions(request.user, operator)
    if (
        request.user != operator.owner
        and 'Mass Log Trips' not in userPerms
        and not request.user.is_superuser
    ):
        messages.error(request, "You do not have permission to log trips for this operator.")
        return redirect(f'/operator/{operator_slug}/')

    # ----------------------------------------------------------------------
    # GET: Load table
    # ----------------------------------------------------------------------
    vehicles = fleet.objects.filter(
        Q(operator=operator) | Q(loan_operator=operator), in_service=True
    ).select_related('vehicle_category', 'vehicleType', 'livery').order_by('fleet_number_sort')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Vehicles', 'url': f'/operator/{operator_slug}/vehicles/'},
        {'name': 'Mass Board Assign', 'url': request.path},
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'vehicles': vehicles,
        'current_date': timezone.now().strftime("%Y-%m-%d"),
    }
    return render(request, 'mass_table_log.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def route_updates_options(request, operator_slug, route_id):
    route_obj = get_object_or_404(route, id=route_id)
    updates = route_obj.service_updates.all()
    return render(request, 'route_updates_options.html', {
        'updates': updates,
        'route': route_obj,
        'operator_slug': operator_slug
    })

@login_required
@require_http_methods(["GET", "POST"])
def route_update_add(request, operator_slug, route_id):
    route_obj = get_object_or_404(route, id=route_id)
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    if request.method == 'POST':
        form = ServiceUpdateForm(request.POST, operator=operator)
        if form.is_valid():
            update = form.save()
            update.effected_route.add(route_obj)
            return redirect('route_updates_options', operator_slug=operator_slug, route_id=route_id)
    else:
        form = ServiceUpdateForm(initial={'effected_route': [route_obj]}, operator=operator)
    return render(request, 'route_updates_form.html', {
        'form': form,
        'route': route_obj,
        'operator_slug': operator_slug,
        'action': 'Add'
    })

@login_required
@require_http_methods(["GET", "POST"])
def route_update_edit(request, operator_slug, route_id, update_id):
    update = get_object_or_404(serviceUpdate, id=update_id)
    route_obj = get_object_or_404(route, id=route_id)
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    if request.method == 'POST':
        form = ServiceUpdateForm(request.POST, instance=update, operator=operator)
        if form.is_valid():
            form.save()
            return redirect('route_updates_options', operator_slug=operator_slug, route_id=route_id)
    else:
        form = ServiceUpdateForm(instance=update, operator=operator)
    return render(request, 'route_updates_form.html', {
        'form': form,
        'route': route_obj,
        'operator_slug': operator_slug,
        'action': 'Edit'
    })

@login_required
@require_http_methods(["GET", "POST"])
def route_update_delete(request, operator_slug, route_id, update_id):
    update = get_object_or_404(serviceUpdate, id=update_id)
    if request.method == 'POST':
        update.delete()
        return redirect('route_updates_options', operator_slug=operator_slug, route_id=route_id)
    return render(request, 'route_updates_delete_confirm.html', {
        'update': update,
        'route_id': route_id,
        'operator_slug': operator_slug
    })

@login_required
@require_http_methods(["GET"])
def boards_api(request, operator_slug):
    """
    API for Select2 to load boards (duties and running boards) for mass assign.
    """
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    # Permissions
    userPerms = get_helper_permissions(request.user, operator)
    if (
        request.user != operator.owner
        and 'Mass Log Trips' not in userPerms
        and not request.user.is_superuser
    ):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    board_type = request.GET.get('type', '').strip()
    search = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    excluded = request.GET.get('excluded', '').strip()

    if board_type == 'running':
        board_type = 'running-boards'

    queryset = duty.objects.filter(
        duty_operator=operator,
    ).select_related('category')

    if board_type:
        queryset = queryset.filter(board_type=board_type)

    if category:
        if category == "none":
            queryset = queryset.filter(category__isnull=True)
        else:
            queryset = queryset.filter(category__id=category)

    if search:
        queryset = queryset.filter(duty_name__icontains=search)

    # Exclude any IDs passed from the client (comma-separated)
    if excluded:
        try:
            ids = [int(x) for x in excluded.split(',') if x.strip().isdigit()]
            if ids:
                queryset = queryset.exclude(id__in=ids)
        except Exception:
            pass

    queryset = queryset.order_by('duty_name')

    results = []
    for board in queryset:
        results.append({
            'id': board.id,
            'text': board.duty_name,
            'category': board.category.name if board.category else 'No Category',
            'type': board.board_type
        })

    return JsonResponse({'results': results})
