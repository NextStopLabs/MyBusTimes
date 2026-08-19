# Python standard library imports
from multiprocessing import context
import calendar
import re
import os
import json
import logging
import random
from mybustimes.http_client import get as http_get, post as http_post
from requests import RequestException
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
from django.core.exceptions import ValidationError, ObjectDoesNotExist
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
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, transaction
from django.db.utils import OperationalError, ProgrammingError, NotSupportedError
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from mybustimes.utils import is_valid_evidence_url

# Django REST Framework imports
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, permissions, viewsets, status
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import IntegerField, Case, When, Value, Count, Min, Max
from django.db.models.functions import Cast

# Project-specific imports
from mybustimes.permissions import ReadOnly, ReadOnly
from .models import *

VEHICLE_TYPE_TEXT_MAX_LENGTH = {
    field.name: field.max_length
    for field in vehicleType._meta.fields
    if isinstance(getattr(field, 'max_length', None), int)
}


def _clamp_vehicle_type_value(field, value):
    """Clamp a proposed vehicle type field value to its model max_length."""
    max_length = VEHICLE_TYPE_TEXT_MAX_LENGTH.get(field)
    if max_length and isinstance(value, str) and len(value) > max_length:
        return value[:max_length]
    return value
from routes.models import *
from .filters import *
from .forms import *
from .serializers import *
from routes.serializers import *
from main.models import featureToggle, update
from main.moderation import is_feature_banned
from tracking.models import BlockVehicleSwap, Tracking, Trip, TripArchive
from gameData.models import *
from words.models import bannedWord
from words.utils import banned_words_in_text

logger = logging.getLogger(__name__)

import requests

DISCORD_FULL_OPERATOR_LOGS_ID = 1432690197228818482
logger = logging.getLogger(__name__)

# Vars

def operator_name_banned_words(operator_name):
    return banned_words_in_text(operator_name, bannedWord.OPERATOR_NAME_SCOPE)


def operator_name_banned_message(blocked_words):
    words = ', '.join(sorted(set(blocked_words)))
    return f"Operator name contains a banned word: {words}."


def reserved_operator_name_message(reservation):
    return f"This operator name ({reservation.operator_name}) is reserved, if you think this is a mistake please open a ticket via discord or on the site"


@login_required
def check_reserved_operator_name(request):
    operator_name = request.GET.get('operator_name', '').strip()
    reservation = reservedOperatorName.blocking_reservation_for_user(operator_name, request.user)
    return JsonResponse({
        'reserved': bool(reservation),
        'message': reserved_operator_name_message(reservation) if reservation else '',
    })
max_for_sale = 25

def get_favourite_vehicle_select_ids(user):
    if not user.is_authenticated:
        return set(), set(), set()

    try:
        favourite_livery_ids = set(
            favouriteLivery.objects.filter(user=user).values_list('livery_id', flat=True)
        )
        favourite_type_ids = set(
            favouriteVehicleType.objects.filter(user=user).values_list('vehicle_type_id', flat=True)
        )
        favourite_operator_ids = set(
            favouriteOperator.objects.filter(user=user).values_list('operator_id', flat=True)
        )
    except (OperationalError, ProgrammingError):
        return set(), set(), set()

    return favourite_livery_ids, favourite_type_ids, favourite_operator_ids

def sort_favourites_first(items, favourite_ids):
    return sorted(
        list(items),
        key=lambda item: (
            0 if item.id in favourite_ids else 1,
            getattr(item, 'name', None) or getattr(item, 'type_name', None) or str(item).lower()
        )
    )

def add_favourite_select_context(context, user, liveries_list=None, types=None):
    favourite_livery_ids, favourite_type_ids, favourite_operator_ids = get_favourite_vehicle_select_ids(user)
    liveries_list = liveries_list if liveries_list is not None else context.get('liveryData', [])
    types = types if types is not None else context.get('typeData', [])

    context.update({
        'liveryData': sort_favourites_first(liveries_list, favourite_livery_ids),
        'typeData': sort_favourites_first(types, favourite_type_ids),
        'favourite_livery_ids': favourite_livery_ids,
        'favourite_type_ids': favourite_type_ids,
        'favourite_operator_ids': favourite_operator_ids,
    })

    for key in ('allowed_operators', 'operatorData'):
        if key in context:
            context[key] = sort_favourites_first(context[key], favourite_operator_ids)

    return context


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
        try:
            response = http_post(
                f"{settings.DISCORD_BOT_API_URL}/send-message-clean",
                data=data,
                files=files,
                timeout=10,
            )
            response.raise_for_status()
        except Exception:
            logger.exception("Failed to send delete notification to Discord")

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
        try:
            response = http_post(
                f"{settings.DISCORD_BOT_API_URL}/send-embed",
                json=data,
                timeout=10,
            )
            response.raise_for_status()
        except Exception:
            logger.exception("Failed to send embed to Discord")

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
        response = http_post(
            f"{settings.DISCORD_BOT_API_URL}/send-embed",
            json=data
        )
        response.raise_for_status()



# API Views
class fleetListView(generics.ListAPIView):
    serializer_class = fleetListSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = fleetsFilter
    permission_classes = [ReadOnly]

    def get_queryset(self):
        return fleet.objects.select_related(
            'operator', 'loan_operator', 'vehicleType', 'livery'
        ).only(
            'id', 'operator_id', 'loan_operator_id', 'vehicleType_id', 'livery_id',
            'in_service', 'for_sale', 'preserved', 'on_load', 'open_top',
            'fleet_number', 'reg', 'type_details',
            'colour', 'branding', 'prev_reg', 'depot', 'name',
            'features', 'notes', 'length', 'last_modified_by',
            'operator__operator_name', 'operator__operator_slug', 'operator__operator_code',
            'loan_operator__operator_name', 'loan_operator__operator_slug', 'loan_operator__operator_code',
            'vehicleType__type_name', 'vehicleType__double_decker', 'vehicleType__type', 'vehicleType__fuel',
            'livery__name', 'livery__colour', 'livery__left_css', 'livery__right_css',
            'livery__text_colour', 'livery__stroke_colour',
        )

class fleetDetailView(generics.RetrieveAPIView):
    queryset = fleet.objects.select_related(
        'operator', 'loan_operator', 'vehicleType', 'livery', 'vehicle_category',
    )
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

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if self.request.user.is_authenticated:
            try:
                ctx['_favourite_ids'] = set(
                    favouriteOperator.objects.filter(user=self.request.user)
                    .values_list('operator_id', flat=True)
                )
            except (OperationalError, ProgrammingError):
                ctx['_favourite_ids'] = set()
            try:
                ctx['_helper_ids'] = set(
                    helper.objects.filter(helper=self.request.user)
                    .values_list('operator_id', flat=True)
                )
            except (OperationalError, ProgrammingError):
                ctx['_helper_ids'] = set()
        return ctx

    def get_queryset(self):
        favourite_ids = []
        if self.request.user.is_authenticated:
            try:
                favourite_ids = list(
                    favouriteOperator.objects.filter(
                        user=self.request.user
                    ).values_list('operator_id', flat=True)
                )
            except (OperationalError, ProgrammingError):
                favourite_ids = []

        ordering = [
            Case(
                When(id__in=favourite_ids, then=Value(0)),
                default=Value(1),
                output_field=IntegerField()
            ),
            'operator_name'
        ]

        # Use minimal query when minimal serializer is requested
        if self.request.query_params.get('minimal', '').lower() == 'true':
            return MBTOperator.objects.only('id', 'operator_name', 'operator_slug', 'operator_code').order_by(*ordering)
        
        # Full queryset with prefetching for the full serializer
        return MBTOperator.objects.prefetch_related('region').select_related('owner', 'group', 'organisation').order_by(*ordering)

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

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if self.request.user.is_authenticated:
            try:
                ctx['_favourite_ids'] = set(
                    favouriteLivery.objects.filter(user=self.request.user)
                    .values_list('livery_id', flat=True)
                )
            except (OperationalError, ProgrammingError):
                ctx['_favourite_ids'] = set()
        return ctx

    def get_queryset(self):
        queryset = liverie.objects.filter(published=True, declined=False)
        if self.request.user.is_authenticated:
            try:
                favourite_ids = list(
                    favouriteLivery.objects.filter(
                        user=self.request.user
                    ).values_list('livery_id', flat=True)
                )
            except (OperationalError, ProgrammingError):
                favourite_ids = []
            return queryset.order_by(
                Case(
                    When(id__in=favourite_ids, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField()
                ),
                'name'
            )
        return queryset.order_by('name')

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

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if self.request.user.is_authenticated:
            try:
                ctx['_favourite_ids'] = set(
                    favouriteVehicleType.objects.filter(user=self.request.user)
                    .values_list('vehicle_type_id', flat=True)
                )
            except (OperationalError, ProgrammingError):
                ctx['_favourite_ids'] = set()
        return ctx

    def get_queryset(self):
        queryset = vehicleType.objects.filter(active=True, hidden=False)
        if self.request.user.is_authenticated:
            try:
                favourite_ids = list(
                    favouriteVehicleType.objects.filter(
                        user=self.request.user
                    ).values_list('vehicle_type_id', flat=True)
                )
            except (OperationalError, ProgrammingError):
                favourite_ids = []
            return queryset.order_by(
                Case(
                    When(id__in=favourite_ids, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField()
                ),
                Case(
                    When(type='Bus', then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField()
                ),
                'type',
                'type_name'
            )
        return queryset.order_by(
            Case(
                When(type='Bus', then=Value(0)),
                default=Value(1),
                output_field=IntegerField()
            ),
            'type',
            'type_name'
        )

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

        # Get helper instance with prefetched perms to avoid N+1
        helper_instance = helper.objects.prefetch_related('perms').filter(helper=user, operator=operator).first()
        if helper_instance:
            return [perm.perm_name for perm in helper_instance.perms.all()]
        return []

    except Exception as e:
        print(f"Error getting helper permissions: {e}")
        return []

@login_required
@require_POST
def toggle_favourite_vehicle_select_item(request):
    favourite_type = request.POST.get('type')
    item_id = request.POST.get('id')

    if not item_id or not str(item_id).isdigit():
        return JsonResponse({'success': False, 'error': 'Missing selected item.'}, status=400)

    if favourite_type == 'livery':
        selected_item = get_object_or_404(liverie, id=item_id)
        try:
            favourite, created = favouriteLivery.objects.get_or_create(
                user=request.user,
                livery=selected_item
            )
        except (OperationalError, ProgrammingError):
            return JsonResponse({'success': False, 'error': 'Favourite tables have not been migrated yet.'}, status=503)
    elif favourite_type == 'vehicle_type':
        selected_item = get_object_or_404(vehicleType, id=item_id)
        try:
            favourite, created = favouriteVehicleType.objects.get_or_create(
                user=request.user,
                vehicle_type=selected_item
            )
        except (OperationalError, ProgrammingError):
            return JsonResponse({'success': False, 'error': 'Favourite tables have not been migrated yet.'}, status=503)
    elif favourite_type == 'operator':
        selected_item = get_object_or_404(MBTOperator, id=item_id)
        try:
            favourite, created = favouriteOperator.objects.get_or_create(
                user=request.user,
                operator=selected_item
            )
        except (OperationalError, ProgrammingError):
            return JsonResponse({'success': False, 'error': 'Favourite tables have not been migrated yet.'}, status=503)
    else:
        return JsonResponse({'success': False, 'error': 'Unknown favourite type.'}, status=400)

    if not created:
        favourite.delete()

    return JsonResponse({
        'success': True,
        'favourited': created,
    })


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
        tabs.append({"name": "Blocks", "url": f"/operator/{operator.operator_slug}/blocks/", "active": active == "blocks"})

    if ticket_count > 0:
        tab_name = f"{ticket_count} tickets" if active == "tickets" else "Tickets"
        tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_slug}/tickets/", "active": active == "tickets"})

    if update_count > 0:
        tab_name = f"{update_count} updates" if active == "updates" else "Updates"
        tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_slug}/updates/", "active": active == "updates"})

    return tabs

def feature_enabled(request, feature_name):
    feature_key = feature_name.lower().replace('_', ' ')

    cache_key = f'feature_toggle_state:{feature_name}'
    feature_state = cache.get(cache_key)
    if feature_state is None:
        feature_state = featureToggle.objects.filter(name=feature_name).values(
            'enabled',
            'maintenance',
            'super_user_only',
        ).first()
        cache.set(cache_key, feature_state, 60)

    if feature_state:
        if feature_state['enabled']:
            # Feature is enabled, so just return None to let the view continue
            return None

        if feature_state['maintenance']:
            if not request.user.is_superuser:
                return render(request, 'feature_maintenance.html', {'feature_name': feature_key}, status=200)
            else:
                return None

        if feature_state['super_user_only'] and not request.user.is_superuser:
            return render(request, 'feature_disabled.html', {'feature_name': feature_key}, status=403)

        # Feature is disabled in other ways
        return render(request, 'feature_disabled.html', {'feature_name': feature_key}, status=200)

    # If feature doesn't exist, block it.
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
    # OPTIMIZATION: Fetch routes with manual prefetch of linked routes
    # ========================================
    route_query = route.objects.filter(route_operators=operator)
    
    if not show_hidden:
        route_query = route_query.filter(hidden=False)
    
    # Fetch initial routes (ordered)
    routes = list(route_query.order_by('route_num'))
    
    if routes:
        route_ids = [r.id for r in routes]
        
        # OPTIMIZATION: Fetch link pairs (just IDs) instead of JOIN + full object queries
        linked_through = route.linked_route.through
        
        # Get all first-level link pairs for initial routes
        link_pairs = list(linked_through.objects.filter(
            from_route_id__in=route_ids
        ).values_list('from_route_id', 'to_route_id'))
        
        # Build link map from initial routes
        link_map = defaultdict(list)
        linked_ids = set()
        for from_id, to_id in link_pairs:
            link_map[from_id].append(to_id)
            linked_ids.add(to_id)
        
        if linked_ids:
            # Get second-level link pairs for linked routes (needed for graph traversal)
            linked_route_ids = list(linked_ids - set(route_ids))
            if linked_route_ids:
                link_pairs_2 = list(linked_through.objects.filter(
                    from_route_id__in=linked_route_ids
                ).values_list('from_route_id', 'to_route_id'))
                for from_id, to_id in link_pairs_2:
                    link_map[from_id].append(to_id)
            
            # Fetch all needed routes in a single query by PK
            all_ids = set(route_ids) | linked_ids
            all_routes = route.objects.filter(id__in=all_ids)
            route_map = {r.id: r for r in all_routes}
            
            # Manually populate prefetch cache for zero-DB graph traversal
            for rid, linked_route_ids_list in link_map.items():
                if rid in route_map:
                    linked_objs = [
                        route_map[lid] for lid in linked_route_ids_list
                        if lid in route_map
                    ]
                    route_map[rid]._prefetched_objects_cache = {
                        'linked_route': linked_objs
                    }
            
            # Reconstruct routes list preserving original order
            routes = [route_map[rid] for rid in route_ids]
    
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
    route_instance = get_object_or_404(
        route.objects.prefetch_related('linked_route'),
        id=route_id
    )
    linked_routes = sorted(
        [route_instance, *list(route_instance.linked_route.all())],
        key=parse_route_key,
    )
    linked_route_ids = [linked_route.id for linked_route in linked_routes]
    
    # ========================================
    # CRITICAL: Fetch ALL trips with FULL prefetching
    # ========================================
    vehicles = list(
        Trip.objects
        .filter(
            trip_route__id__in=linked_route_ids,
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
        .distinct()
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
        'linked_routes': linked_routes,
        'has_linked_routes': len(linked_routes) > 1,
        'show_board': show_board,
        'breadcrumbs': breadcrumbs,
        'date': date,
        'now': timezone.now()
    }
    
    return render(request, 'route_vehicles.html', context)


MAX_BLOCK_SWAPS_PER_DAY = 2


def _swap_block_vehicle(board_obj, replacement_vehicle, selected_date, swap_from_trip_id, user=None):
    if selected_date != timezone.localdate():
        raise ValidationError({"__all__": ["Vehicle swaps can only be made for today's date."]})

    if BlockVehicleSwap.objects.filter(board_id=board_obj.id, service_date=selected_date).count() >= MAX_BLOCK_SWAPS_PER_DAY:
        raise ValidationError({"__all__": ["This running board has already been swapped twice today."]})

    swap_from_trip = Trip.objects.filter(
        trip_id=swap_from_trip_id,
        trip_board=board_obj,
        trip_start_at__date=selected_date,
        trip_missed=False,
    ).first()
    if not swap_from_trip:
        raise ValidationError({"__all__": ["Choose a valid trip to swap from."]})

    vehicle_busy = Trip.objects.filter(
        trip_vehicle=replacement_vehicle,
        trip_start_at__date=selected_date,
        trip_missed=False,
    ).exists()
    if vehicle_busy:
        raise ValidationError({"__all__": ["That vehicle already has trips logged for this date."]})

    source_trips = Trip.objects.filter(
        trip_board=board_obj,
        trip_start_at__date=selected_date,
        trip_missed=False,
    )
    if not source_trips.exists():
        raise ValidationError({"__all__": ["There are no active trips to swap for this running board."]})

    remaining_trips = list(
        source_trips
        .filter(trip_start_at__gte=swap_from_trip.trip_start_at)
        .select_related("trip_route")
        .order_by("trip_start_at", "trip_id")
    )
    if not remaining_trips:
        raise ValidationError({"__all__": ["There are no remaining trips to generate for this block."]})

    with transaction.atomic():
        if BlockVehicleSwap.objects.select_for_update().filter(board_id=board_obj.id, service_date=selected_date).count() >= MAX_BLOCK_SWAPS_PER_DAY:
            raise ValidationError({"__all__": ["This running board has already been swapped twice today."]})

        missed_count = Trip.objects.filter(
            trip_id__in=[trip.trip_id for trip in remaining_trips]
        ).update(trip_missed=True)
        created_count = 0
        for source_trip in remaining_trips:
            created_trip = Trip(
                trip_vehicle=replacement_vehicle,
                trip_route=source_trip.trip_route,
                trip_route_num=source_trip.trip_route_num,
                trip_display_id=source_trip.trip_display_id,
                trip_driver=source_trip.trip_driver,
                trip_start_location=source_trip.trip_start_location,
                trip_end_location=source_trip.trip_end_location,
                trip_start_at=source_trip.trip_start_at,
                trip_end_at=source_trip.trip_end_at,
                trip_board=board_obj,
                trip_inbound=source_trip.trip_inbound,
            )
            created_trip.full_clean()
            created_trip.save()
            created_count += 1
        BlockVehicleSwap.objects.create(
            board_id=board_obj.id,
            service_date=selected_date,
            swap_from_trip_id=swap_from_trip.trip_id,
            from_vehicle_id=swap_from_trip.trip_vehicle_id,
            to_vehicle_id=replacement_vehicle.id,
            created_by_id=user.id if getattr(user, "is_authenticated", False) else None,
        )

    return missed_count, created_count


def _add_validation_messages(request, exc):
    if hasattr(exc, "message_dict"):
        for field, errors in exc.message_dict.items():
            for error in errors:
                messages.error(request, error if field == "__all__" else f"{field}: {error}")
    else:
        for error in exc.messages:
            messages.error(request, error)


def blocks(request, operator_slug):
    response = feature_enabled(request, "view_trips")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    helper_permissions = get_helper_permissions(request.user, operator)

    selected_date = parse_date(request.GET.get("date") or "")
    if selected_date is None:
        selected_date = timezone.localdate()

    trip_groups = list(
        Trip.objects
        .filter(
            trip_board__board_type="running-boards",
            trip_board__duty_operator=operator,
            trip_start_at__date=selected_date,
            trip_missed=False,
        )
        .values(
            "trip_board_id",
            "trip_board__duty_name",
            "trip_vehicle_id",
            "trip_vehicle__fleet_number",
            "trip_vehicle__reg",
            "trip_vehicle__operator__operator_slug",
        )
        .annotate(
            trip_count=Count("trip_id"),
            first_start=Min("trip_start_at"),
            last_end=Max("trip_end_at"),
        )
        .order_by("trip_board__duty_name", "trip_vehicle__fleet_number")
    )

    block_map = OrderedDict()
    for trip_group in trip_groups:
        board_id = trip_group["trip_board_id"]
        if not board_id:
            continue

        block = block_map.setdefault(board_id, {
            "board_id": board_id,
            "board_name": trip_group["trip_board__duty_name"],
            "vehicles": OrderedDict(),
            "trip_count": 0,
            "first_start": trip_group["first_start"],
            "last_end": trip_group["last_end"],
        })
        block["trip_count"] += trip_group["trip_count"]
        if trip_group["first_start"] and (block["first_start"] is None or trip_group["first_start"] < block["first_start"]):
            block["first_start"] = trip_group["first_start"]
        if trip_group["last_end"] and (block["last_end"] is None or trip_group["last_end"] > block["last_end"]):
            block["last_end"] = trip_group["last_end"]

        vehicle_id = trip_group["trip_vehicle_id"]
        if vehicle_id:
            block["vehicles"][vehicle_id] = {
                "id": vehicle_id,
                "fleet_number": trip_group["trip_vehicle__fleet_number"],
                "reg": trip_group["trip_vehicle__reg"],
                "operator_slug": trip_group["trip_vehicle__operator__operator_slug"],
            }

    block_rows = list(block_map.values())
    for block in block_rows:
        block["vehicles"] = list(block["vehicles"].values())
        block["block_url"] = f"/operator/{operator.operator_slug}/blocks/{block['board_id']}/?date={selected_date.isoformat()}"
        block["board_url"] = f"/operator/{operator.operator_slug}/running-boards/{block['board_id']}/"

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Blocks', 'url': f'/operator/{operator_slug}/blocks/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'blocks': block_rows,
        'selected_date': selected_date,
        'tabs': generate_tabs("blocks", operator, helper_permissions=helper_permissions),
    }

    return render(request, 'blocks.html', context)


def block_detail(request, operator_slug, board_id, vehicle_id=None):
    response = feature_enabled(request, "view_trips")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    helper_permissions = get_helper_permissions(request.user, operator)
    selected_date = parse_date(request.POST.get("date") or request.GET.get("date") or "")
    if selected_date is None:
        selected_date = timezone.localdate()

    board_obj = get_object_or_404(
        duty,
        id=board_id,
        duty_operator=operator,
        board_type="running-boards",
    )
    can_swap_blocks = _can_mass_log_for_operator(request.user, operator)
    swap_count = BlockVehicleSwap.objects.filter(board_id=board_obj.id, service_date=selected_date).count()
    swaps_remaining = max(0, MAX_BLOCK_SWAPS_PER_DAY - swap_count)
    can_swap_selected_date = can_swap_blocks and selected_date == timezone.localdate() and swaps_remaining > 0

    if request.method == "POST":
        if not can_swap_blocks:
            messages.error(request, "You do not have permission to swap blocks for this operator.")
            return redirect(f"{request.path}?date={selected_date.isoformat()}")
        if selected_date != timezone.localdate():
            messages.error(request, "Vehicle swaps can only be made for today's date.")
            return redirect(f"{request.path}?date={selected_date.isoformat()}")

        vehicle_id = request.POST.get("vehicle_id")
        replacement_vehicle = get_object_or_404(
            fleet,
            Q(operator=operator) | Q(loan_operator=operator),
            id=vehicle_id,
            in_service=True,
        )

        try:
            missed_count, created_count = _swap_block_vehicle(
                board_obj,
                replacement_vehicle,
                selected_date,
                request.POST.get("swap_from_trip_id"),
                request.user,
            )
        except ValidationError as exc:
            _add_validation_messages(request, exc)
            return redirect(f"{request.path}?date={selected_date.isoformat()}")

        messages.success(
            request,
            f"Block swapped to {replacement_vehicle.fleet_number}. {missed_count} original trip(s) marked missed and {created_count} remaining trip(s) created.",
        )
        return redirect(f"{request.path}?date={selected_date.isoformat()}")

    trip_filters = {
        "trip_board": board_obj,
        "trip_start_at__date": selected_date,
        "trip_missed": False,
    }
    if vehicle_id:
        trip_filters["trip_vehicle_id"] = vehicle_id

    trips = list(
        Trip.objects
        .filter(**trip_filters)
        .select_related("trip_route", "trip_vehicle", "trip_vehicle__operator")
        .order_by("trip_start_at")
    )
    vehicle = trips[0].trip_vehicle if vehicle_id and trips else None
    available_swap_vehicles = []
    available_swap_trips = []
    default_swap_trip_id = None
    if can_swap_selected_date:
        busy_vehicle_ids = Trip.objects.filter(
            trip_start_at__date=selected_date,
            trip_missed=False,
        ).values_list("trip_vehicle_id", flat=True)
        available_swap_vehicles = list(
            fleet.objects
            .filter(Q(operator=operator) | Q(loan_operator=operator), in_service=True)
            .exclude(id__in=busy_vehicle_ids)
            .order_by("fleet_number_sort", "fleet_number")
        )
        available_swap_trips = trips
        now_dt = timezone.now()
        default_swap_trip = next(
            (trip for trip in available_swap_trips if trip.trip_start_at and trip.trip_start_at >= now_dt),
            None,
        )
        if default_swap_trip:
            default_swap_trip_id = default_swap_trip.trip_id

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': 'Blocks', 'url': f'/operator/{operator_slug}/blocks/?date={selected_date.isoformat()}'},
        {'name': board_obj.duty_name, 'url': f'/operator/{operator_slug}/blocks/{board_id}/?date={selected_date.isoformat()}'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'board': board_obj,
        'vehicle': vehicle,
        'trips': trips,
        'available_swap_vehicles': available_swap_vehicles,
        'available_swap_trips': available_swap_trips,
        'default_swap_trip_id': default_swap_trip_id,
        'can_swap_blocks': can_swap_selected_date,
        'swap_count': swap_count,
        'swaps_remaining': swaps_remaining,
        'max_block_swaps_per_day': MAX_BLOCK_SWAPS_PER_DAY,
        'now': timezone.now(),
        'selected_date': selected_date,
        'tabs': generate_tabs("blocks", operator, helper_permissions=helper_permissions),
    }

    return render(request, 'block_detail.html', context)


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
    """Extract and parse timetable data with per-entry caching."""
    if not timetable_entry:
        return {}
    
    cached = getattr(timetable_entry, '_cached_raw_stop_times', None)
    if cached is not None:
        return cached
    
    try:
        raw_stop_times = timetable_entry.stop_times
        result = json.loads(raw_stop_times) if raw_stop_times else {}
        timetable_entry._cached_raw_stop_times = result
        return result
    except json.JSONDecodeError:
        timetable_entry._cached_raw_stop_times = {}
        return {}


def normalize_timetable_time_value(value):
    if value is None:
        return ""

    value = str(value).strip()
    if not value:
        return ""

    match = re.search(r'(\d{1,2}):(\d{2})', value)
    if not match:
        return ""

    hour = int(match.group(1)) % 24
    minute = int(match.group(2))
    if minute > 59:
        return ""

    return f"{hour:02d}:{minute:02d}"


def normalize_timetable_time_list(values):
    if not isinstance(values, list):
        return []
    return [normalize_timetable_time_value(value) for value in values]


def timetable_minutes_since_midnight(value):
    value = normalize_timetable_time_value(value)
    if not value:
        return None
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def timetable_day_offsets(times):
    offsets = []
    day_offset = 0
    previous_minutes = None

    for value in times:
        minutes = timetable_minutes_since_midnight(value)
        if minutes is not None and previous_minutes is not None and minutes < previous_minutes:
            day_offset += 1

        offsets.append(day_offset)

        if minutes is not None:
            previous_minutes = minutes

    return offsets


def format_timetable_time_with_day(value, day_offset):
    value = normalize_timetable_time_value(value)
    if not value:
        return ""
    return value


def build_time_pairs(stop_data):
    departures = normalize_timetable_time_list(stop_data.get("departure_times") or stop_data.get("times") or [])
    arrivals = normalize_timetable_time_list(stop_data.get("arrival_times") or departures)
    max_len = max(len(arrivals), len(departures))
    departure_offsets = timetable_day_offsets(departures)
    arrival_offsets = timetable_day_offsets(arrivals)

    pairs = []
    for index in range(max_len):
        arrival = arrivals[index] if index < len(arrivals) else ""
        departure = departures[index] if index < len(departures) else ""
        departure_offset = departure_offsets[index] if index < len(departure_offsets) else 0
        arrival_offset = arrival_offsets[index] if index < len(arrival_offsets) else departure_offset
        arrival_display = format_timetable_time_with_day(arrival, arrival_offset)
        departure_display = format_timetable_time_with_day(departure, departure_offset)
        pairs.append({
            "arrival": arrival_display,
            "departure": departure_display,
            "arrival_day_offset": arrival_offset if arrival_display else 0,
            "departure_day_offset": departure_offset if departure_display else 0,
            "display_day_offset": departure_offset if departure_display else 0,
            "display": departure_display if not arrival_display or arrival_display == departure_display else f"{arrival_display} / {departure_display}",
            "has_arrival_departure": bool(arrival and departure and arrival != departure),
        })

    return pairs


def normalize_timetable_stop_times(stop_times):
    if not isinstance(stop_times, dict):
        return {}

    for stop_data in stop_times.values():
        departures = normalize_timetable_time_list(stop_data.get("departure_times") or stop_data.get("times") or [])
        arrivals = normalize_timetable_time_list(stop_data.get("arrival_times") or departures)
        stop_data["times"] = departures
        stop_data["departure_times"] = departures
        stop_data["arrival_times"] = arrivals
        stop_data["time_pairs"] = build_time_pairs(stop_data)

    return stop_times


def get_cached_normalized_stop_times(entry):
    """Return normalized stop times for a timetable entry, using per-entry cache."""
    if not entry:
        return {}
    cached = getattr(entry, '_cached_normalized', None)
    if cached is not None:
        return cached
    raw = process_timetable_data(entry)
    result = normalize_timetable_stop_times(raw)
    entry._cached_normalized = result
    return result


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
    day_names = getattr(entry, '_day_names', None)
    if day_names is not None:
        return service_day in day_names
    return any(day.name == service_day for day in entry.day_type.all())


def format_service_date(service_date):
    return f"{service_date.strftime('%A')} {service_date.day} {service_date.strftime('%B %Y')}"


def build_route_timetable_context(route_instance, timetable_entries, route_stops, current_date, operators_cache):
    inbound_entries = [e for e in timetable_entries if e.route_id == route_instance.id and e.inbound]
    outbound_entries = [e for e in timetable_entries if e.route_id == route_instance.id and not e.inbound]

    inbound_timetable = get_valid_timetable_entry(inbound_entries, current_date)
    inbound_timetableData = get_cached_normalized_stop_times(inbound_timetable)
    inbound_groupedSchedule = build_grouped_schedule(inbound_entries, operators_cache)

    outbound_timetable = get_valid_timetable_entry(outbound_entries, current_date)
    outbound_timetableData = get_cached_normalized_stop_times(outbound_timetable)
    outbound_groupedSchedule = build_grouped_schedule(outbound_entries, operators_cache)

    return {
        'route': route_instance,
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
        'route_stops_full': {
            'inbound': route_stops.get((route_instance.id, True)),
            'outbound': route_stops.get((route_instance.id, False)),
        },
    }


def build_combined_linked_timetable(routes_for_group, timetable_entries, direction):
    direction_entries = [
        entry for entry in timetable_entries
        if entry.inbound == direction and entry.route_id in {r.id for r in routes_for_group}
    ]

    stop_rows = OrderedDict()
    stop_order_edges = defaultdict(set)
    trips = []

    def stop_order_would_cycle(source_key, target_key):
        if source_key == target_key:
            return False

        to_visit = list(stop_order_edges[target_key])
        visited = set()
        while to_visit:
            current_key = to_visit.pop()
            if current_key == source_key:
                return True
            if current_key in visited:
                continue
            visited.add(current_key)
            to_visit.extend(stop_order_edges[current_key])

        return False

    for entry in direction_entries:
        stop_times = get_cached_normalized_stop_times(entry)
        if not stop_times:
            continue

        stop_items = list(stop_times.items())
        if not stop_items:
            continue

        first_stop_data = stop_items[0][1]
        trip_count = len(first_stop_data.get("time_pairs") or [])

        stop_row_keys = []
        previous_row_key = None
        for stop_key, stop_data in stop_items:
            stop_name = stop_data.get("stopname") or stop_key
            base_row_key = re.sub(r'\s+', ' ', str(stop_name)).strip().casefold()
            row_key = base_row_key
            if (
                previous_row_key
                and row_key in stop_rows
                and stop_order_would_cycle(previous_row_key, row_key)
            ):
                variant_index = 2
                row_key = f"{base_row_key}::{entry.route_id}:{variant_index}"
                while row_key in stop_rows:
                    variant_index += 1
                    row_key = f"{base_row_key}::{entry.route_id}:{variant_index}"

            stop_row_keys.append((row_key, stop_data))
            if row_key not in stop_rows:
                stop_rows[row_key] = {
                    "stopname": stop_name,
                    "timing_point": stop_data.get("timing_point", True),
                    "cells": [],
                    "order": len(stop_rows),
                }
            elif stop_data.get("timing_point", True):
                stop_rows[row_key]["timing_point"] = True

            if previous_row_key and previous_row_key != row_key:
                stop_order_edges[previous_row_key].add(row_key)
            previous_row_key = row_key

        for trip_index in range(trip_count):
            first_pair = first_stop_data.get("time_pairs", [])[trip_index]
            trip_stop_times = {}
            for row_key, stop_data in stop_row_keys:
                time_pairs = stop_data.get("time_pairs") or []
                if trip_index < len(time_pairs) and row_key not in trip_stop_times:
                    trip_stop_times[row_key] = time_pairs[trip_index]

            trips.append({
                "route_id": entry.route_id,
                "route_num": entry.route.route_num or str(entry.route_id),
                "sort_minutes": timetable_minutes_since_midnight(first_pair.get("departure") or first_pair.get("display")) or 0,
                "stop_times": trip_stop_times,
            })

    trips.sort(key=lambda trip: (trip["sort_minutes"], trip["route_num"]))

    for stop_key, stop_row in stop_rows.items():
        cells = []
        for trip in trips:
            cell = dict(trip["stop_times"].get(stop_key, {
                "arrival": "",
                "departure": "",
                "arrival_day_offset": 0,
                "departure_day_offset": 0,
                "display": "",
                "display_day_offset": 0,
                "has_arrival_departure": False,
            }))
            cell["route_num"] = trip["route_num"]
            cells.append(cell)
        stop_row["cells"] = cells

    outgoing = stop_order_edges
    incoming_counts = {stop_key: 0 for stop_key in stop_rows}
    for source_key, target_keys in outgoing.items():
        for target_key in target_keys:
            incoming_counts[target_key] += 1

    available = sorted(
        [stop_key for stop_key, count in incoming_counts.items() if count == 0],
        key=lambda stop_key: stop_rows[stop_key]["order"],
    )
    ordered_stop_keys = []
    while available:
        stop_key = available.pop(0)
        ordered_stop_keys.append(stop_key)
        for next_key in sorted(outgoing[stop_key], key=lambda key: stop_rows[key]["order"]):
            incoming_counts[next_key] -= 1
            if incoming_counts[next_key] == 0:
                available.append(next_key)
        available.sort(key=lambda key: stop_rows[key]["order"])

    if len(ordered_stop_keys) < len(stop_rows):
        ordered_stop_keys.extend(
            sorted(
                [stop_key for stop_key in stop_rows if stop_key not in ordered_stop_keys],
                key=lambda stop_key: stop_rows[stop_key]["order"],
            )
        )

    return {
        "has_trips": bool(trips),
        "route_numbers": [trip["route_num"] for trip in trips],
        "stops": [(stop_key, stop_rows[stop_key]) for stop_key in ordered_stop_keys],
    }


def route_detail(request, operator_slug, route_id):
    """
    Route detail view - OPTIMIZED with precomputed caches.
    """
    response = feature_enabled(request, "view_routes")
    if response:
        return response
    
    current_date = timezone.now().date()
    max_service_date = add_one_month(current_date)
    
    # ========================================
    # FETCH ALL DATA IN MINIMAL QUERIES
    # ========================================
    
    # Query 1: Get operator
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    
    # Query 2: Deep prefetching - also prefetch route_operators on linked/related routes for template N+1
    route_instance = get_object_or_404(
        route.objects.prefetch_related(
            'route_operators',
            Prefetch(
                'service_updates',
                queryset=serviceUpdate.objects.prefetch_related(
                    Prefetch('effected_route', queryset=route.objects.prefetch_related('route_operators'))
                )
            ),
            Prefetch(
                'related_route',
                queryset=route.objects.prefetch_related('route_operators')
            ),
            Prefetch(
                'linked_route',
                queryset=route.objects.prefetch_related('route_operators', 'service_updates')
            )
        ),
        id=route_id
    )
    
    linked_routes = sorted(
        [route_instance, *list(route_instance.linked_route.all())],
        key=parse_route_key,
    )
    linked_route_ids = [linked_route.id for linked_route in linked_routes]
    
    linked_route_options = []
    linked_destination_lines = []
    seen_destinations = set()
    for linked_route in linked_routes:
        destination_parts = [
            linked_route.inbound_destination,
            *(linked_route.other_destination or []),
            linked_route.outbound_destination,
        ]
        destination_label = " - ".join(part for part in destination_parts if part).strip()
        if destination_label and destination_label not in seen_destinations:
            seen_destinations.add(destination_label)
            linked_destination_lines.append(destination_label)
        linked_route_options.append({
            "id": linked_route.id,
            "route_num": linked_route.route_num,
            "label": f"{linked_route.route_num} - {destination_label}" if destination_label else linked_route.route_num,
        })
    
    # Query 3: Get transit authority
    details = operator.operator_details or {}
    transit_authority = details.get('transit_authority') or details.get('transit_authorities')
    
    transit_authority_details_obj = None
    if transit_authority:
        first_authority_code = transit_authority.split(",")[0].strip()
        transit_authority_details_obj = (
            transitAuthoritiesColour.objects
            .filter(authority_code=first_authority_code)
            .first()
        )
    
    # Process colors
    route_instance.colours, school_service = get_route_colours(
        route_instance, 
        transit_authority_details_obj
    )
    
    # Query 4: Get ALL route stops at once (only non-waypoint)
    route_stops = list(routeStop.objects.filter(route_id__in=linked_route_ids))
    route_stops_by_route_direction = {}
    for route_stop in route_stops:
        if route_stop.stops:
            route_stop.stops = [
                s for s in route_stop.stops
                if not s.get('waypoint', False)
            ]
        route_stops_by_route_direction[(route_stop.route_id, route_stop.inbound)] = route_stop

    route_stop_full_inbound = route_stops_by_route_direction.get((route_instance.id, True))
    route_stop_full_outbound = route_stops_by_route_direction.get((route_instance.id, False))
    
    # Query 5: Get all day types
    days = list(dayType.objects.all())

    # Query 6: Get all timetable entries with prefetched day_types
    all_timetable_entries = list(
        timetableEntry.objects
        .filter(route_id__in=linked_route_ids)
        .filter(
            Q(end_date__gte=current_date) | Q(end_date__isnull=True),
            Q(start_date__lte=max_service_date) | Q(start_date__isnull=True)
        )
        .select_related('route')
        .prefetch_related('day_type')
    )

    # ========================================
    # PRECOMPUTE DAY NAMES ON EACH ENTRY (avoids day_type.all() in hot loops)
    # ========================================
    for entry in all_timetable_entries:
        prefetched_days = entry._prefetched_objects_cache.get('day_type', [])
        entry._day_names = {dt.name for dt in prefetched_days}

    # ========================================
    # BUILD SIGNATURE MAP FOR DEDUPLICATION
    # ========================================
    rule_exemplars = {}
    entry_to_rule_key = {}
    
    for entry in all_timetable_entries:
        dt_ids = tuple(sorted(dt.id for dt in entry._prefetched_objects_cache.get('day_type', [])))
        signature = (
            dt_ids,
            entry.start_date,
            entry.end_date,
            entry.calendar_id if hasattr(entry, 'calendar_id') else None,
            entry.service_id if hasattr(entry, 'service_id') else None,
        )
        entry_to_rule_key[entry.id] = signature
        if signature not in rule_exemplars:
            rule_exemplars[signature] = entry

    # ========================================
    # HIGH-SPEED 30-DAY LOOKAHEAD (uses _day_names, no DB hits)
    # ========================================
    available_dates = []
    service_date = current_date
    while service_date <= max_service_date:
        if any(timetable_entry_runs_on(exemplar, service_date) for exemplar in rule_exemplars.values()):
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

    # ========================================
    # FILTER ENTRIES FOR SELECTED DATE (no redundant timetable_entry_runs_on calls for non-exemplars)
    # ========================================
    active_signatures = {
        sig for sig, exemplar in rule_exemplars.items()
        if timetable_entry_runs_on(exemplar, selected_service_date)
    }
    
    selected_timetable_entries = [
        entry for entry in all_timetable_entries
        if entry_to_rule_key[entry.id] in active_signatures
    ]
    
    selected_current_route_entries = [
        entry for entry in selected_timetable_entries
        if entry.route_id == route_instance.id
    ]
    
    inbound_entries = [e for e in selected_current_route_entries if e.inbound]
    outbound_entries = [e for e in selected_current_route_entries if not e.inbound]
    
    # ========================================
    # PRE-FETCH OPERATORS FOR SCHEDULES
    # ========================================
    all_operator_codes = set()
    for entry in selected_timetable_entries:
        if entry.operator_schedule:
            all_operator_codes.update(entry.operator_schedule)
    
    operators_cache = {}
    if all_operator_codes:
        operators_cache = {
            op.operator_code: op.operator_name 
            for op in MBTOperator.objects.filter(operator_code__in=all_operator_codes)
        }
    
    # ========================================
    # PROCESS TIMETABLES (uses per-entry caches, no redundant JSON parses)
    # ========================================
    inbound_timetable = get_valid_timetable_entry(inbound_entries, current_date)
    inbound_timetableData = get_cached_normalized_stop_times(inbound_timetable)
    inbound_groupedSchedule = build_grouped_schedule(inbound_entries, operators_cache)
    
    if inbound_timetableData:
        inbound_first_stop_name = list(inbound_timetableData.keys())[0]
        inbound_first_stop_times = inbound_timetableData[inbound_first_stop_name]["times"]
    else:
        inbound_first_stop_name = None
        inbound_first_stop_times = []
    
    outbound_timetable = get_valid_timetable_entry(outbound_entries, current_date)
    outbound_timetableData = get_cached_normalized_stop_times(outbound_timetable)
    outbound_groupedSchedule = build_grouped_schedule(outbound_entries, operators_cache)
    
    if outbound_timetableData:
        outbound_first_stop_name = list(outbound_timetableData.keys())[0]
        outbound_first_stop_times = outbound_timetableData[outbound_first_stop_name]["times"]
    else:
        outbound_first_stop_name = None
        outbound_first_stop_times = []

    linked_timetable_blocks = [
        build_route_timetable_context(
            linked_route,
            selected_timetable_entries,
            route_stops_by_route_direction,
            current_date,
            operators_cache,
        )
        for linked_route in linked_routes
        if linked_route.id != route_instance.id
    ]
    
    combined_linked_timetables = None
    if len(linked_routes) > 1:
        linked_timetable_candidate = {
            "outbound": build_combined_linked_timetable(linked_routes, selected_timetable_entries, False),
            "inbound": build_combined_linked_timetable(linked_routes, selected_timetable_entries, True),
        }
        if linked_timetable_candidate["outbound"]["has_trips"] or linked_timetable_candidate["inbound"]["has_trips"]:
            combined_linked_timetables = linked_timetable_candidate
    
    # ========================================
    # BUILD CONTEXT
    # ========================================
    full_route_num = ' '.join(
        part for part in [
            route_instance.route_num,
            route_instance.inbound_destination,
            route_instance.outbound_destination,
        ]
        if part
    ).strip()
    
    helper_permissions = get_helper_permissions(request.user, operator)
    
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator.operator_slug}/'},
        {'name': route_instance.route_num or 'Route Details', 
         'url': f'/operator/{operator.operator_slug}/route/{route_id}/'}
    ]
    
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
    
    current_updates = [
        update for update in route_instance.service_updates.all() 
        if update.end_date >= current_date
    ]
    
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
        'transit_authority_details': transit_authority_details_obj,
        'inbound_first_stop_name': inbound_first_stop_name,
        'inbound_first_stop_times': inbound_first_stop_times,
        'outbound_first_stop_name': outbound_first_stop_name,
        'outbound_first_stop_times': outbound_first_stop_times,
        'linkedRoutes': [linked_route for linked_route in linked_routes if linked_route.id != route_instance.id],
        'linkedRouteOptions': linked_route_options,
        'linkedDestinationLines': linked_destination_lines,
        'linked_timetable_blocks': linked_timetable_blocks,
        'combined_linked_timetables': combined_linked_timetables,
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

@login_required
@require_POST
def operator_transfer_request(request, operator_slug):
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    helper_permissions = get_helper_permissions(request.user, operator)

    if 'owner' not in helper_permissions:
        return render(request, 'error/403.html', status=403)

    to_user_id = request.POST.get('to_user_id', '').strip()
    if not to_user_id.isdigit():
        messages.error(request, 'Please select a user to transfer the operator to.')
        return redirect('operator_manage', operator_slug=operator.operator_slug)

    to_user = get_object_or_404(CustomUser, id=int(to_user_id))
    if to_user == request.user:
        messages.error(request, 'You cannot transfer the operator to yourself.')
        return redirect('operator_manage', operator_slug=operator.operator_slug)

    if to_user == operator.owner:
        messages.error(request, 'This user already owns the operator.')
        return redirect('operator_manage', operator_slug=operator.operator_slug)

    # Cancel any other pending transfer requests for this operator
    operator.transfer_requests.filter(status=operatorTransferRequest.PENDING).exclude(to_user=to_user).update(
        status=operatorTransferRequest.DECLINED,
        responded_at=timezone.now(),
    )

    # Reuse an existing pending request to the same user instead of creating a duplicate
    existing = operator.transfer_requests.filter(
        to_user=to_user,
        status=operatorTransferRequest.PENDING,
    ).first()
    if existing:
        existing.from_user = request.user
        existing.save(update_fields=['from_user'])
    else:
        operatorTransferRequest.objects.create(
            operator=operator,
            from_user=request.user,
            to_user=to_user,
        )

    messages.success(
        request,
        f'Transfer request sent to {to_user.username}. They need to approve it on their profile before the operator is transferred.',
    )
    return redirect('operator_manage', operator_slug=operator.operator_slug)


@login_required
@require_POST
def operator_transfer_approve(request, operator_slug, request_id):
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    transfer_request = get_object_or_404(
        operatorTransferRequest,
        id=request_id,
        operator=operator,
        to_user=request.user,
        status=operatorTransferRequest.PENDING,
    )

    with transaction.atomic():
        transfer_request.status = operatorTransferRequest.APPROVED
        transfer_request.responded_at = timezone.now()
        transfer_request.save(update_fields=['status', 'responded_at'])

        operator.owner = request.user
        operator.save(update_fields=['owner'])

        # Cancel any other pending requests for this operator
        operator.transfer_requests.filter(status=operatorTransferRequest.PENDING).exclude(id=transfer_request.id).update(
            status=operatorTransferRequest.DECLINED,
            responded_at=timezone.now(),
        )

    messages.success(request, f'You are now the owner of {operator.operator_name}.')
    return redirect('user_profile', username=request.user.username)


@login_required
@require_POST
def operator_transfer_decline(request, operator_slug, request_id):
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    transfer_request = get_object_or_404(
        operatorTransferRequest,
        id=request_id,
        operator=operator,
        to_user=request.user,
        status=operatorTransferRequest.PENDING,
    )

    transfer_request.status = operatorTransferRequest.DECLINED
    transfer_request.responded_at = timezone.now()
    transfer_request.save(update_fields=['status', 'responded_at'])

    messages.success(request, f'You declined the transfer of {operator.operator_name}.')
    return redirect('user_profile', username=request.user.username)


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

def _process_vehicles_data(vehicles_qs, operator):
    vehicle_fields = (
        'id', 'fleet_number', 'fleet_number_sort', 'reg', 'prev_reg', 'colour',
        'branding', 'depot', 'name', 'features', 'last_tracked_date', 'last_tracked_route', 'for_sale',
        'type_details', 'open_top', 'in_service',
        'last_trip_datetime', 'last_trip_route_num',
        'livery__name', 'livery__left_css', 'livery__stroke_colour', 'livery__text_colour',
        'vehicleType__type_name',
        'loan_operator__operator_slug',
        'operator__operator_slug', 'operator__operator_code'
    )

    vehicles = list(vehicles_qs.order_by('fleet_number_sort').values(*vehicle_fields))

    latest_trips = {}
    if vehicles:
        vehicle_ids = [v['id'] for v in vehicles]
        try:
            trips = (
                Trip.objects
                .filter(trip_vehicle_id__in=vehicle_ids, trip_missed=False, trip_start_at__lte=timezone.now())
                .order_by('trip_vehicle_id', '-trip_start_at')
                .distinct('trip_vehicle_id')
                .values('trip_vehicle_id', 'trip_start_at', 'trip_route_num', 'trip_route__route_num')
            )
            latest_trips = {trip['trip_vehicle_id']: trip for trip in trips}
        except (NotImplementedError, NotSupportedError):
            seen = set()
            for trip in (
                Trip.objects
                .filter(trip_vehicle_id__in=vehicle_ids, trip_missed=False, trip_start_at__lte=timezone.now())
                .order_by('trip_vehicle_id', '-trip_start_at')
                .values('trip_vehicle_id', 'trip_start_at', 'trip_route_num', 'trip_route__route_num')[:len(vehicle_ids) * 2]
            ):
                vid = trip['trip_vehicle_id']
                if vid not in seen:
                    seen.add(vid)
                    latest_trips[vid] = trip

    now_local = timezone.localtime(timezone.now())
    now_date = now_local.date()
    now_year = now_local.year
    operator_slug_val = operator.operator_slug
    flickr_base = 'https://www.flickr.com/search/?text='
    flickr_suffix = '&sort=date-taken-desc'

    show_flags = {
        'livery': False, 'branding': False, 'prev_reg': False,
        'name': False, 'depot': False, 'features': False
    }

    for item in vehicles:
        trip = latest_trips.get(item['id'])
        if trip:
            item['last_trip_route'] = trip.get('trip_route__route_num') or trip.get('trip_route_num')
            trip_start = trip['trip_start_at']
            local_time = timezone.localtime(trip_start)
            if local_time.date() == now_date:
                item['last_trip_display'] = local_time.strftime('%H:%M')
            else:
                fmt = '%d %b %Y' if local_time.year != now_year else '%d %b'
                item['last_trip_display'] = local_time.strftime(fmt).lstrip('0')
            item['last_trip_date'] = trip_start.strftime('%Y-%m-%d')
        else:
            persisted_dt = item.get('last_trip_datetime')
            if persisted_dt:
                item['last_trip_route'] = item.get('last_trip_route_num') or None
                parsed_dt = None
                try:
                    parsed_dt = datetime.fromisoformat(persisted_dt)
                except (ValueError, TypeError):
                    pass
                if parsed_dt:
                    local_time = timezone.localtime(timezone.make_aware(parsed_dt) if timezone.is_naive(parsed_dt) else parsed_dt)
                    if local_time.date() == now_date:
                        item['last_trip_display'] = local_time.strftime('%H:%M')
                    else:
                        fmt = '%d %b %Y' if local_time.year != now_year else '%d %b'
                        item['last_trip_display'] = local_time.strftime(fmt).lstrip('0')
                    item['last_trip_date'] = parsed_dt.strftime('%Y-%m-%d')
                else:
                    item['last_trip_route'] = item['last_trip_display'] = item['last_trip_date'] = None
            else:
                legacy_dt = item.get('last_tracked_date')
                if legacy_dt:
                    item['last_trip_route'] = item.get('last_tracked_route') or None
                    local_time = timezone.localtime(legacy_dt) if timezone.is_aware(legacy_dt) else legacy_dt
                    if local_time.date() == now_date:
                        item['last_trip_display'] = local_time.strftime('%H:%M')
                    else:
                        fmt = '%d %b %Y' if local_time.year != now_year else '%d %b'
                        item['last_trip_display'] = local_time.strftime(fmt).lstrip('0')
                    if hasattr(local_time, 'strftime'):
                        item['last_trip_date'] = local_time.strftime('%Y-%m-%d')
                    else:
                        item['last_trip_date'] = str(local_time)[:10]
                else:
                    item['last_trip_route'] = item['last_trip_display'] = item['last_trip_date'] = None

        loan_slug = item.get('loan_operator__operator_slug')
        item['onloan'] = bool(loan_slug and item['operator__operator_slug'] == operator_slug_val and loan_slug != operator_slug_val)

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

        show_flags['livery'] = show_flags['livery'] or bool(item.get('livery__name') or item.get('colour'))
        show_flags['branding'] = show_flags['branding'] or bool(item.get('branding') and item.get('livery__name'))
        show_flags['prev_reg'] = show_flags['prev_reg'] or bool(prev_reg)
        show_flags['name'] = show_flags['name'] or bool(item.get('name'))
        show_flags['depot'] = show_flags['depot'] or bool(item.get('depot'))
        show_flags['features'] = show_flags['features'] or bool(item.get('features'))

    return vehicles, show_flags


def vehicles(request, operator_slug, depot=None, withdrawn=False):
    """Fast-loading vehicle list - renders shell immediately, data loaded via API."""
    auto_return_expired_loans()
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
    type_id = request.GET.get('type')

    # Build base queryset once — reused for both count and direct load
    base_qs = fleet.objects.filter(Q(operator=operator) | Q(loan_operator=operator))
    if not withdrawn:
        base_qs = base_qs.filter(in_service=True)
    if depot:
        base_qs = base_qs.filter(depot=depot)
    if type_id and type_id.isdigit():
        base_qs = base_qs.filter(vehicleType_id=int(type_id))
    total_count = base_qs.count()

    # Vehicle type filter options (distinct types across the operator's fleet)
    vehicle_type_options = [
        {'id': o[0], 'name': o[1]}
        for o in fleet.objects
        .filter(Q(operator=operator) | Q(loan_operator=operator))
        .exclude(vehicleType__isnull=True)
        .order_by('vehicleType__type_name')
        .values_list('vehicleType_id', 'vehicleType__type_name')
        .distinct()
    ]
    vehicle_type_options_json = json.dumps(vehicle_type_options)
    current_type = type_id if type_id and type_id.isdigit() else ''

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

    # Direct DB load for small fleets (< 1000 vehicles) — avoids API round-trip
    direct_load = total_count < 1000
    if direct_load:
        vehicles_data, show_flags = _process_vehicles_data(base_qs, operator)
        vehicles_json = json.dumps(vehicles_data, cls=DjangoJSONEncoder)
        show_flags_json = json.dumps(show_flags)
        pagination_json = json.dumps({
            'current_page': 1,
            'total_pages': 1,
            'has_previous': False,
            'has_next': False,
            'previous_page': None,
            'next_page': None,
        })
    else:
        vehicles_json = None
        show_flags_json = None
        pagination_json = None

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
        'vehicles_json': vehicles_json,
        'show_flags_json': show_flags_json,
        'pagination_json': pagination_json,
        'show_fleet_icons': request.user.fleet_icons if request.user.is_authenticated else True,
        'vehicle_type_options_json': vehicle_type_options_json,
        'current_type': current_type,
        'show_vehicle_type_filter': operator.operator_slug == 'abandoned-buses-llc',
    }
    return render(request, 'vehicles.html', context)


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone


def vehicles_api(request, operator_slug):
    """API endpoint for vehicle data - optimized for remote DB."""
    auto_return_expired_loans()
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    
    withdrawn = request.GET.get('withdrawn', '').lower() == 'true'
    depot = request.GET.get('depot')
    page = request.GET.get('page', 1)
    type_id = request.GET.get('type')

    # Base queryset with select_related to reduce queries
    qs = fleet.objects.filter(
        Q(operator=operator) | Q(loan_operator=operator)
    ).select_related('livery', 'vehicleType', 'loan_operator', 'operator')
    
    if not withdrawn:
        qs = qs.filter(in_service=True)
    if depot:
        qs = qs.filter(depot=depot)
    if type_id and type_id.isdigit():
        qs = qs.filter(vehicleType_id=int(type_id))

    # Define fields
    vehicle_fields = (
        'id', 'fleet_number', 'fleet_number_sort', 'reg', 'prev_reg', 'colour',
        'branding', 'depot', 'name', 'features', 'last_tracked_date', 'last_tracked_route', 'for_sale',
        'type_details', 'open_top', 'in_service',
        'last_trip_datetime', 'last_trip_route_num',
        'livery__name', 'livery__left_css', 'livery__stroke_colour', 'livery__text_colour',
        'vehicleType__type_name',
        'loan_operator__operator_slug',
        'operator__operator_slug', 'operator__operator_code'
    )

    # Paginate (Paginator internally counts, no need for separate qs.count())
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
        except (NotImplementedError, NotSupportedError):
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
            persisted_dt = item.get('last_trip_datetime')
            if persisted_dt:
                item['last_trip_route'] = item.get('last_trip_route_num') or None
                parsed_dt = None
                try:
                    parsed_dt = datetime.fromisoformat(persisted_dt)
                except (ValueError, TypeError):
                    pass
                if parsed_dt:
                    local_time = timezone.localtime(timezone.make_aware(parsed_dt) if timezone.is_naive(parsed_dt) else parsed_dt)
                    if local_time.date() == now_date:
                        item['last_trip_display'] = local_time.strftime('%H:%M')
                    else:
                        fmt = '%d %b %Y' if local_time.year != now_year else '%d %b'
                        item['last_trip_display'] = local_time.strftime(fmt).lstrip('0')
                    item['last_trip_date'] = parsed_dt.strftime('%Y-%m-%d')
                else:
                    item['last_trip_route'] = item['last_trip_display'] = item['last_trip_date'] = None
            else:
                legacy_dt = item.get('last_tracked_date')
                if legacy_dt:
                    item['last_trip_route'] = item.get('last_tracked_route') or None
                    local_time = timezone.localtime(legacy_dt) if timezone.is_aware(legacy_dt) else legacy_dt
                    if local_time.date() == now_date:
                        item['last_trip_display'] = local_time.strftime('%H:%M')
                    else:
                        fmt = '%d %b %Y' if local_time.year != now_year else '%d %b'
                        item['last_trip_display'] = local_time.strftime(fmt).lstrip('0')
                    if hasattr(local_time, 'strftime'):
                        item['last_trip_date'] = local_time.strftime('%Y-%m-%d')
                    else:
                        item['last_trip_date'] = str(local_time)[:10]
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
        'total_count': paginator.count,
    })

def vehicle_detail(request, operator_slug, vehicle_id):
    response = feature_enabled(request, "view_vehicles")
    if response:
        return response
    
    auto_return_expired_loans()
    try:
        operator = MBTOperator.objects.only(
            'id', 'operator_name', 'operator_code', 'operator_slug', 'owner_id'
        ).get(operator_slug=operator_slug)
        vehicle = fleet.objects.select_related(
            'operator',
            'loan_operator',
            'vehicleType',
            'livery',
            'vehicle_category',
            'current_trip',
        ).get(id=vehicle_id, operator=operator)

        trip_dates_cache_key = f'vehicle_trip_dates:{vehicle_id}'
        all_trip_dates = cache.get(trip_dates_cache_key)
        if all_trip_dates is None:
            trip_date_values = Trip.objects.filter(trip_vehicle_id=vehicle_id).dates('trip_start_at', 'day', order='DESC')
            all_trip_dates = [d.date() if hasattr(d, 'date') else d for d in trip_date_values]
            cache.set(trip_dates_cache_key, all_trip_dates, 300)

    except (MBTOperator.DoesNotExist, fleet.DoesNotExist):
        return render(request, '404.html', status=404)

    helper_permissions = get_helper_permissions(request.user, operator)

    vehicle_on_loan = (
        vehicle.loan_operator_id is not None
        and vehicle.loan_operator_id != vehicle.operator_id
    )
    if vehicle_on_loan:
        # While on loan, only the loanee may edit/log the loaned bus. The origin
        # operator cannot edit or sell it until it is returned.
        helper_permissions = get_helper_permissions(request.user, vehicle.loan_operator)

    # If a date is selected via GET, use it, else default to today
    selected_date_str = request.GET.get("date")
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = all_trip_dates[0] if all_trip_dates else date.today()

    
    start_of_day = timezone.make_aware(datetime.combine(selected_date, time.min))
    end_of_day = timezone.make_aware(datetime.combine(selected_date, time.max))


    trips = list(Trip.objects.filter(
        trip_vehicle_id=vehicle_id,
        trip_start_at__range=(start_of_day, end_of_day)
    ).select_related('trip_route', 'trip_board').only(
        'trip_id', 'trip_vehicle_id', 'trip_start_at', 'trip_end_at',
        'trip_route_id', 'trip_board_id', 'trip_driver_id',
        'trip_route_num', 'trip_display_id', 'trip_inbound',
        'trip_start_location', 'trip_end_location', 'trip_missed',
        'trip_route__route_num', 'trip_route__inbound_destination',
        'trip_route__outbound_destination',
        'trip_board__duty_name', 'trip_board__board_type',
    ).order_by('trip_start_at'))

    trips_json = json.dumps([
        {
            'pk': t.trip_id,
            'model': 'tracking.trip',
            'fields': {
                'trip_id': t.trip_id,
                'trip_vehicle_id': t.trip_vehicle_id,
                'trip_start_at': t.trip_start_at.isoformat() if t.trip_start_at else None,
                'trip_end_at': t.trip_end_at.isoformat() if t.trip_end_at else None,
                'trip_route_id': t.trip_route_id,
                'trip_board_id': t.trip_board_id,
                'trip_driver_id': t.trip_driver_id,
                'trip_route_num': t.trip_route_num,
                'trip_display_id': t.trip_display_id,
                'trip_inbound': t.trip_inbound,
                'trip_start_location': t.trip_start_location,
                'trip_end_location': t.trip_end_location,
                'trip_missed': t.trip_missed,
            }
        }
        for t in trips
    ], default=str)

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

    def _format_last_trip_datetime(dt_str):
        if not dt_str:
            return None
        try:
            parsed = datetime.fromisoformat(dt_str)
        except (ValueError, TypeError):
            return None
        fmt = '%d %b %Y' if parsed.year != timezone.now().year else '%d %b'
        return parsed.strftime(fmt).lstrip('0')

    def _format_last_trip_datetime_time(dt_str):
        if not dt_str:
            return None
        try:
            parsed = datetime.fromisoformat(dt_str)
        except (ValueError, TypeError):
            return None
        return parsed.strftime('%H:%M')

    def vehicle_link_data(other_vehicle):
        if not other_vehicle:
            return None
        display = (
            f"{other_vehicle.fleet_number} - {other_vehicle.reg}"
            if other_vehicle.reg and other_vehicle.fleet_number
            else other_vehicle.reg or other_vehicle.fleet_number or str(other_vehicle.id)
        )
        return {
            'id': other_vehicle.id,
            'fleet_number': other_vehicle.fleet_number,
            'reg': other_vehicle.reg,
            'display': display,
            'link': f"/operator/{operator.operator_slug}/vehicles/{other_vehicle.id}/",
        }

    previous_vehicle = None
    next_vehicle = None
    if vehicle.fleet_number_sort is not None:
        previous_vehicle = (
            fleet.objects
            .filter(operator_id=operator.id, in_service=True, fleet_number_sort__lt=vehicle.fleet_number_sort)
            .only('id', 'fleet_number', 'reg')
            .order_by('-fleet_number_sort')
            .first()
        )
        next_vehicle = (
            fleet.objects
            .filter(operator_id=operator.id, in_service=True, fleet_number_sort__gt=vehicle.fleet_number_sort)
            .only('id', 'fleet_number', 'reg')
            .order_by('fleet_number_sort')
            .first()
        )

    reg = vehicle.reg.replace(' ', '') if vehicle.reg else ''
    prev_reg = vehicle.prev_reg.replace(' ', '') if vehicle.prev_reg else ''
    if prev_reg:
        flickr_link = f'https://www.flickr.com/search/?text="{vehicle.reg}"%20or%20{reg}%20or%20"{vehicle.prev_reg}"%20or%20{prev_reg}&sort=date-taken-desc'
    else:
        flickr_link = f'https://www.flickr.com/search/?text="{vehicle.reg}"%20or%20{reg}&sort=date-taken-desc'

    serialized_vehicle_data = {
        'id': vehicle.id,
        'in_service': vehicle.in_service,
        'for_sale': vehicle.for_sale,
        'preserved': vehicle.preserved,
        'on_load': vehicle.on_load,
        'open_top': vehicle.open_top,
        'fleet_number': vehicle.fleet_number,
        'reg': vehicle.reg,
        'operator': {
            'id': operator.id,
            'operator_name': operator.operator_name,
            'operator_slug': operator.operator_slug,
            'operator_code': operator.operator_code,
        },
        'loan_operator': {
            'id': vehicle.loan_operator.id,
            'operator_name': vehicle.loan_operator.operator_name,
            'operator_slug': vehicle.loan_operator.operator_slug,
            'operator_code': vehicle.loan_operator.operator_code,
        } if vehicle.loan_operator else None,
        'vehicle_type_data': {
            'id': vehicle.vehicleType.id,
            'type_name': vehicle.vehicleType.type_name,
            'double_decker': vehicle.vehicleType.double_decker,
            'type': vehicle.vehicleType.type,
            'fuel': vehicle.vehicleType.fuel,
        } if vehicle.vehicleType else None,
        'type_details': vehicle.type_details,
        'livery': {
            'id': vehicle.livery.id,
            'name': vehicle.livery.name,
            'colour': vehicle.livery.colour,
            'left_css': vehicle.livery.left_css,
            'right_css': vehicle.livery.right_css,
            'text_colour': vehicle.livery.text_colour,
            'stroke_colour': vehicle.livery.stroke_colour,
        } if vehicle.livery else None,
        'colour': vehicle.colour,
        'branding': vehicle.branding,
        'prev_reg': vehicle.prev_reg,
        'depot': vehicle.depot,
        'name': vehicle.name,
        'engine': vehicle.engine,
        'gearbox': vehicle.gearbox,
        'door_amount': vehicle.door_amount,
        'features': vehicle.features,
        'notes': vehicle.notes,
        'length': vehicle.length,
        'advanced_details': vehicle.advanced_details,
        'vehicle_category': {
            'name': vehicle.vehicle_category.name,
        } if vehicle.vehicle_category else None,
        'previous_vehicle': vehicle_link_data(previous_vehicle),
        'next_vehicle': vehicle_link_data(next_vehicle),
        'flickr_link': flickr_link,
        'last_trip_datetime': vehicle.last_trip_datetime,
        'last_trip_route_num': vehicle.last_trip_route_num,
        'last_tracked_date': vehicle.last_tracked_date,
        'last_tracked_route': vehicle.last_tracked_route,
        'last_trip_datetime_formatted': _format_last_trip_datetime(vehicle.last_trip_datetime),
        'last_trip_datetime_time': _format_last_trip_datetime_time(vehicle.last_trip_datetime),
    }

    last_trip = (
        Tracking.objects
        .filter(tracking_vehicle_id=vehicle_id, trip_ended=False)
        .order_by('-tracking_start_at')
        .first()
    )

    now = timezone.now()

    context = {
        'last_trip': last_trip,
        'all_trip_dates': all_trip_dates,
        'selected_date': selected_date,
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'vehicle': serialized_vehicle_data,
        'helper_permissions': helper_permissions,
        'tabs': tabs,
        'now': now,
        'trips': trips,
        'show_board': any(t.trip_board for t in trips),
        'trips_json': trips_json,
        'show_fleet_icons': request.user.fleet_icons if request.user.is_authenticated else True,
        'vehicle_on_loan': vehicle_on_loan,
        'loan_operator_obj': vehicle.loan_operator,
        'loan_until': vehicle.loan_until,
    }
    return render(request, 'vehicle_detail.html', context)


def vehicle_archived(request, operator_slug, vehicle_id):
    response = feature_enabled(request, "view_vehicles")
    if response:
        return response
    
    try:
        operator = MBTOperator.objects.only(
            'id', 'operator_name', 'operator_code', 'operator_slug', 'owner_id'
        ).get(operator_slug=operator_slug)
        vehicle = fleet.objects.select_related(
            'operator',
            'loan_operator',
            'vehicleType',
            'livery',
            'vehicle_category',
        ).only(
            'id', 'fleet_number', 'reg', 'in_service', 'operator_id',
            'loan_operator_id', 'vehicleType_id', 'livery_id',
            'vehicle_category_id', 'colour', 'branding', 'fleet_number_sort',
        ).get(id=vehicle_id, operator=operator)
    except (MBTOperator.DoesNotExist, fleet.DoesNotExist):
        return render(request, '404.html', status=404)

    trip_dates_cache_key = f'vehicle_archived_dates:{vehicle_id}'
    all_trip_dates = cache.get(trip_dates_cache_key)
    if all_trip_dates is None:
        date_values = TripArchive.objects.filter(
            trip_vehicle_id=vehicle_id
        ).dates('trip_start_at', 'day', order='DESC')
        all_trip_dates = [d.date() if hasattr(d, 'date') else d for d in date_values]
        cache.set(trip_dates_cache_key, all_trip_dates, 300)

    selected_date_str = request.GET.get("date")
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = all_trip_dates[0] if all_trip_dates else date.today()
    else:
        selected_date = all_trip_dates[0] if all_trip_dates else date.today()

    start_of_day = timezone.make_aware(datetime.combine(selected_date, time.min))
    end_of_day = timezone.make_aware(datetime.combine(selected_date, time.max))

    trips = list(TripArchive.objects.filter(
        trip_vehicle_id=vehicle_id,
        trip_start_at__range=(start_of_day, end_of_day)
    ).select_related('trip_route', 'trip_board').order_by('trip_start_at'))

    helper_permissions = get_helper_permissions(request.user, operator)

    def vehicle_link_data(other_vehicle):
        if not other_vehicle:
            return None
        display = (
            f"{other_vehicle.fleet_number} - {other_vehicle.reg}"
            if other_vehicle.reg and other_vehicle.fleet_number
            else other_vehicle.reg or other_vehicle.fleet_number or str(other_vehicle.id)
        )
        return {
            'id': other_vehicle.id,
            'fleet_number': other_vehicle.fleet_number,
            'reg': other_vehicle.reg,
            'display': display,
            'link': f"/operator/{operator.operator_slug}/vehicles/{other_vehicle.id}/",
        }

    previous_vehicle = None
    next_vehicle = None
    if vehicle.fleet_number_sort is not None:
        previous_vehicle = (
            fleet.objects
            .filter(operator_id=operator.id, in_service=True, fleet_number_sort__lt=vehicle.fleet_number_sort)
            .only('id', 'fleet_number', 'reg')
            .order_by('-fleet_number_sort')
            .first()
        )
        next_vehicle = (
            fleet.objects
            .filter(operator_id=operator.id, in_service=True, fleet_number_sort__gt=vehicle.fleet_number_sort)
            .only('id', 'fleet_number', 'reg')
            .order_by('fleet_number_sort')
            .first()
        )

    vehicle.previous_vehicle = vehicle_link_data(previous_vehicle)
    vehicle.next_vehicle = vehicle_link_data(next_vehicle)

    bread_operator = {'name': operator.operator_name, 'url': f'/operator/{operator.operator_slug}/'}
    if vehicle.loan_operator_id and vehicle.loan_operator_id != operator.id:
        loan_op = MBTOperator.objects.only('id', 'operator_name', 'operator_slug').get(id=vehicle.loan_operator_id)
        bread_operator = {'name': f"{loan_op.operator_name} (on loan from {operator.operator_name})", 'url': f'/operator/{operator.operator_slug}/'}

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        bread_operator,
        {'name': 'Vehicles', 'url': f'/operator/{operator.operator_slug}/vehicles#{vehicle.fleet_number}-{operator.operator_code}'},
        {'name': f'{vehicle.fleet_number} - {vehicle.reg}', 'url': f'/operator/{operator.operator_slug}/vehicles/{vehicle_id}/'},
        {'name': 'Archived Trips', 'url': ''},
    ]

    tabs = generate_tabs("vehicles", operator)

    context = {
        'operator': operator,
        'vehicle': vehicle,
        'helper_permissions': helper_permissions,
        'tabs': tabs,
        'breadcrumbs': breadcrumbs,
        'all_trip_dates': all_trip_dates,
        'selected_date': selected_date,
        'trips': trips,
    }
    return render(request, 'vehicle_archived.html', context)


def vehicle_archived_dates_json(request, operator_slug, vehicle_id):
    try:
        operator = MBTOperator.objects.only('id').get(operator_slug=operator_slug)
        vehicle = fleet.objects.only('id').get(id=vehicle_id, operator=operator)
    except (MBTOperator.DoesNotExist, fleet.DoesNotExist):
        return JsonResponse({'error': 'Not found'}, status=404)

    try:
        limit = int(request.GET.get('limit', 30))
    except (TypeError, ValueError):
        limit = 30
    try:
        offset = int(request.GET.get('offset', 0))
    except (TypeError, ValueError):
        offset = 0

    cache_key = f'vehicle_archived_dates:{vehicle_id}'
    all_dates = cache.get(cache_key)
    if all_dates is None:
        date_values = TripArchive.objects.filter(
            trip_vehicle_id=vehicle_id
        ).dates('trip_start_at', 'day', order='DESC')
        all_dates = [d.date().isoformat() if hasattr(d, 'date') else d for d in date_values]
        cache.set(cache_key, all_dates, 300)

    page = all_dates[offset:offset + limit]
    has_more = (offset + limit) < len(all_dates)

    return JsonResponse({
        'dates': page,
        'total': len(all_dates),
        'has_more': has_more,
        'next_offset': offset + limit if has_more else None,
    })


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
    vehicle = get_object_or_404(fleet, id=vehicle_id)

    on_loan = (
        vehicle.loan_operator_id is not None
        and vehicle.loan_operator_id != vehicle.operator_id
    )

    origin_perms = get_helper_permissions(request.user, vehicle.operator)
    can_edit_origin = (
        request.user == vehicle.operator.owner
        or 'Edit Buses' in origin_perms
        or request.user.is_superuser
    )

    is_loanee_edit = False
    if on_loan:
        if can_edit_origin and not request.user.is_superuser:
            messages.error(request, "This vehicle is on loan and cannot be edited until it is returned.")
            return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/')
        loan_perms = get_helper_permissions(request.user, vehicle.loan_operator)
        can_edit_loanee = (
            request.user == vehicle.loan_operator.owner
            or 'Edit Buses' in loan_perms
            or request.user.is_superuser
        )
        if not can_edit_loanee:
            return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/')
        is_loanee_edit = True
    else:
        if not can_edit_origin:
            return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/')

    # Load related data needed for selects and checkboxes
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
        was_on_loan = (
            vehicle.loan_operator_id is not None
            and vehicle.loan_operator_id != vehicle.operator_id
        )
        loan_starting = False
        loan_returning = False
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
        vehicle.engine = request.POST.get('engine', '').strip()
        vehicle.gearbox = request.POST.get('gearbox', '').strip()
        vehicle.door_amount = request.POST.get('door_amount', '').strip()
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

        if is_loanee_edit:
            # A loanee editing a loaned bus cannot change which operator owns it,
            # which operator it is on loan to, or the loan return date.
            vehicle.operator = current_operator
        else:
            try:
                new_operator = MBTOperator.objects.get(id=request.POST.get('operator'))
            except (MBTOperator.DoesNotExist, TypeError, ValueError):
                new_operator = None
            if new_operator != current_operator:
                vehicle.for_sale = False
            vehicle.operator = new_operator

            loan_op = request.POST.get('loan_operator')
            if loan_op == "null" or not loan_op:
                vehicle.loan_operator = None
                vehicle.loan_until = None
            else:
                try:
                    vehicle.loan_operator = MBTOperator.objects.get(id=loan_op)
                except MBTOperator.DoesNotExist:
                    vehicle.loan_operator = None

                loan_until_str = request.POST.get('loan_until', '').strip()
                loan_until = None
                if loan_until_str:
                    try:
                        loan_until = parse_datetime(loan_until_str)
                    except (ValueError, TypeError):
                        loan_until = None
                    if loan_until is not None and timezone.is_naive(loan_until):
                        loan_until = timezone.make_aware(loan_until)
                vehicle.loan_until = loan_until

            loan_active = (
                vehicle.loan_operator_id is not None
                and vehicle.loan_operator_id != vehicle.operator_id
            )
            if loan_active and not was_on_loan and not vehicle.loan_snapshot:
                # A loan is starting: mark it so the snapshot of the final saved
                # state is captured before saving.
                loan_starting = True
            elif not loan_active and was_on_loan and vehicle.loan_snapshot:
                # Loan ending manually: revert all loanee edits and return home.
                loan_returning = True

        type_id = request.POST.get('type')
        if type_id:
            try:
                vehicle.vehicleType = vehicleType.objects.get(id=type_id)
            except vehicleType.DoesNotExist:
                vehicle.vehicleType = None
        else:
            vehicle.vehicleType = None

        livery_id = request.POST.get('livery')
        if livery_id:
            try:
                vehicle.livery = liverie.objects.get(id=livery_id)
            except liverie.DoesNotExist:
                vehicle.livery = None
        else:
            vehicle.livery = None

        # Vehicle category (must belong to the current or loan operator)
        try:
            from routes.models import board_category as BoardCategory
            vc_id = request.POST.get('vehicle_category')
            if vc_id:
                try:
                    cat = BoardCategory.objects.get(id=vc_id)
                    # Loanee may set a category from the loan operator so the bus
                    # can be table logged; otherwise category must match owner.
                    cat_operator_id = (
                        vehicle.loan_operator_id if is_loanee_edit else vehicle.operator_id
                    )
                    if cat.operator and cat.operator.id == cat_operator_id:
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

        if loan_starting:
            vehicle.loan_snapshot = capture_loan_snapshot(vehicle)
        elif loan_returning:
            restore_loan_snapshot(vehicle, vehicle.loan_snapshot)
            vehicle.loan_snapshot = None
            vehicle.loan_operator = None
            vehicle.loan_until = None

        try:
            vehicle.save()
        except OperationalError:
            messages.error(
                request,
                "The database is busy right now. Your changes could not be saved. "
                "Please try again in a few seconds."
            )
            return redirect('vehicle_detail', operator_slug=vehicle.operator.operator_slug, vehicle_id=vehicle_id)

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
        elif on_loan:
            hide_sell_button = True
        else:
            hide_sell_button = False

        # Categories for this operator (loanee editing uses the loan operator's
        # categories so the bus can be table logged while on loan)
        try:
            from routes.models import board_category as BoardCategory
            category_operator = vehicle.loan_operator if is_loanee_edit else vehicle.operator
            category_list = BoardCategory.objects.filter(operator=category_operator)
        except Exception:
            category_list = []

        all_types = vehicleType.objects.all()
        type_lengths_map = {t.id: [l.strip() for l in t.lengths.split(',') if l.strip()] for t in all_types}
        type_engine_map = {t.id: [e.strip() for e in t.engine.split(',') if e.strip()] for t in all_types}
        type_gearbox_map = {t.id: [g.strip() for g in t.gearbox.split(',') if g.strip()] for t in all_types}
        type_door_map = {t.id: [d.strip() for d in t.door_amount.split(',') if d.strip()] for t in all_types}
        type_category_map = {t.id: t.type for t in all_types}
        type_fuel_map = {t.id: t.fuel for t in all_types}
        context = {
            'hide_sell_button': hide_sell_button,
            'fleetData': vehicle,
            'operator': vehicle.operator,
            'type': vehicle.vehicleType,
            'type_lengths_json': json.dumps(type_lengths_map),
            'type_engine_json': json.dumps(type_engine_map),
            'type_gearbox_json': json.dumps(type_gearbox_map),
            'type_door_json': json.dumps(type_door_map),
            'type_category_json': json.dumps(type_category_map),
            'type_fuel_json': json.dumps(type_fuel_map),
            'livery': vehicle.livery,
            'categoryData': category_list,
            'features': features_list,
            'userData': user_data,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
            "custom": advanced_details_to_text(vehicle.advanced_details),
            'allowed_operators': allowed_operators,
            'on_loan': on_loan,
            'is_loanee_edit': is_loanee_edit,
            'loan_operator': vehicle.loan_operator,
            'loan_until': vehicle.loan_until,
        }
        add_favourite_select_context(context, request.user,)
        return render(request, 'edit.html', context)

def vehicles_trip_manage(request, operator_slug, vehicle_id):
    response = feature_enabled(request, "manage_trips")
    if response:
        return response
    
    
    try:
        operator = MBTOperator.objects.get(operator_slug=operator_slug)
        vehicle = fleet.objects.get(id=vehicle_id, operator=operator)
        all_trip_dates = Trip.objects.filter(trip_vehicle=vehicle).dates('trip_start_at', 'day', order='DESC')
        all_trip_dates = [d.date() if hasattr(d, 'date') else d for d in all_trip_dates]
        
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

    
    start_of_day = timezone.make_aware(datetime.combine(selected_date, time.min))
    end_of_day = timezone.make_aware(datetime.combine(selected_date, time.max))


    trips = Trip.objects.filter(
        trip_vehicle=vehicle,
        trip_start_at__range=(start_of_day, end_of_day)
    ).only(
        'trip_id', 'trip_vehicle_id', 'trip_start_at', 'trip_end_at',
        'trip_route_id', 'trip_board_id', 'trip_driver_id',
        'trip_route_num', 'trip_display_id', 'trip_inbound',
        'trip_start_location', 'trip_end_location', 'trip_missed',
    ).order_by('trip_start_at')

    trips_json = json.dumps([
        {
            'pk': t.trip_id,
            'model': 'tracking.trip',
            'fields': {
                'trip_id': t.trip_id,
                'trip_vehicle_id': t.trip_vehicle_id,
                'trip_start_at': t.trip_start_at.isoformat() if t.trip_start_at else None,
                'trip_end_at': t.trip_end_at.isoformat() if t.trip_end_at else None,
                'trip_route_id': t.trip_route_id,
                'trip_board_id': t.trip_board_id,
                'trip_driver_id': t.trip_driver_id,
                'trip_route_num': t.trip_route_num,
                'trip_display_id': t.trip_display_id,
                'trip_inbound': t.trip_inbound,
                'trip_start_location': t.trip_start_location,
                'trip_end_location': t.trip_end_location,
                'trip_missed': t.trip_missed,
            }
        }
        for t in trips
    ], default=str)
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
#        response = http_post(webhook_url, json=data)
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
            response_message = http_post(
                f"{settings.DISCORD_BOT_API_URL}/send-message-clean",
                data=message_data,
                files=None,
                timeout=5,
            )
            # raise for bad status codes
            response_message.raise_for_status()
            response_message.close()
    except RequestException as e:
        return False, f"Failed to send Discord message: {e}"

    # now send the embed
    try:
        response = http_post(
            f"{settings.DISCORD_BOT_API_URL}/send-embed",
            json=data,
            timeout=5,
        )
        response.raise_for_status()
        response.close()
    except RequestException as e:
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

    if (
        vehicle.loan_operator_id is not None
        and vehicle.loan_operator_id != vehicle.operator_id
    ):
        messages.error(request, "This vehicle is on loan and cannot be listed for sale until it is returned.")
        return redirect(f'/operator/{operator_slug}/vehicles/{vehicle_id}/')

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

    board_type_url = board_type.replace('duty', 'duties')

    try:
        operator = MBTOperator.objects.get(operator_slug=operator_slug)
        duties_queryset = duty.objects.filter(duty_operator=operator, board_type=board_type).prefetch_related('duty_day', 'category').order_by('duty_name')
    except MBTOperator.DoesNotExist:
        return render(request, '404.html', status=404)

    userPerms = get_helper_permissions(request.user, operator)

    # Operators the user is a helper on (for the Transfer to Operator action)
    transfer_operators = []
    if request.user.is_authenticated:
        helper_op_ids = helper.objects.filter(helper=request.user).values_list('operator_id', flat=True)
        owned_op_ids = MBTOperator.objects.filter(owner=request.user).values_list('id', flat=True)
        all_op_ids = set(helper_op_ids) | set(owned_op_ids)
        transfer_operators = (
            MBTOperator.objects.filter(id__in=all_op_ids)
            .exclude(id=operator.id)
            .order_by('operator_name')
        )

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
        {'name': titles, 'url': f'/operator/{operator_slug}/{board_type_url}/'}
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
        'transfer_operators': transfer_operators,
        'board_type': board_type,
        'board_type_url': board_type_url,
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

    board_type_url = board_type.replace('duty', 'duties')

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    duty_instance = get_object_or_404(duty, id=duty_id, duty_operator=operator)

    userPerms = get_helper_permissions(request.user, operator)

    if request.method == "POST" and request.POST.get("no_run_period"):
        if request.user != operator.owner and 'Edit Duties' not in userPerms and not request.user.is_superuser:
            messages.error(request, f"You do not have permission to edit this {title} for this operator.")
            return redirect(request.path)

        start_str = request.POST.get("no_run_start", "").strip()
        end_str = request.POST.get("no_run_end", "").strip()

        if request.POST.get("no_run_clear"):
            start_str = ""
            end_str = ""

        def parse_date_field(value):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except (TypeError, ValueError):
                return None

        no_run_start = parse_date_field(start_str)
        no_run_end = parse_date_field(end_str)

        if (start_str or end_str) and not (no_run_start and no_run_end):
            messages.error(request, "Set both a no-run start and end date, or clear both.")
            return redirect(request.path)

        if no_run_start and no_run_end and no_run_start > no_run_end:
            messages.error(request, "No-run start must be on or before the no-run end date.")
            return redirect(request.path)

        duty_instance.no_run_start = no_run_start
        duty_instance.no_run_end = no_run_end
        duty_instance.save(update_fields=["no_run_start", "no_run_end"])
        if no_run_start and no_run_end:
            messages.success(request, f"No-run period set for {no_run_start.isoformat()} to {no_run_end.isoformat()}.")
        else:
            messages.success(request, "No-run period cleared.")
        return redirect(request.path)

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
        {'name': titles, 'url': f'/operator/{operator_slug}/{board_type_url}/'},
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

    board_type_url = board_type.replace('duty', 'duties')

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, f"You do not have permission to add a {titles} for this operator.")
        return redirect(f'/operator/{operator_slug}/{board_type_url}/')

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
            try:
                gen_rest_minutes = max(0, int(request.POST.get('rest_minutes', '0') or 0))
            except (TypeError, ValueError):
                gen_rest_minutes = 0
            
            if not route_id:
                messages.error(request, "Please select a route.")
                return redirect(f'/operator/{operator_slug}/{board_types}/add/')
            
            selected_route = get_object_or_404(route, id=route_id)
            
            # Get category if selected
            selected_category = None
            if gen_category_id:
                try:
                    selected_category = board_category.objects.get(id=gen_category_id, operator=operator)
                except board_category.DoesNotExist:
                    pass
            
            # Get timetable entries for this route
            timetables = timetableEntry.objects.filter(route=selected_route, active=True)
            
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
                
                previous_start_mins = None
                for i, start_time in enumerate(first_times):
                    if not start_time:
                        continue
                    end_time = last_times[i] if i < len(last_times) else None
                    if not end_time:
                        continue
                    
                    start_mins, end_mins = normalize_trip_minutes(
                        start_time,
                        end_time,
                        previous_start_mins,
                    )
                    if start_mins is None or end_mins is None:
                        continue
                    previous_start_mins = start_mins
                    
                    # Use logical location: outbound ends at 'far', inbound ends at 'home'
                    # Circular routes loop back to their start, so they start and end at
                    # 'home', letting a single vehicle chain consecutive loops.
                    if bool(tt.circular) or (tt.route_id and not getattr(tt.route, 'outbound_destination', None)):
                        start_loc = 'home'
                        end_loc = 'home'
                    elif is_inbound:
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
                return redirect(f'/operator/{operator_slug}/{board_types}/add/')
            
            # Vehicle blocking algorithm - assign trips to vehicles
            vehicles = []  # List of vehicle blocks
            
            for trip in all_trips:
                # Find a vehicle that can do this trip
                best_vehicle = None
                best_wait_time = float('inf')
                
                for v in vehicles:
                    # Check if vehicle is available and at the right location
                    if v['end_minutes'] + gen_rest_minutes <= trip['start_minutes']:
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
                return redirect(f'/operator/{operator_slug}/{board_types}/add/')
            
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
            return redirect(f'/operator/{operator_slug}/{board_types}/')
        
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
            {'name': titles, 'url': f'/operator/{operator_slug}/{board_type_url}/'},
            {'name': f'Add {title}', 'url': f'/operator/{operator_slug}/{board_type_url}/add/'}
        ]

        tabs = generate_tabs("duties", operator)

        # Get routes for this operator for the generator
        operator_routes = route.objects.filter(route_operators=operator).values(
            'id', 'route_num', 'inbound_destination', 'outbound_destination', 'route_details'
        )

        circular_route_ids = set(
            timetableEntry.objects.filter(
                route_id__in=operator_routes.values('id'), circular=True
            ).values_list('route_id', flat=True)
        )

        routes_json = json.dumps([
            {
                'id': r['id'],
                'route_num': r['route_num'] or '',
                'inbound_destination': r['inbound_destination'] or '',
                'outbound_destination': r['outbound_destination'] or '',
                'colours': r['route_details'].get('colours', '') if r['route_details'] else '',
                'circular': r['id'] in circular_route_ids
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
            'board_type_url': board_type_url,
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
    
def parse_day_ids(raw_day_ids):
    day_ids = []
    for raw_day_id in raw_day_ids:
        for part in str(raw_day_id).split(','):
            try:
                day_ids.append(int(part))
            except (TypeError, ValueError):
                continue
    return list(dict.fromkeys(day_ids))


def normalize_stop_name(name):
    """
    Reduce a stop name for location comparison, ignoring stand/platform
    suffixes. "Wellington Bus Station (Stand D)" and "Wellington Bus Station
    (Stand F)" both reduce to "wellington bus station".
    """
    if not name:
        return ''
    cleaned = re.sub(r'\s*\([^)]*\)\s*$', '', str(name)).strip()
    return cleaned.casefold()


def build_vehicle_blocks_for_timetables(timetables, direction, rest_minutes=0, intertwine=False):
    """
    Return vehicle blocks calculated from a concrete set of timetable entries.
    rest_minutes is the minimum layover a vehicle must have between consecutive
    trips before it can take the next one.
    When intertwine is True, trips chain by their actual (normalized) stop
    locations so vehicles can share boards across different routes that serve
    the same stops. Otherwise logical 'home'/'far' locations are used.
    """
    all_trips = []
    seen_trips = set()

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
        route_id = tt.route_id
        route_num = getattr(tt.route, 'route_num', '') or ''
        
        # Skip if direction filter doesn't match
        if direction == 'inbound' and not is_inbound:
            continue
        if direction == 'outbound' and is_inbound:
            continue
        
        previous_start_mins = None
        for i, start_time in enumerate(first_times):
            # Skip empty strings and None values
            if not start_time or start_time.strip() == '':
                continue
            end_time = last_times[i] if i < len(last_times) else None
            if not end_time or end_time.strip() == '':
                continue
            
            # Create unique identifier for this trip
            trip_direction = 'inbound' if is_inbound else 'outbound'
            trip_key = f"{route_id}|{start_time}|{end_time}|{trip_direction}|{first_stop_name}|{last_stop_name}"
            
            # Skip if we've already seen this exact trip
            if trip_key in seen_trips:
                continue
            
            seen_trips.add(trip_key)
            start_minutes, end_minutes = normalize_trip_minutes(
                start_time,
                end_time,
                previous_start_mins,
            )
            if start_minutes is None or end_minutes is None:
                continue
            previous_start_mins = start_minutes
            
            # Use logical location: outbound ends at 'far', inbound ends at 'home'
            # This allows proper chaining regardless of actual stop names.
            # Circular routes loop back to their start, so they start and end at
            # 'home', letting a single vehicle chain consecutive loops.
            if intertwine:
                # Chain by actual (normalized) stop locations so trips from
                # different routes serving the same stops can share a vehicle.
                start_loc = normalize_stop_name(first_stop_name)
                end_loc = normalize_stop_name(last_stop_name)
            elif bool(tt.circular) or (tt.route_id and not getattr(tt.route, 'outbound_destination', None)):
                start_loc = 'home'
                end_loc = 'home'
            elif is_inbound:
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
                'route_id': route_id,
                'route_num': route_num,
                'start_minutes': start_minutes,
                'end_minutes': end_minutes,
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
    # Phase 1: location-based chaining (round trips). A vehicle is only given a trip when it
    # ends where that trip departs, so a duty naturally alternates inbound/outbound (the bus
    # arrives at a stop and leaves from the same stop) rather than deadhead running.
    # Phase 2: leftover single-direction boards are merged by estimating deadhead time back
    # to the start. This runs only AFTER all round trips are formed, so a same-direction
    # trip can never "steal" a vehicle that a proper out/in duty could have used.
    vehicles = []  # List of vehicle blocks, each is {'trips': [], 'end_minutes': int, 'end_location': str}
    
    # Auto-detect when every collected trip runs the same way (e.g. an outbound-only
    # service) so it gets deadhead treatment instead of per-trip boards.
    trip_directions = {t['direction'] for t in all_trips}
    single_direction_mode = direction in ['inbound', 'outbound'] or len(trip_directions) <= 1
    
    for trip in all_trips:
        assigned = False
        for v in vehicles:
            if v['end_minutes'] + rest_minutes <= trip['start_minutes']:
                if v['end_location'] == trip['start_location']:
                    v['trips'].append(trip)
                    v['end_minutes'] = trip['end_minutes']
                    v['end_location'] = trip['end_location']
                    assigned = True
                    break
        if not assigned:
            vehicles.append({
                'trips': [trip],
                'end_minutes': trip['end_minutes'],
                'end_location': trip['end_location']
            })
    
    # Phase 2: merge leftover boards onto earlier boards. A board can be merged when the
    # earlier board either ends where the merged board departs (round-trip continuation,
    # free) or runs the same direction and has enough time to deadhead back.
    changed = True
    while changed:
        changed = False
        for i, A in enumerate(vehicles):
            for j, B in enumerate(vehicles):
                if i == j or not A['trips'] or not B['trips']:
                    continue
                last_a = A['trips'][-1]
                first_b = B['trips'][0]
                if A['end_minutes'] + rest_minutes > first_b['start_minutes']:
                    continue
                if A['end_location'] == first_b['start_location']:
                    # Round-trip continuation - no deadhead needed
                    pass
                else:
                    # Deadhead merge - same direction only
                    if not single_direction_mode and last_a['direction'] != first_b['direction']:
                        continue
                    avail = A['end_minutes'] + (last_a['end_minutes'] - last_a['start_minutes'])
                    if avail + rest_minutes > first_b['start_minutes']:
                        continue
                A['trips'].extend(B['trips'])
                A['end_minutes'] = B['end_minutes']
                A['end_location'] = B['end_location']
                vehicles.pop(j)
                changed = True
                break
            if changed:
                break
    
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

    return result


def timetable_group_signature(timetables, direction, rest_minutes=0):
    """
    Build a stable signature from the actual timetable content, not entry ids.
    This lets separate Monday/Tuesday entries group together when their trips match.
    """
    blocks = build_vehicle_blocks_for_timetables(timetables, direction, rest_minutes)
    signature = []
    for block in blocks:
        trips = []
        for trip in block.get("trips", []):
            trips.append((
                trip.get("start_time"),
                trip.get("end_time"),
                trip.get("origin"),
                trip.get("destination"),
                trip.get("direction"),
            ))
        signature.append((
            block.get("start_time"),
            block.get("end_time"),
            tuple(trips),
        ))
    return tuple(signature), blocks


def _blocks_signature(blocks):
    sig = []
    for block in blocks:
        trips = []
        for trip in block.get("trips", []):
            trips.append((
                trip.get("start_time"),
                trip.get("end_time"),
                trip.get("origin"),
                trip.get("destination"),
                trip.get("direction"),
                trip.get("route_id"),
            ))
        sig.append((
            block.get("start_time"),
            block.get("end_time"),
            tuple(trips),
        ))
    return tuple(sig)


def annotate_blocks(blocks):
    """Add route_ids, route_nums and intertwined flags to vehicle blocks."""
    for block in blocks:
        route_ids = []
        route_nums = []
        seen_ids = set()
        for trip in block.get("trips", []):
            rid = trip.get("route_id")
            if rid not in seen_ids:
                seen_ids.add(rid)
                if rid:
                    route_ids.append(rid)
                rn = trip.get("route_num")
                if rn:
                    route_nums.append(rn)
        block["route_ids"] = route_ids
        block["route_nums"] = route_nums
        block["intertwined"] = len(route_ids) > 1
    return blocks


def route_intertwine_groups(timetables, direction):
    """
    Partition route ids into groups whose trips can actually be intertwined.
    Two routes can share a vehicle when trips on one end at the same
    (normalized) stop where trips on the other start. Routes that share no
    terminal stops are left in their own single-route group so they are built
    normally instead of producing lots of single-trip running boards.
    """
    starts = defaultdict(set)  # route_id -> normalized start stops
    ends = defaultdict(set)    # route_id -> normalized end stops
    for tt in timetables:
        if direction == 'inbound' and not tt.inbound:
            continue
        if direction == 'outbound' and tt.inbound:
            continue
        stop_times = tt.stop_times
        if isinstance(stop_times, str):
            try:
                stop_times = json.loads(stop_times)
            except (json.JSONDecodeError, TypeError):
                continue
        if not isinstance(stop_times, dict):
            continue
        sorted_stops = sorted(
            stop_times.items(),
            key=lambda x: x[1].get('order', 0) if isinstance(x[1], dict) else 0,
        )
        if len(sorted_stops) < 2:
            continue
        first = sorted_stops[0][1]
        last = sorted_stops[-1][1]
        if not isinstance(first, dict) or not isinstance(last, dict):
            continue
        rid = tt.route_id
        starts[rid].add(normalize_stop_name(first.get('stopname', '')))
        ends[rid].add(normalize_stop_name(last.get('stopname', '')))

    if not starts:
        return []

    # Union-find over routes sharing a terminal stop
    route_ids = list(starts.keys())
    parent = {rid: rid for rid in route_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i, a in enumerate(route_ids):
        for b in route_ids[i + 1:]:
            if ends[a] & starts[b] or ends[b] & starts[a]:
                union(a, b)

    groups = defaultdict(list)
    for rid in route_ids:
        groups[find(rid)].append(rid)
    return list(groups.values())


def build_intertwined_blocks(timetables, direction, rest_minutes):
    """
    Build vehicle blocks across multiple routes, intertwining only the routes
    that genuinely share terminal stops. Routes that cannot intertwine are
    built per-route as normal. Returns (blocks, intertwined_any).
    """
    groups = route_intertwine_groups(timetables, direction)
    blocks = []
    intertwined_any = False
    for group in groups:
        group_timetables = [tt for tt in timetables if tt.route_id in group]
        can_intertwine = len(group) > 1
        if can_intertwine:
            intertwined_any = True
        blocks += build_vehicle_blocks_for_timetables(
            group_timetables, direction, rest_minutes, intertwine=can_intertwine,
        )
    return blocks, intertwined_any


def compute_multi_route_blocks(route_ids, direction, rest_minutes, intertwine, selected_day_ids):
    routes = route.objects.filter(pk__in=route_ids)
    timetables = (
        timetableEntry.objects
        .filter(route__in=routes, active=True)
        .select_related('route')
        .prefetch_related('day_type')
        .order_by('id')
    )

    if not selected_day_ids:
        if intertwine:
            blocks, _ = build_intertwined_blocks(
                list(timetables), direction, rest_minutes,
            )
        else:
            blocks = []
            for r in routes:
                blocks += build_vehicle_blocks_for_timetables(
                    list(timetables.filter(route=r)), direction, rest_minutes,
                )
        return blocks

    selected_days = list(dayType.objects.filter(id__in=selected_day_ids).order_by('id'))
    day_names_by_id = {day.id: day.name for day in selected_days}

    groups = OrderedDict()
    for day_id in selected_day_ids:
        day_timetables = [
            tt for tt in timetables
            if any(day.id == day_id for day in tt.day_type.all())
            and not (direction == 'inbound' and not tt.inbound)
            and not (direction == 'outbound' and tt.inbound)
        ]
        if not day_timetables:
            continue

        if intertwine:
            blocks, _ = build_intertwined_blocks(
                day_timetables, direction, rest_minutes,
            )
        else:
            blocks = []
            for r in routes:
                rt_timetables = [tt for tt in day_timetables if tt.route_id == r.id]
                if rt_timetables:
                    blocks += build_vehicle_blocks_for_timetables(
                        rt_timetables, direction, rest_minutes,
                    )

        group_key = _blocks_signature(blocks)
        if group_key not in groups:
            groups[group_key] = {
                "day_ids": [],
                "day_names": [],
                "blocks": blocks,
            }
        groups[group_key]["day_ids"].append(day_id)
        groups[group_key]["day_names"].append(day_names_by_id.get(day_id, str(day_id)))

    result = []
    for group_index, group in enumerate(groups.values(), start=1):
        for block in group["blocks"]:
            block = block.copy()
            block["days"] = group["day_ids"]
            block["day_names"] = group["day_names"]
            block["timetable_group_id"] = f"timetable-{group_index}"
            result.append(block)

    result.sort(key=lambda x: (
        min(x.get("days", [99]) or [99]),
        time_to_minutes(x["start_time"]),
        x.get("vehicle_num", 0),
    ))
    return result


def get_timetable_trips(request, route_id):
    """
    Return vehicle blocks calculated from timetable entries.
    When day ids are supplied, blocks are grouped by the timetables that run on
    those days so mixed timetable selections create boards for the correct days.
    """
    direction = request.GET.get('direction', 'both')
    selected_day_ids = parse_day_ids(request.GET.getlist('days'))
    try:
        rest_minutes = max(0, int(request.GET.get('rest_minutes', '0') or 0))
    except (TypeError, ValueError):
        rest_minutes = 0

    r = route.objects.filter(pk=route_id).first()
    if not r:
        return JsonResponse({"error": "Route not found", "trips": []}, status=400)

    result = compute_multi_route_blocks([route_id], direction, rest_minutes, False, selected_day_ids)
    annotate_blocks(result)
    return JsonResponse({"trips": result, "vehicle_count": len(result)})


def get_routes_timetable_trips(request):
    """
    Return vehicle blocks for multiple routes at once, optionally intertwining
    boards across routes that share the same start/end stops.
    Query params: routes=1,2,3 direction=both days=... rest_minutes=N intertwine=1
    """
    raw_routes = request.GET.getlist('routes')
    if not raw_routes:
        return JsonResponse({"error": "No routes supplied", "trips": []}, status=400)

    route_ids = []
    for raw in raw_routes:
        for part in str(raw).split(','):
            try:
                route_ids.append(int(part))
            except (TypeError, ValueError):
                continue
    route_ids = list(dict.fromkeys(route_ids))
    if not route_ids:
        return JsonResponse({"error": "No valid routes supplied", "trips": []}, status=400)

    if not route.objects.filter(pk__in=route_ids).exists():
        return JsonResponse({"error": "Routes not found", "trips": []}, status=400)

    direction = request.GET.get('direction', 'both')
    selected_day_ids = parse_day_ids(request.GET.getlist('days'))
    try:
        rest_minutes = max(0, int(request.GET.get('rest_minutes', '0') or 0))
    except (TypeError, ValueError):
        rest_minutes = 0
    intertwine = request.GET.get('intertwine') == '1'

    result = compute_multi_route_blocks(route_ids, direction, rest_minutes, intertwine, selected_day_ids)
    annotate_blocks(result)
    return JsonResponse({"trips": result, "vehicle_count": len(result)})

def time_to_minutes(time_str):
    """Convert HH:MM to minutes since midnight."""
    try:
        parts = time_str.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, AttributeError, IndexError):
        return 0


def normalize_trip_minutes(start_time, end_time, previous_start_minutes=None):
    """
    Convert timetable display times into monotonic minutes for blocking.
    Timetables can wrap after midnight, so 00:27 after a 20:20 departure must
    compare as next day rather than the start of the same day.
    """
    try:
        start_minutes = time_to_minutes(start_time)
        end_minutes = time_to_minutes(end_time)
    except Exception:
        return None, None

    if previous_start_minutes is not None:
        while start_minutes < previous_start_minutes:
            start_minutes += 24 * 60

    while end_minutes < start_minutes:
        end_minutes += 24 * 60

    return start_minutes, end_minutes


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
        trip_route = selected_route
        trip_route_id = trip.get('route_id')
        if trip_route_id and int(trip_route_id) != selected_route.id:
            trip_route = route.objects.filter(id=trip_route_id).first() or selected_route
        trip_route_num = trip.get('route_num') or trip_route.route_num
        dutyTrip.objects.create(
            duty=duty_instance,
            route=trip_route_num,
            route_link=trip_route,
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

        inbound_entry = timetableEntry.objects.filter(route=r, inbound=True, active=True).first()
        outbound_entry = timetableEntry.objects.filter(route=r, inbound=False, active=True).first()

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

    board_type_url = board_type.replace('duty', 'duties')
    
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
        return redirect(f'/operator/{operator_slug}/{board_type_url}/')

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
        return redirect(f'/operator/{operator_slug}/{board_type_url}/')

    else:
        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
            {'name': titles, 'url': f'/operator/{operator_slug}/{board_type_url}/'},
            {'name': duty_instance.duty_name, 'url': f'/operator/{operator_slug}/{board_type_url}/{duty_id}/'},
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

    board_type_url = board_type.replace('duty', 'duties')

    if request.user != operator.owner and 'Edit Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, f"You do not have permission to edit this {title} for this operator.")
        return redirect(f'/operator/{operator_slug}/{board_type_url}/')

    trips = dutyTrip.objects.filter(duty=duty_instance)
    for trip in trips:
        trip.inbound = not trip.inbound
        trip.save()

    messages.success(request, f"Flipped directions for all trips on {title} '{duty_instance.duty_name}'.")
    return redirect(f'/operator/{operator_slug}/{board_type_url}/edit/{duty_instance.id}/trips/')

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

    board_type_url = board_type.replace('duty', 'duties')
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)
    duty_instance = get_object_or_404(duty, id=duty_id, duty_operator=operator)

    if request.user != operator.owner and 'Delete Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, f"You do not have permission to delete this {title}.")
        return redirect(f'/operator/{operator_slug}/{board_type_url}/')

    duty_instance.delete()
    messages.success(request, f"Deleted {title} '{duty_instance.duty_name}'.")
    return redirect(f'/operator/{operator_slug}/{board_type_url}/')

@login_required
@require_http_methods(["POST"])
def duty_mass_delete(request, operator_slug):
    response = feature_enabled(request, "delete_boards")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Delete Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete running boards.")
        return redirect(f'/operator/{operator_slug}/running-boards/')

    raw_ids = request.POST.get('duty_ids', '')
    ids = [i for i in raw_ids.split(',') if i.strip().isdigit()]

    deleted_info = duty.objects.filter(
        id__in=ids, duty_operator=operator, board_type='running-boards'
    ).delete()
    count = deleted_info[1].get('routes.duty', 0)

    messages.success(request, f"Deleted {count} running board(s) and their trips.")
    return redirect(f'/operator/{operator_slug}/running-boards/')

@login_required
@require_http_methods(["POST"])
def duty_mass_move(request, operator_slug):
    response = feature_enabled(request, "edit_boards")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to move running boards.")
        return redirect(f'/operator/{operator_slug}/running-boards/')

    raw_ids = request.POST.get('duty_ids', '')
    ids = [i for i in raw_ids.split(',') if i.strip().isdigit()]

    category = None
    if request.POST.get('category_id'):
        category = board_category.objects.filter(
            id=request.POST.get('category_id'), operator=operator, board_type='running-boards'
        ).first()
        if not category:
            messages.error(request, "The selected category does not exist for this operator.")
            return redirect(f'/operator/{operator_slug}/running-boards/')

    boards = duty.objects.filter(
        id__in=ids, duty_operator=operator, board_type='running-boards'
    )
    count = boards.count()
    if count == 0:
        messages.error(request, "No running boards were selected.")
        return redirect(f'/operator/{operator_slug}/running-boards/')

    boards.update(category=category)
    messages.success(request, f"Moved {count} running board(s).")
    return redirect(f'/operator/{operator_slug}/running-boards/')

@login_required
@require_http_methods(["POST"])
def duty_mass_transfer(request, operator_slug):
    response = feature_enabled(request, "edit_boards")
    if response:
        return response

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to transfer running boards.")
        return redirect(f'/operator/{operator_slug}/running-boards/')

    raw_ids = request.POST.get('duty_ids', '')
    ids = [i for i in raw_ids.split(',') if i.strip().isdigit()]

    target_operator = None
    if request.POST.get('target_operator_id'):
        target_operator = MBTOperator.objects.filter(id=request.POST.get('target_operator_id')).first()

    if not target_operator:
        messages.error(request, "Please choose an operator to transfer the selected running board(s) to.")
        return redirect(f'/operator/{operator_slug}/running-boards/')

    # The user must be a helper (or owner) of the target operator
    helper_op_ids = set(
        helper.objects.filter(helper=request.user).values_list('operator_id', flat=True)
    )
    if (
        request.user != target_operator.owner
        and target_operator.id not in helper_op_ids
        and not request.user.is_superuser
    ):
        messages.error(request, f"You are not a helper on {target_operator.operator_name}, so you cannot transfer running boards to it.")
        return redirect(f'/operator/{operator_slug}/running-boards/')

    boards = duty.objects.filter(
        id__in=ids, duty_operator=operator, board_type='running-boards'
    )
    count = boards.count()
    if count == 0:
        messages.error(request, "No running boards were selected.")
        return redirect(f'/operator/{operator_slug}/running-boards/')

    boards.update(duty_operator=target_operator, category=None)
    messages.success(request, f"Transferred {count} running board(s) to {target_operator.operator_name}.")
    return redirect(f'/operator/{operator_slug}/running-boards/')

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
    board_type_url = board_type.replace('duty', 'duties')

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)
    duty_instance = get_object_or_404(duty, id=duty_id, duty_operator=operator)

    if request.user != operator.owner and 'Edit Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, f"You do not have permission to edit this {title} for this operator.")
        return redirect(f'/operator/{operator_slug}/{board_type_url}/')

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
        return redirect(f'/operator/{operator_slug}/{board_type_url}/')

    else:
        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
            {'name': titles, 'url': f'/operator/{operator_slug}/{board_type_url}/'},
            {'name': f"Edit {duty_instance.duty_name}", 'url': f'/operator/{operator_slug}/{board_type_url}/edit/{duty_instance.id}/'}
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
            'board_type_url': board_type_url,
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
    board_type_url = board_type.replace('duty', 'duties')
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
        {'name': titles, 'url': f'/operator/{operator_slug}/{board_type_url}/'},
        {'name': 'Categories', 'url': f'/operator/{operator_slug}/{board_type_url}/categories/'}
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
        'board_type_url': board_type_url,
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
    board_type_url = board_type.replace('duty', 'duties')
    title = "Running Board" if is_running_board else "Duty"
    titles = "Running Boards" if is_running_board else "Duties"

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add categories for this operator.")
        return redirect(f'/operator/{operator_slug}/{board_type_url}/categories/')

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
        return redirect(f'/operator/{operator_slug}/{board_type_url}/categories/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': titles, 'url': f'/operator/{operator_slug}/{board_type_url}/'},
        {'name': 'Categories', 'url': f'/operator/{operator_slug}/{board_type_url}/categories/'},
        {'name': 'Add Category', 'url': f'/operator/{operator_slug}/{board_type_url}/categories/add/'}
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
        'board_type_url': board_type_url,
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
    board_type_url = board_type.replace('duty', 'duties')
    title = "Running Board" if is_running_board else "Duty"
    titles = "Running Boards" if is_running_board else "Duties"

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    category_instance = get_object_or_404(board_category, id=category_id, operator=operator)
    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit categories for this operator.")
        return redirect(f'/operator/{operator_slug}/{board_type_url}/categories/')

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
        return redirect(f'/operator/{operator_slug}/{board_type_url}/categories/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator.operator_name, 'url': f'/operator/{operator_slug}/'},
        {'name': titles, 'url': f'/operator/{operator_slug}/{board_type_url}/'},
        {'name': 'Categories', 'url': f'/operator/{operator_slug}/{board_type_url}/categories/'},
        {'name': f'Edit {category_instance.name}', 'url': f'/operator/{operator_slug}/{board_type_url}/categories/edit/{category_id}/'}
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
        'board_type_url': board_type_url,
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
    board_type_url = board_type.replace('duty', 'duties')

    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    category_instance = get_object_or_404(board_category, id=category_id, operator=operator)
    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Duties' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete categories for this operator.")
        return redirect(f'/operator/{operator_slug}/{board_type_url}/categories/')

    if request.method == "POST":
        # Clear category from any duties that use it
        duty.objects.filter(category=category_instance).update(category=None)
        category_instance.delete()
        messages.success(request, "Category deleted successfully.")
        return redirect(f'/operator/{operator_slug}/{board_type_url}/categories/')

    return redirect(f'/operator/{operator_slug}/{board_type_url}/categories/')

@login_required
@require_http_methods(["GET", "POST"])
def log_trip(request, operator_slug, vehicle_id):
    response = feature_enabled(request, "log_trips")
    if response:
        return response

    auto_return_expired_loans()

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
    except (AttributeError, ObjectDoesNotExist):
        current_map = 1

    mapTileSetAll = mapTileSet.available_to_user(request.user)

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
                mapTileSet_instance = mapTileSet.available_to_user(request.user).get(id=mapTile_id)
            except mapTileSet.DoesNotExist:
                mapTileSet_instance = mapTileSet.default_for_user(request.user)
                print(f"MapTileSet with ID {mapTile_id} does not exist.")
        else:
            mapTileSet_instance = mapTileSet.default_for_user(request.user)
            print("No mapTileSet ID provided in POST data.")

        original_operator_name = operator.operator_name
        original_operator_code = operator.operator_code

        new_operator_name = request.POST.get('operator_name', '').strip()
        new_operator_code = request.POST.get('operator_code', '').strip()

        blocked_words = operator_name_banned_words(new_operator_name)
        if blocked_words:
            messages.error(request, operator_name_banned_message(blocked_words))
            return redirect(f'/operator/{operator_slug}/edit/')

        reservation = reservedOperatorName.blocking_reservation_for_user(new_operator_name, request.user)
        if reservation:
            messages.error(request, reserved_operator_name_message(reservation))
            return redirect(f'/operator/{operator_slug}/edit/')

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
        op_pk = operator.pk
        op_name = operator.operator_name
        op_slug = operator.operator_slug
        username = request.user.username

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL statement_timeout = 0")
                    cursor.execute("SET LOCAL lock_timeout = '30s'")

                    cursor.execute(
                        "DELETE FROM routes_route_route_operators WHERE mbtoperator_id = %s",
                        [op_pk],
                    )

                    default_op = default_operator_id()
                    cursor.execute(
                        "UPDATE fleet_fleet SET operator_id = %s WHERE operator_id = %s",
                        [default_op.pk, op_pk],
                    )
                    cursor.execute(
                        "UPDATE fleet_fleet SET loan_operator_id = NULL WHERE loan_operator_id = %s",
                        [op_pk],
                    )
                    cursor.execute(
                        "UPDATE fleet_fleetchange SET operator_id = NULL WHERE operator_id = %s",
                        [op_pk],
                    )

                    cursor.execute(
                        "DELETE FROM routes_dutytrip WHERE duty_id IN (SELECT id FROM routes_duty WHERE duty_operator_id = %s)",
                        [op_pk],
                    )
                    cursor.execute(
                        "DELETE FROM routes_duty WHERE duty_operator_id = %s",
                        [op_pk],
                    )

                    if "fleet_depot" in connection.introspection.table_names():
                        cursor.execute(
                            "DELETE FROM fleet_depot WHERE operator_id = %s",
                            [op_pk],
                        )

                companyUpdate.objects.filter(operator_id=op_pk).delete()
                helper.objects.filter(operator_id=op_pk).delete()
                ticket.objects.filter(operator_id=op_pk).delete()
                board_category.objects.filter(operator_id=op_pk).delete()
                favouriteOperator.objects.filter(operator_id=op_pk).delete()

                operator.region.clear()
                operator.delete()

            messages.success(request, f"Operator '{op_slug}' has been deleted.")

            try:
                if count > 10:
                    send_to_discord_delete(count, settings.DISCORD_OPERATOR_LOGS_ID, op_name)
                send_to_discord_embed(
                    DISCORD_FULL_OPERATOR_LOGS_ID,
                    "Operator deleted",
                    f"**{op_name}** has been deleted by {username}.",
                    0xED4245,
                )
            except Exception:
                logger.warning(f"Operator {op_slug} deleted but Discord notification failed", exc_info=True)

        except Exception:
            logger.error(f"Failed to delete operator {op_slug}", exc_info=True)
            messages.error(request, f"Failed to delete operator '{op_slug}'. Please try again later.")

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
        vehicle.engine = request.POST.get('engine', '').strip()
        vehicle.gearbox = request.POST.get('gearbox', '').strip()
        vehicle.door_amount = request.POST.get('door_amount', '').strip()
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

        type_id = request.POST.get('type')
        if type_id:
            try:
                vehicle.vehicleType = vehicleType.objects.get(id=type_id)
            except vehicleType.DoesNotExist:
                vehicle.vehicleType = None
        else:
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

        type_lengths_map = {t.id: [l.strip() for l in t.lengths.split(',') if l.strip()] for t in types}
        type_engine_map = {t.id: [e.strip() for e in t.engine.split(',') if e.strip()] for t in types}
        type_gearbox_map = {t.id: [g.strip() for g in t.gearbox.split(',') if g.strip()] for t in types}
        type_door_map = {t.id: [d.strip() for d in t.door_amount.split(',') if d.strip()] for t in types}
        type_category_map = {t.id: t.type for t in types}
        type_fuel_map = {t.id: t.fuel for t in types}
        context = {
            'operator_current': operator,
            'fleetData': vehicle,
            'operatorData': operators,
            'typeData': types,
            'type_lengths_json': json.dumps(type_lengths_map),
            'type_engine_json': json.dumps(type_engine_map),
            'type_gearbox_json': json.dumps(type_gearbox_map),
            'type_door_json': json.dumps(type_door_map),
            'type_category_json': json.dumps(type_category_map),
            'type_fuel_json': json.dumps(type_fuel_map),
            'liveryData': liveries_list,
            'features': features_list,
            'userData': user_data,
            'breadcrumbs': breadcrumbs,
            'category_list': category_list,
            'tabs': tabs,
            'allowed_operators': allowed_operators,
        }
        add_favourite_select_context(context, request.user, liveries_list, types)
        return render(request, 'add.html', context)
    
@login_required
@require_http_methods(["GET", "POST"])
def vehicle_mass_add(request, operator_slug):
    rate_limit_window = timedelta(minutes=1)
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
            elapsed = now - last_add_time
            if elapsed < rate_limit_window:
                remaining = max(1, int(rate_limit_window.total_seconds() - elapsed.total_seconds()))
                messages.error(request, f'Rate limited. Try again in {remaining} seconds.')
                return redirect(reverse('mass_add_vehicles', args=[operator_slug]))

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
        engine = request.POST.get('engine', '').strip()
        gearbox = request.POST.get('gearbox', '').strip()
        door_amount = request.POST.get('door_amount', '').strip()
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

        type_id = request.POST.get('type')
        if type_id:
            try:
                type_fk = vehicleType.objects.get(id=type_id)
            except vehicleType.DoesNotExist:
                type_fk = None
        else:
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
            vehicle.engine = engine
            vehicle.gearbox = gearbox
            vehicle.door_amount = door_amount
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

        last_add = request.session.get('last_mass_add')
        rate_limit_remaining = 0
        if last_add:
            last_add_time = timezone.datetime.fromisoformat(last_add)
            elapsed = timezone.now() - last_add_time
            if elapsed < rate_limit_window:
                rate_limit_remaining = max(1, int(rate_limit_window.total_seconds() - elapsed.total_seconds()))

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

        type_lengths_map = {t.id: [l.strip() for l in t.lengths.split(',') if l.strip()] for t in types}
        type_engine_map = {t.id: [e.strip() for e in t.engine.split(',') if e.strip()] for t in types}
        type_gearbox_map = {t.id: [g.strip() for g in t.gearbox.split(',') if g.strip()] for t in types}
        type_door_map = {t.id: [d.strip() for d in t.door_amount.split(',') if d.strip()] for t in types}
        type_category_map = {t.id: t.type for t in types}
        type_fuel_map = {t.id: t.fuel for t in types}
        context = {
            'fleetData': vehicle,
            'operator_current': operator,
            'operatorData': allowed_operators,
            'typeData': types,
            'type_lengths_json': json.dumps(type_lengths_map),
            'type_engine_json': json.dumps(type_engine_map),
            'type_gearbox_json': json.dumps(type_gearbox_map),
            'type_door_json': json.dumps(type_door_map),
            'type_category_json': json.dumps(type_category_map),
            'type_fuel_json': json.dumps(type_fuel_map),
            'liveryData': liveries_list,
            'features': features_list,
            'userData': user_data,
            'breadcrumbs': breadcrumbs,
            'categoryData': category_list,
            'tabs': tabs,
            'mass_add_rate_limit_remaining': rate_limit_remaining,
        }
        add_favourite_select_context(context, request.user, liveries_list, types)
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

            if 'edit_in_service' in request.POST:
                vehicle.in_service = 'in_service' in request.POST
            if 'edit_preserved' in request.POST:
                vehicle.preserved = 'preserved' in request.POST
            if 'edit_open_top' in request.POST:
                vehicle.open_top = 'open_top' in request.POST
            if 'edit_for_sale' in request.POST:
                vehicle.for_sale = 'for_sale' in request.POST
            if 'edit_type_details' in request.POST:
                vehicle.type_details = request.POST.get('type_details', '').strip()
            if 'edit_length' in request.POST:
                vehicle.length = request.POST.get('length', '').strip() or None
            if 'edit_engine' in request.POST:
                vehicle.engine = request.POST.get('engine', '').strip()
            if 'edit_gearbox' in request.POST:
                vehicle.gearbox = request.POST.get('gearbox', '').strip()
            if 'edit_door_amount' in request.POST:
                vehicle.door_amount = request.POST.get('door_amount', '').strip()
            if 'edit_colour' in request.POST:
                vehicle.colour = request.POST.get('colour', '').strip()
            if 'edit_branding' in request.POST:
                vehicle.branding = request.POST.get('branding', '').strip()
            if 'edit_prev_reg' in request.POST:
                vehicle.prev_reg = request.POST.get('prev_reg', '').strip()
            if 'edit_depot' in request.POST:
                vehicle.depot = request.POST.get('depot', '').strip()
            if 'edit_name' in request.POST:
                vehicle.name = request.POST.get('name', '').strip()
            if 'edit_notes' in request.POST:
                vehicle.notes = request.POST.get('notes', '').strip()
            if 'edit_summary' in request.POST:
                vehicle.summary = request.POST.get('summary', '').strip()

            current_operator = vehicle.operator
            was_on_loan = (
                vehicle.loan_operator_id is not None
                and vehicle.loan_operator_id != vehicle.operator_id
            )
            loan_starting = False
            loan_returning = False

            # Foreign Keys
            if 'edit_operator' in request.POST:
                try:
                    vehicle.operator = MBTOperator.objects.get(id=request.POST.get('operator'))
                except MBTOperator.DoesNotExist:
                    pass

            if 'edit_loan_operator' in request.POST:
                loan_op = request.POST.get('loan_operator')
                if loan_op == "null" or not loan_op:
                    vehicle.loan_operator = None
                    vehicle.loan_until = None
                else:
                    try:
                        vehicle.loan_operator = MBTOperator.objects.get(id=loan_op)
                    except MBTOperator.DoesNotExist:
                        vehicle.loan_operator = None
                    loan_until_str = request.POST.get('loan_until', '').strip()
                    loan_until = None
                    if loan_until_str:
                        try:
                            loan_until = parse_datetime(loan_until_str)
                        except (ValueError, TypeError):
                            loan_until = None
                        if loan_until is not None and timezone.is_naive(loan_until):
                            loan_until = timezone.make_aware(loan_until)
                    vehicle.loan_until = loan_until

                loan_active = (
                    vehicle.loan_operator_id is not None
                    and vehicle.loan_operator_id != vehicle.operator_id
                )
                if loan_active and not was_on_loan and not vehicle.loan_snapshot:
                    loan_starting = True
                elif not loan_active and was_on_loan and vehicle.loan_snapshot:
                    loan_returning = True

            if 'edit_type' in request.POST:
                type_id = request.POST.get('type')
                if type_id:
                    try:
                        vehicle.vehicleType = vehicleType.objects.get(id=type_id)
                    except vehicleType.DoesNotExist:
                        vehicle.vehicleType = None
                else:
                    vehicle.vehicleType = None

            if 'edit_livery' in request.POST:
                try:
                    vehicle.livery = liverie.objects.get(id=request.POST.get('livery'))
                except liverie.DoesNotExist:
                    vehicle.livery = None

            # Vehicle category (shared field in the form) — ensure it belongs to the operator
            if 'edit_vehicle_category' in request.POST:
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

            if 'edit_features' in request.POST:
                try:
                    features_selected = json.loads(request.POST.get('features', '[]'))
                    vehicle.features = features_selected
                except json.JSONDecodeError:
                    pass

            if 'edit_custom' in request.POST:
                custom = request.POST.get('custom', '').strip()
                json_custom = {}
                for line in custom.splitlines():
                    match = re.match(r'^\s*"?(.+?)"?\s*[:=]\s*"?(.+?)"?\s*$', line)
                    if match:
                        key, value = match.groups()
                        json_custom[key.strip()] = value.strip()
                vehicle.advanced_details = json_custom

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

                    if total_for_sale > max_for_sale:
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

                    if loan_starting:
                        vehicle.loan_snapshot = capture_loan_snapshot(vehicle)
                    elif loan_returning:
                        restore_loan_snapshot(vehicle, vehicle.loan_snapshot)
                        vehicle.loan_snapshot = None
                        vehicle.loan_operator = None
                        vehicle.loan_until = None

                    vehicle.save()

                    operator = MBTOperator.objects.get(id=operator.id)
                    for_sale_count = fleet.objects.filter(operator=operator, for_sale=True).count()
                    operator.vehicles_for_sale = for_sale_count
                    operator.save()

                    updated_count += 1
                else:
                    if loan_starting:
                        vehicle.loan_snapshot = capture_loan_snapshot(vehicle)
                    elif loan_returning:
                        restore_loan_snapshot(vehicle, vehicle.loan_snapshot)
                        vehicle.loan_snapshot = None
                        vehicle.loan_operator = None
                        vehicle.loan_until = None
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

        type_lengths_map = {t.id: [l.strip() for l in t.lengths.split(',') if l.strip()] for t in types}
        type_engine_map = {t.id: [e.strip() for e in t.engine.split(',') if e.strip()] for t in types}
        type_gearbox_map = {t.id: [g.strip() for g in t.gearbox.split(',') if g.strip()] for t in types}
        type_door_map = {t.id: [d.strip() for d in t.door_amount.split(',') if d.strip()] for t in types}
        type_category_map = {t.id: t.type for t in types}
        type_fuel_map = {t.id: t.fuel for t in types}
        context = {
            'hide_sell_button': hide_sell_button,
            'fleetData': vehicles[0],  # Used for shared fields
            'vehicles': vehicles,
            'operatorData': allowed_operators,
            'typeData': types,
            'type_lengths_json': json.dumps(type_lengths_map),
            'type_engine_json': json.dumps(type_engine_map),
            'type_gearbox_json': json.dumps(type_gearbox_map),
            'type_door_json': json.dumps(type_door_map),
            'type_category_json': json.dumps(type_category_map),
            'type_fuel_json': json.dumps(type_fuel_map),
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
        add_favourite_select_context(context, request.user, liveries_list, types)
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
        apply_route_status = request.POST.get('apply_route_status') == 'on'
        apply_depot = request.POST.get('apply_depot') == 'on'

        if not any([
            apply_text_colour,
            apply_background_colour,
            apply_linked_routes,
            apply_related_routes,
            apply_route_operators,
            apply_payment_methods,
            apply_route_status,
            apply_depot,
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
        route_depot = request.POST.get('route_depot', '').strip()

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

                if apply_route_status:
                    details['school_service'] = str(school_service).lower()

                route_details['details'] = details
                route_instance.route_details = route_details

                if apply_route_status:
                    route_instance.hidden = hidden

                if apply_depot:
                    route_instance.route_depot = route_depot

                route_instance.save(update_fields=['route_details', 'hidden', 'route_depot'])

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
    mapTileSetAll = mapTileSet.available_to_user(request.user)

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

        blocked_words = operator_name_banned_words(operator_name)
        if blocked_words:
            return render(request, 'create_operator.html', {
                'error': 'operator_name_banned',
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
                'blockedWords': sorted(set(blocked_words)),
                'groups': groups,
                'organisations': organisations,
                'operatorTypeData': operator_types,
                'gameData': games,
                'regionData': regionData,
                'mapTileSets': mapTileSetAll,
            })

        reservation = reservedOperatorName.blocking_reservation_for_user(operator_name, request.user)
        if reservation:
            return render(request, 'create_operator.html', {
                'error': 'operator_name_reserved',
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
                'reservedOperatorName': reservation.operator_name,
                'reservedOperatorNameMessage': reserved_operator_name_message(reservation),
                'groups': groups,
                'organisations': organisations,
                'operatorTypeData': operator_types,
                'gameData': games,
                'regionData': regionData,
                'mapTileSets': mapTileSetAll,
            })

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
                'mapTileSets': mapTileSetAll,
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
                'mapTileSets': mapTileSetAll,
            })

        operator_group = group.objects.filter(id=operator_group_id).first() if operator_group_id else None
        operator_org = organisation.objects.filter(id=operator_org_id).first() if operator_org_id else None
        mapTileSet_selected = mapTileSet.available_to_user(request.user).filter(id=mapTile_id).first() if mapTile_id else mapTileSet.default_for_user(request.user)
        if mapTileSet_selected is None:
            mapTileSet_selected = mapTileSet.default_for_user(request.user)

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
        timetable_id = request.POST.get("timetable_id")
        timetable_instance = get_object_or_404(timetableEntry, id=timetable_id, route=route_instance)
        timetable_instance.active = request.POST.get("active") == "on"
        timetable_instance.save(update_fields=["active"])
        status = "active" if timetable_instance.active else "inactive"
        messages.success(request, f"Timetable marked as {status}.")
        return redirect(request.path)

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
    mapTiles = operator.mapTile if operator.mapTile and operator.mapTile.is_available_to_user(request.user) else mapTileSet.default_for_user(request.user)
    route_instance = get_object_or_404(route, id=route_id)

    userPerms = get_helper_permissions(request.user, operator)

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
                except (ValueError, TypeError):
                    parsed_snapped = None
            else:
                parsed_snapped = None

            # Save everything
            routeStop.objects.filter(
                route=route_instance,
                inbound=(direction == "inbound")
            ).delete()
            routeStop.objects.create(
                route=route_instance,
                inbound=(direction == "inbound"),
                circular=False,
                stops=parsed_stops,
                snapped_route=parsed_snapped,
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
        'mapTileSets': mapTileSet.available_to_user(request.user).order_by('name'),
        'existing_stops': existing_stops,  # Pass existing stops here
        'existing_snapped': existing_snapped,  # Pass existing snapped geometry here
    }
    return render(request, 'route_edit_route.html', context)

@login_required
@require_POST
@csrf_exempt
def valhalla_proxy(request):
    url = settings.ROUTEING_URL
    headers = {"Content-Type": "application/json"}

    valhalla_user = getattr(settings, "VALHALLA_USER", None)
    valhalla_pass = getattr(settings, "VALHALLA_PASS", None)
    auth = (valhalla_user, valhalla_pass) if valhalla_user and valhalla_pass else None

    try:
        r = http_post(url, data=request.body, headers=headers, auth=auth, timeout=30)
    except Exception as e:
        return JsonResponse({"error": f"Proxy request failed: {e}"}, status=500)

    try:
        return JsonResponse(r.json(), safe=False, status=r.status_code)
    except ValueError:
        return HttpResponse(r.text, status=r.status_code)


def orr_proxy(request):
    url = settings.ORR_URL
    headers = {"Content-Type": "application/json"}

    try:
        r = http_post(url, data=request.body, headers=headers, timeout=30)
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
    mapTiles = operator.mapTile if operator.mapTile and operator.mapTile.is_available_to_user(request.user) else mapTileSet.default_for_user(request.user)
    route_instance = get_object_or_404(route, id=route_id)

    userPerms = get_helper_permissions(request.user, operator)

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
        'mapTileSets': mapTileSet.available_to_user(request.user).order_by('name'),
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
            res = http_get(timetable_url, headers=headers)
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
                times = [
                    normalize_timetable_time_value(td.get_text(" ", strip=True))
                    for td in row.find_all("td")
                ]

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
                    normalize_timetable_time_value(t.strip().strip('"').strip("'"))
                    for t in raw_times.split(",")
                    if t.strip()
                ]
                arrival_times = [
                    normalize_timetable_time_value(t.strip().strip('"').strip("'"))
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
            timetable_instance.active = request.POST.get("active") == "on"
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
            http_post(webhook_url, json=message, timeout=5)
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

    if request.method == 'POST':
        action = request.POST.get('action')
        request_id = request.POST.get('request_id')
        change_request = get_object_or_404(VehicleTypeChangeRequest, id=request_id)

        if change_request.status != 'pending':
            messages.error(request, "This request has already been reviewed.")
            return redirect('/operator/vehicle-types/admin/')

        change_request.reviewed_by = request.user
        change_request.reviewed_at = timezone.now()

        if action == 'disapprove':
            change_request.status = 'disapproved'
            change_request.disapproved_reason = request.POST.get('disapproved_reason', '').strip()
            change_request.save()
            messages.success(request, "Request disapproved.")
            return redirect('/operator/vehicle-types/admin/')

        if action == 'approve':
            if change_request.request_type == 'edit':
                type_obj = change_request.vehicle_type
                if not type_obj:
                    messages.error(request, "Vehicle type no longer exists.")
                    return redirect('/operator/vehicle-types/admin/')

                for field, change in (change_request.proposed_changes or {}).items():
                    setattr(type_obj, field, _clamp_vehicle_type_value(field, change.get('new')))
                if change_request.evidence:
                    type_obj.evidence = change_request.evidence
                type_obj.save()

                change_request.status = 'approved'
                change_request.save()
                messages.success(request, "Edit request approved.")
                return redirect('/operator/vehicle-types/admin/')

            if change_request.request_type == 'delete':
                type_obj = change_request.vehicle_type
                if not type_obj:
                    messages.error(request, "Vehicle type no longer exists.")
                    return redirect('/operator/vehicle-types/admin/')

                replacement_type = change_request.replacement_type
                in_use_count = fleet.objects.filter(vehicleType=type_obj).count()

                if in_use_count > 0 and not replacement_type:
                    messages.error(request, "A replacement type is required before deletion.")
                    return redirect('/operator/vehicle-types/admin/')

                if replacement_type and VehicleTypeChangeRequest.objects.filter(
                    vehicle_type=replacement_type,
                    request_type='delete',
                    status='pending'
                ).exists():
                    messages.error(request, "Replacement type has a pending delete request.")
                    return redirect('/operator/vehicle-types/admin/')

                if replacement_type:
                    fleet.objects.filter(vehicleType=type_obj).update(vehicleType=replacement_type)

                change_request.status = 'approved'
                change_request.save()
                type_obj.delete()
                messages.success(request, "Delete request approved.")
                return redirect('/operator/vehicle-types/admin/')

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

        if action in ['edit', 'delete'] and is_feature_banned(request.user, 'vehicle_type_changes'):
            return redirect('vehicle_type_banned')

        if action == 'edit':
            proposed = {}
            text_fields = ['type_name', 'type', 'fuel', 'lengths', 'engine', 'gearbox', 'door_amount']
            bool_fields = ['double_decker', 'active', 'hidden']
            required_fields = ['type_name', 'type', 'fuel']
            evidence = request.POST.get('evidence', '').strip()

            if not request.user.is_superuser and not is_valid_evidence_url(evidence):
                messages.error(request, "Evidence must be a valid URL (e.g. https://www.example.com or https://example.co.uk).")
                return redirect(f'/operator/vehicle-types/{vehicle_type.id}/')

            for field in text_fields:
                new_value = request.POST.get(field, '').strip()
                old_value = getattr(vehicle_type, field) or ''
                if field in required_fields and new_value == '' and old_value != '':
                    messages.error(request, f"{field.replace('_', ' ').title()} cannot be blank.")
                    return redirect(f'/operator/vehicle-types/{vehicle_type.id}/')
                max_length = VEHICLE_TYPE_TEXT_MAX_LENGTH.get(field)
                if max_length and len(new_value) > max_length:
                    messages.error(request, f"{field.replace('_', ' ').title()} is limited to {max_length} characters")
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
                evidence=evidence,
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
                    setattr(type_obj, field, _clamp_vehicle_type_value(field, change.get('new')))
                if change_request.evidence:
                    type_obj.evidence = change_request.evidence
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

    type_choices = list(vehicleType.objects.values_list('type', flat=True).distinct().order_by('type'))
    fuel_choices = list(vehicleType.objects.values_list('fuel', flat=True).distinct().order_by('fuel'))
    engine_choices = list(vehicleType.objects.exclude(engine='').values_list('engine', flat=True).distinct().order_by('engine'))
    gearbox_choices = list(vehicleType.objects.exclude(gearbox='').values_list('gearbox', flat=True).distinct().order_by('gearbox'))
    door_amount_choices = list(vehicleType.objects.exclude(door_amount='').values_list('door_amount', flat=True).distinct().order_by('door_amount'))

    context = {
        'breadcrumbs': breadcrumbs,
        'vehicle_type': vehicle_type,
        'pending_requests': pending_requests,
        'all_requests': all_requests,
        'replacement_options': replacement_options,
        'vehicle_count': vehicle_count,
        'pending_delete_exists': pending_delete_exists,
        'vehicle_type_changes_banned': is_feature_banned(request.user, 'vehicle_type_changes'),
        'type_choices': type_choices,
        'fuel_choices': fuel_choices,
        'engine_choices': engine_choices,
        'gearbox_choices': gearbox_choices,
        'door_amount_choices': door_amount_choices,
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

    auto_return_expired_loans()

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

        cutoff_date = loan_log_cutoff_date(vehicle)

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

            if cutoff_date is not None and current_start.date() > cutoff_date:
                messages.error(
                    request,
                    f"This vehicle is on loan and can only be logged up to {cutoff_date.isoformat()} (the day before it is due back).",
                )
                return redirect(request.path)

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

        if cutoff_date is not None and selected_date > cutoff_date:
            messages.error(
                request,
                f"This vehicle is on loan and can only be logged up to {cutoff_date.isoformat()} (the day before it is due back).",
            )
            return redirect(request.path)

        board_obj = selected_duty if duty_id else selected_rb
        if running_board_id and not running_board_runs_on_date(board_obj, selected_date):
            messages.error(request, running_board_day_error(board_obj, selected_date))
            return redirect(request.path)
        if running_board_id and not running_board_active_on_date(board_obj, selected_date):
            messages.error(request, running_board_active_error(board_obj, selected_date))
            return redirect(request.path)

        trip_set = trip_set.order_by('id')

        has_trips = trip_set.exists()

        if not has_trips:
            messages.error(request, "Selected duty or running board has no trips defined.")
            return redirect(request.path)

        for trip, start_dt, end_dt in build_board_trip_windows(trip_set, selected_date):
            routeLink = trip.route_link if trip.route_link else None

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
    current_date = timezone.localdate()
    running_boards = duty.objects.filter(
        duty_operator=operator,
        board_type='running-boards',
        duty_day__name=current_date.strftime("%A"),
    ).distinct().order_by('duty_name')
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
        'current_date': current_date.strftime("%Y-%m-%d"),
        'current_date_time': timezone.now().strftime("%Y-%m-%d %H:%M"),
    }
    return render(request, 'mass-log-trips.html', context)

def _can_mass_log_for_operator(user, operator):
    user_perms = get_helper_permissions(user, operator)
    return user == operator.owner or 'Mass Log Trips' in user_perms or user.is_superuser


def build_board_trip_windows(board_trips, selected_date):
    """
    Build aware start/end datetimes for a duty/running-board trip list.
    Times after a midnight rollover belong to the following service date.

    Trips are ordered chronologically regardless of storage order (duty trips
    may be stored out of time order), then rotated around the largest gap
    between consecutive start times so the "first trip of the day" is found.
    Only trips that genuinely cross midnight then roll into the next day.
    """
    trips = sorted(board_trips, key=lambda t: t.start_time)

    if not trips:
        return []

    # Find the largest circular gap between consecutive trip start times.
    # The trip immediately after that gap is the first trip of the day.
    n = len(trips)
    if n > 1:
        minutes = [t.start_time.hour * 60 + t.start_time.minute for t in trips]
        largest_gap = -1
        rotate_by = 0
        for i in range(n):
            gap = (minutes[(i + 1) % n] - minutes[i]) % (24 * 60)
            if gap > largest_gap:
                largest_gap = gap
                rotate_by = (i + 1) % n
        if rotate_by:
            trips = trips[rotate_by:] + trips[:rotate_by]

    trip_windows = []
    day_offset = timedelta(days=0)
    previous_start_time = None

    for trip in trips:
        if previous_start_time is not None and trip.start_time < previous_start_time:
            day_offset += timedelta(days=1)

        start_date = selected_date + day_offset
        end_date = start_date
        if trip.end_time <= trip.start_time:
            end_date += timedelta(days=1)

        start_dt = make_aware(datetime.combine(start_date, trip.start_time))
        end_dt = make_aware(datetime.combine(end_date, trip.end_time))

        trip_windows.append((trip, start_dt, end_dt))
        previous_start_time = trip.start_time

    return trip_windows


def running_board_runs_on_date(board_obj, service_date):
    if board_obj.board_type != "running-boards":
        return True
    return board_obj.duty_day.filter(name=service_date.strftime("%A")).exists()


def running_board_active_on_date(board_obj, service_date):
    """A running board is inactive while its no-run period covers the date."""
    if board_obj.board_type != "running-boards":
        return True
    if board_obj.no_run_start and board_obj.no_run_end:
        return not (board_obj.no_run_start <= service_date <= board_obj.no_run_end)
    return True


def running_board_active_error(board_obj, service_date):
    period = f"{board_obj.no_run_start.isoformat()} to {board_obj.no_run_end.isoformat()}"
    return f"{board_obj.duty_name} cannot be mass logged on {service_date.isoformat()}; it has a no-run period of {period}."


def running_board_day_error(board_obj, service_date):
    day_names = list(board_obj.duty_day.order_by("id").values_list("name", flat=True))
    listed_days = ", ".join(day_names) if day_names else "no days"
    return f"{board_obj.duty_name} cannot be assigned on {service_date.strftime('%A')}; it is listed for {listed_days}."

@login_required
@require_http_methods(["POST"])
def mass_assign_single_vehicle_api(request, operator_slug):
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    if not _can_mass_log_for_operator(request.user, operator):
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

            if board_obj.board_type == "running-boards" and not running_board_runs_on_date(board_obj, selected_date):
                yield f"data: {json.dumps({'type': 'done', 'success': False, 'error': running_board_day_error(board_obj, selected_date)})}\n\n"
                return

            if board_obj.board_type == "running-boards" and not running_board_active_on_date(board_obj, selected_date):
                yield f"data: {json.dumps({'type': 'done', 'success': False, 'error': running_board_active_error(board_obj, selected_date)})}\n\n"
                return

            trip_set = board_obj.duty_trips.select_related("route_link").order_by("id")

            created_count = 0
            skipped_count = 0
            skipped_details = []
            errors = []
            overwritten_count = 0

            trip_windows = build_board_trip_windows(trip_set, selected_date)

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
@require_http_methods(["POST"])
def mass_assign_batch_api(request, operator_slug):
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)

    if not _can_mass_log_for_operator(request.user, operator):
        return JsonResponse({'success': False, 'error': "Permission denied."}, status=403)

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    assignments = body.get("assignments", [])
    date_str = body.get("date")
    override_existing = body.get("override", False)

    if not assignments or not date_str:
        return JsonResponse({'success': False, 'error': 'Missing data'}, status=400)

    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid date'}, status=400)

    # --- NORMALISE IDS (FIXES YOUR BUG) ---
    def to_int(val):
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    normalised_assignments = []
    vehicle_ids = set()
    board_ids = set()

    for item in assignments:
        v_id = to_int(item.get("vehicle_id"))
        b_id = to_int(item.get("board_id"))

        if v_id and b_id:
            normalised_assignments.append({
                "vehicle_id": v_id,
                "board_id": b_id
            })
            vehicle_ids.add(v_id)
            board_ids.add(b_id)

    if not normalised_assignments:
        return JsonResponse({'success': False, 'error': 'No valid assignments'}, status=400)

    # --- BULK FETCH VEHICLES ---
    vehicles = {
        v.id: v
        for v in fleet.objects.filter(
            Q(operator=operator) | Q(loan_operator=operator),
            id__in=vehicle_ids
        )
    }

    # --- BULK FETCH BOARDS + TRIPS ---
    boards_qs = (
        duty.objects
        .filter(id__in=board_ids, duty_operator=operator)
        .prefetch_related(
            Prefetch(
                "duty_trips",
                queryset=dutyTrip.objects.select_related("route_link").order_by("id")
            )
        )
    )

    boards_map = {b.id: b for b in boards_qs}

    results = []
    trips_to_create = []

    # --- BUILD TRIPS ---
    for item in normalised_assignments:
        vehicle_id = item["vehicle_id"]
        board_id   = item["board_id"]

        vehicle = vehicles.get(vehicle_id)
        board_obj = boards_map.get(board_id)

        if not vehicle or not board_obj:
            results.append({
                "vehicle_id": vehicle_id,
                "success": False,
                "error": "Invalid vehicle or board"
            })
            continue

        if board_obj.board_type == "running-boards":
            if not running_board_runs_on_date(board_obj, selected_date):
                results.append({
                    "vehicle_id": vehicle_id,
                    "success": False,
                    "error": running_board_day_error(board_obj, selected_date)
                })
                continue
            if not running_board_active_on_date(board_obj, selected_date):
                results.append({
                    "vehicle_id": vehicle_id,
                    "success": False,
                    "error": running_board_active_error(board_obj, selected_date)
                })
                continue

        created = 0

        for trip, start_dt, end_dt in build_board_trip_windows(board_obj.duty_trips.all(), selected_date):
            trips_to_create.append(
                Trip(
                    trip_vehicle=vehicle,
                    trip_route=trip.route_link,
                    trip_route_num=getattr(trip.route_link, "route_num", None),
                    trip_inbound=trip.inbound,
                    trip_start_location=trip.start_at,
                    trip_end_location=trip.end_at,
                    trip_start_at=start_dt,
                    trip_end_at=end_dt,
                    trip_board=board_obj,
                )
            )
            created += 1

        results.append({
            "vehicle_id": vehicle_id,
            "success": True,
            "created": created
        })

    # --- DELETE EXISTING TRIPS IF OVERRIDE ---
    try:
        with transaction.atomic():
            if override_existing and vehicle_ids:
                start_of_day = make_aware(datetime.combine(selected_date, time.min))
                end_of_day = make_aware(datetime.combine(selected_date, time.max))
                Trip.objects.filter(
                    trip_vehicle_id__in=vehicle_ids,
                    trip_start_at__range=(start_of_day, end_of_day)
                ).delete()

            Trip.objects.bulk_create(
                trips_to_create,
                batch_size=1000
            )
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

    return JsonResponse({
        "success": True,
        "results": results
    })

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

def boards_api(request, operator_slug):
    PAGE_SIZE = 100

    q          = request.GET.get("q", "").strip()
    board_type = request.GET.get("type")
    category   = request.GET.get("category")
    date_str   = request.GET.get("date", "").strip()
    service_date = None
    if date_str:
        try:
            service_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            service_date = None
    try:
        page = int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        page = 1

    qs = duty.objects.filter(
        duty_operator__operator_slug=operator_slug
    )

    # filter by type
    if board_type:
        if board_type == "running":
            qs = qs.filter(board_type="running-boards")
        else:
            qs = qs.filter(board_type=board_type)

    # filter by category
    if category and category != "none":
        qs = qs.filter(category_id=category)

    # search
    if q:
        qs = qs.filter(
            Q(duty_name__icontains=q) |
            Q(trip__icontains=q)
        )

    qs = qs.order_by("duty_name").only(
        "id",
        "duty_name",
        "board_type",
        "category",
        "no_run_start",
        "no_run_end",
    ).prefetch_related("duty_day")

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj  = paginator.get_page(page)

    results = []
    for b in page_obj.object_list:
        active = True
        if b.board_type == "running-boards" and service_date is not None:
            active = running_board_active_on_date(b, service_date)
        results.append({
            "id": b.id,
            "text": b.duty_name,
            "type": "running" if b.board_type == "running-boards" else b.board_type,
            "category": str(b.category_id) if b.category_id else "none",
            "days": [d.name for d in b.duty_day.all()],
            "active": active,
        })

    return JsonResponse({
        "results": results,
        "has_more": page_obj.has_next(),
    })
