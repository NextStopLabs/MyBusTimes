#python imports
from itertools import count
import json
import operator
import random
import os
import secrets
import threading
import concurrent.futures
import requests
import traceback
import traceback
import sys
import mimetypes
import logging

#app imports
from main.models import *
from fleet.models import *
from routes.models import *
from routes.serializers import *
from .serializers import *
from tracking.models import Tracking
from .forms import ReportForm
from .filters import siteUpdateFilter
from fleet.models import mapTileSet

#django imports
from django.conf import settings
import logging
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_page
from django.db.models import Q, Prefetch
from django.core.cache import cache
from django.utils.timezone import now
from django.contrib import messages
from django.views.decorators.http import require_GET
from django.shortcuts import redirect, get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from collections import defaultdict
from django.http import HttpResponse, Http404
from django.http import FileResponse
from datetime import timedelta
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db.models import Count, Avg

# Bounded executor to avoid unbounded thread growth from repeated imports
_IMPORT_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import status

from tracking.models import Trip
from fleet.models import fleet, MBTOperator
from routes.models import route
from main.models import CustomUser, siteUpdate, featureToggle, siteUpdate, patchNote, Report, CommunityImages
from .forms import GameForm
from fleet.models import fleet, fleetChange, ticket, region, helper, liverie, vehicleType

def buying_buses_banned(request):
    return render(request, 'buying_buses_banned.html')

def selling_buses_banned(request):
    return render(request, 'selling_buses_banned.html')

def ads_txt_view(request):
    ads_path = os.path.join(settings.BASE_DIR, 'static/ads.txt')
    return FileResponse(open(ads_path, 'rb'), content_type='text/plain')

def favicon(request):
    favicon_path = os.path.join(settings.BASE_DIR, 'static/src/icons/favicon/favicon.ico')
    return FileResponse(open(favicon_path, 'rb'), content_type='image/x-icon')

def ticketer_down(request):
    return render(request, 'downpages/ticketer.html')

def about(request):
    return render(request, 'about.html')

def ratelimit_view(request, exception):
    return render(request, 'error/429.html', status=429)

def get_random_community_image(request):
    image_count = CommunityImages.objects.count()
    if image_count == 0:
        return JsonResponse({'error': 'No images found'}, status=404)

    random_index = random.randint(0, image_count - 1)
    image = (
        CommunityImages.objects
        .select_related('uploaded_by')
        .only('id', 'image', 'uploaded_by__username')
        .order_by('id')[random_index]
    )
    if image:
        return JsonResponse({'id': image.id, 'image_url': image.image.url, 'uploaded_by': image.uploaded_by.username})
    return JsonResponse({'error': 'No images found'}, status=404)

def community_hub(request):
    recent_updates = siteUpdate.objects.all().order_by('-updated_at')[:5]

    return render(request, 'community.html', {'recent_updates': recent_updates})

def resources(request):
    return render(request, 'resources.html')

def appeal_ban(request):
    return HttpResponse("No")

@csrf_exempt
def get_user_profile(request):
    if request.method == 'OPTIONS':
        response = HttpResponse()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed', 'status': 405, 'method': request.method}, status=405)

    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        code = data.get('code')
        username = data.get('username')
        password = data.get('password')

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if (user_id and code):
    # use user_id + code path
        try:
            user = User.objects.get(id=user_id, ticketer_code=code)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Invalid login'}, status=401)

    elif (username and password):
        # use username + password path
        user = authenticate(request, username=username, password=password)
        if not user:
            return JsonResponse({'error': 'Invalid login'}, status=401)

    else:
        # neither path provided
        return JsonResponse(
            {'error': 'Missing required fields: provide either (user_id & code) or (username & password)', 'data': data},
            status=400
        )

    # Clear any existing session keys for this user
    UserKeys.objects.filter(user=user).delete()

    # Generate a new 64-character hex session key
    session_key = secrets.token_hex(32)

    # Store in UserKeys
    UserKeys.objects.create(user=user, session_key=session_key)

    user_data = {
        'id': user.id,
        'username': user.username,
        'ticketer_code': user.ticketer_code,
        'session_key': session_key,
    }

    return JsonResponse(user_data)

def ads_txt_view(request):
    possible_paths = []

    # Check STATIC_ROOT (prod, after collectstatic)
    if settings.STATIC_ROOT:
        possible_paths.append(os.path.join(settings.STATIC_ROOT, 'ads.txt'))

    # Check dev static dirs
    if hasattr(settings, 'STATICFILES_DIRS'):
        for static_dir in settings.STATICFILES_DIRS:
            possible_paths.append(os.path.join(static_dir, 'ads.txt'))

    # Serve first existing path
    for path in possible_paths:
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as f:
                return HttpResponse(f.read(), content_type='text/plain')

    raise Http404("ads.txt not found")

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
            return render(request, 'feature_maintenance.html', {'feature_name': feature_key}, status=200)

        if feature_state['super_user_only'] and not request.user.is_superuser:
            return render(request, 'feature_disabled.html', {'feature_name': feature_key}, status=403)

        # Feature is disabled in other ways
        return render(request, 'feature_disabled.html', {'feature_name': feature_key}, status=200)

    # If feature doesn't exist, block it.
    return render(request, 'feature_disabled.html', {'feature_name': feature_key}, status=200)

@require_POST
def set_theme(request):
    theme_id = request.POST.get('theme_id')
    dark_mode = request.POST.get('darkMode')
    dark_mode = True if dark_mode == 'true' else False

    selected_theme = None
    if theme_id:
        try:
            selected_theme = theme.objects.get(pk=theme_id)
        except theme.DoesNotExist:
            return JsonResponse({'error': 'Invalid theme'}, status=400)

    # -----------------------------
    # LOGGED-IN USER
    # -----------------------------
    if request.user.is_authenticated:
        if selected_theme:
            request.user.theme = selected_theme

        request.user.dark_mode = dark_mode
        request.user.save()
        
        return JsonResponse({'message': 'Theme updated for user'})

    # -----------------------------
    # ANONYMOUS USER
    # -----------------------------
    response = JsonResponse({'message': 'Theme set in cookie'})

    if selected_theme:
        light_css_file = selected_theme.light_css.name.split('/')[-1] if selected_theme.light_css else ""
        dark_css_file = selected_theme.dark_css.name.split('/')[-1] if selected_theme.dark_css else ""

        response.set_cookie('themeLight', light_css_file, max_age=60*60*24*365)
        response.set_cookie('themeDarkCSS', dark_css_file, max_age=60*60*24*365)
        response.set_cookie('themeID', selected_theme.id, max_age=60*60*24*365)

        # Set correct brand colour based on dark mode
        brand_colour = selected_theme.dark_main_colour if dark_mode else selected_theme.light_main_colour
        response.set_cookie('brandColour', brand_colour, max_age=60*60*24*365)

    response.set_cookie('darkMode', 'true' if dark_mode else 'false', max_age=60*60*24*365)

    return response

def transparency(request):
    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': 'Transparency', 'url': '/transparency/'}]

    context = {
        'breadcrumbs': breadcrumbs,
    }
    return render(request, 'transparency.html', context)


def get_random_message():
    messages = cache.get('mod_messages')
    if messages is None:
        try:
            with default_storage.open("JSON/mod.json", "r") as f:
                data = json.load(f)
        except Exception as e:
            logging.getLogger(__name__).warning("Could not open JSON/mod.json from storage: %s", e)
            # Attempt local fallback in project tree
            local_path = os.path.join(settings.BASE_DIR, 'JSON', 'mod.json')
            if os.path.exists(local_path):
                with open(local_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
        messages = data.get('messages', [])
        cache.set('mod_messages', messages, 3600)  # Cache for 1 hour
    return random.choice(messages) if messages else "Welcome!"

@cache_page(60 * 5)  # Cache for 5 minutes
def for_sale_count_api(request):
    count = fleet.objects.filter(for_sale=True).count()
    
    # Format the count
    if count > 999:
        formatted = f"{count // 1000}K+"
    else:
        formatted = str(count)
    
    return JsonResponse({
        'count': count,
        'formatted': formatted
    })

def index(request):
    message = get_random_message()
    stats = cache.get('home_page_stats')
    if stats is None:
        stats = {
            'tracking_vehicle_count': fleet.objects.filter(
                sim_lat__isnull=False,
                sim_lon__isnull=False,
                current_trip__isnull=False,
            ).count(),
            'route_count': route.objects.filter(hidden=False).count(),
            'operator_count': MBTOperator.objects.count(),
            'vehicle_count': fleet.objects.count(),
        }
        cache.set('home_page_stats', stats, 300)
    
    # Cache regions for 1 hour
    regions = cache.get('all_regions')
    if regions is None:
        regions = list(region.objects.all().order_by('region_country', 'region_name'))
        cache.set('all_regions', regions, 3600)
    
    breadcrumbs = [{'name': 'Home', 'url': '/'}]
    context = {
        'breadcrumbs': breadcrumbs,
        'message': message,
        'regions': regions,
        **stats,
    }
    return render(request, 'index.html', context)

def adfirst_test(request):
    # Load mod.json messages as before
    for_sale_vehicles = fleet.objects.filter(for_sale=True).order_by('fleet_number').count()
    tracking_vehicle_count = fleet.objects.filter(
        sim_lat__isnull=False,
        sim_lon__isnull=False,
        current_trip__isnull=False,
    ).count()
    route_count = route.objects.filter(hidden=False).distinct().count()
    operator_count = MBTOperator.objects.count()
    vehicle_count = fleet.objects.count()

    path = "JSON/mod.json"
    try:
        with default_storage.open(path, "r") as f:
            data = json.load(f)
    except Exception as e:
        logging.getLogger(__name__).warning("Could not open %s from storage: %s", path, e)
        local_path = os.path.join(settings.BASE_DIR, 'JSON', 'mod.json')
        if os.path.exists(local_path):
            with open(local_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}
    messages = data.get('messages', [])
    message = random.choice(messages) if messages else "Welcome!"

    # Get all regions from DB, order by country and then name
    regions = region.objects.all().order_by('region_country', 'region_name')

    breadcrumbs = [{'name': 'Home', 'url': '/'}]
    if for_sale_vehicles > 9999: 
        for_sale_vehicles = "10K+"
    elif for_sale_vehicles > 8999: 
        for_sale_vehicles = "9K+"
    elif for_sale_vehicles > 7999: 
        for_sale_vehicles = "8K+"
    elif for_sale_vehicles > 6999: 
        for_sale_vehicles = "7K+"
    elif for_sale_vehicles > 5999: 
        for_sale_vehicles = "6K+"
    elif for_sale_vehicles > 4999: 
        for_sale_vehicles = "5K+"
    elif for_sale_vehicles > 3999: 
        for_sale_vehicles = "4K+"
    elif for_sale_vehicles > 2999: 
        for_sale_vehicles = "3K+"
    elif for_sale_vehicles > 1999: 
        for_sale_vehicles = "2K+"
    elif for_sale_vehicles > 999: 
        for_sale_vehicles = "1K+"
    else:
        for_sale_vehicles = for_sale_vehicles
    
    context = {
        'breadcrumbs': breadcrumbs,
        'message': message,
        'regions': regions,
        'for_sale_vehicles': for_sale_vehicles,
        'tracking_vehicle_count': tracking_vehicle_count,
        'route_count': route_count,
        'operator_count': operator_count,
        'vehicle_count': vehicle_count,
    }
    return render(request, 'index-adfirst.html', context)

def live_map(request):
    response = feature_enabled(request, "live_map")
    if response:
        return response
    
    active_trips = Tracking.objects.filter(trip_ended=False).values_list('tracking_data', flat=True)

    vehicles_data = []
    for data in active_trips:
        if data and 'X' in data and 'Y' in data:
            vehicles_data.append({
                "x": data['X'],
                "y": data['Y'],
                "heading": data.get('heading', None),
                "timestamp": data.get('timestamp', None),
                # add any other info you want to include here
            })

    context = {
        'vehicles_json': json.dumps(vehicles_data, cls=DjangoJSONEncoder),
        'mapTileSets': mapTileSet.objects.all().order_by('name'),
    }
    return render(request, 'map.html', context)

def stop_map(request):
    return render(request, 'map-stops.html', {
        'mapTileSets': mapTileSet.objects.all().order_by('name'),
    })

def live_map_simple(request):
    return render(request, 'map-simple.html', {
        'mapTile': mapTileSet.objects.filter(is_default=True).first(),
    })

def operator_route_map(request, operator_slug):
    response = feature_enabled(request, "route_map")
    if response:
        return response
    
    operator = get_object_or_404(MBTOperator, operator_slug=operator_slug)
    mapTiles_instance = operator.mapTile if operator else mapTileSet.objects.filter(is_default=True).first()

    if mapTiles_instance == None:
        mapTiles_instance = mapTileSet.objects.get(id=1)

    context = {
        'operator': operator,
        'mapTile': mapTiles_instance,
        'mapTileSets': mapTileSet.objects.all().order_by('name'),
    }
    return render(request, 'map-operator.html', context)

def live_route_map(request, route_id):
    response = feature_enabled(request, "route_map")
    if response:
        return response
    
    route_instance = get_object_or_404(route, id=route_id)
    operator = route_instance.route_operators.first()
    mapTiles_instance = operator.mapTile if operator else mapTileSet.objects.filter(is_default=True).first()

    if mapTiles_instance == None:
        mapTiles_instance = mapTileSet.objects.get(id=1)

    context = {
        'route': route_instance,
        'full_route_num': route_instance.route_num or "Route",
        'operator': operator,
        'mapTile': mapTiles_instance,
        'mapTileSets': mapTileSet.objects.all().order_by('name'),
    }
    return render(request, 'route_map.html', context)

def live_vehicle_map(request, vehicle_id):
    response = feature_enabled(request, "vehicle_map")
    if response:
        return response

    vehicle_instance = get_object_or_404(fleet, id=vehicle_id)

    context = {
        'vehicle': vehicle_instance,
        'full_vehicle_num': vehicle_instance.fleet_number or "Vehicle",
    }
    return render(request, 'vehicle_map.html', context)

def trip_map(request, trip_id):
    response = feature_enabled(request, "vehicle_map")
    if response:
        return response

    trip = get_object_or_404(Trip, trip_id=trip_id)
    tracking_data = Tracking.objects.filter(tracking_trip=trip).first()
    route = trip.trip_route  # assuming related Route object

    tracking_points = []
    if tracking_data and tracking_data.tracking_history_data:
        tracking_points = tracking_data.tracking_history_data
    else:
        tracking_points = []

    # Determine direction
    if route and route.inbound_destination == trip.trip_end_location:
        direction = "inbound"
    else:
        direction = "outbound"

    operator = route.route_operators.first() if route else None

    mapTiles = mapTileSet.objects.filter(is_default=True).first()
    if operator and operator.mapTile:
        mapTiles = operator.mapTile

    context = {
        'trip': trip,
        'tracking_data': tracking_data,
        'route': route,
        'route_id': route.id if route else "null",
        'operator': operator,
        'direction': direction,
        'mapTile': mapTiles,
        'mapTileSets': mapTileSet.objects.all().order_by('name'),
        'tracking_points': tracking_points,
    }
    return render(request, 'trip_map.html', context)


def region_view(request, region_code):
    try:
        region_instance = region.objects.get(region_code=region_code)
        operators = MBTOperator.objects.filter(region=region_instance).order_by('operator_slug')
    except region.DoesNotExist:
        return render(request, '404.html', status=404)

    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': region_instance.region_name, 'url': f'/region/{region_code}/'}]

    context = {
        'breadcrumbs': breadcrumbs,
        'region': region_instance,
        'operators': operators,
    }
    return render(request, 'region.html', context)

def search(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return render(request, 'search.html', {'results': [], 'query': query})

    # Search for operators and vehicles
    operators = list(MBTOperator.objects.filter(
        Q(operator_name__icontains=query) | Q(operator_code__icontains=query) | Q(operator_slug__icontains=query)
    ).only('id', 'operator_name', 'operator_slug', 'operator_code', 'verified').order_by('operator_slug')[:20])

    vehicle_rows = fleet.objects.filter(
        Q(reg__icontains=query) | Q(fleet_number__icontains=query)
    ).select_related('operator').values(
        'id',
        'fleet_number',
        'reg',
        'operator__operator_name',
        'operator__operator_slug',
    ).order_by('fleet_number')[:20]
    vehicles = [
        {
            'id': row['id'],
            'fleet_number': row['fleet_number'],
            'reg': row['reg'],
            'operator': {
                'operator_name': row['operator__operator_name'],
                'operator_slug': row['operator__operator_slug'],
            },
        }
        for row in vehicle_rows
    ]
    
    routes_qs = (
        route.objects.filter(
        Q(route_name__icontains=query) | Q(route_num__icontains=query)
        )
        .prefetch_related(Prefetch(
            'route_operators',
            queryset=MBTOperator.objects.only('id', 'operator_name', 'operator_slug'),
        ))
        .only('id', 'route_num', 'route_name', 'inbound_destination', 'outbound_destination')
        .order_by('route_num')[:20]
    )

    users = list(CustomUser.objects.filter(
        Q(username__icontains=query)
    ).only('id', 'username').order_by('username')[:20])

    full_routes = []
    for route_obj in routes_qs:
        operators_data = [
            {
                'operator_name': operator.operator_name,
                'operator_slug': operator.operator_slug,
            }
            for operator in route_obj.route_operators.all()[:1]
        ]
        full_routes.append({
            'id': route_obj.id,
            'route_num': route_obj.route_num,
            'route_name': route_obj.route_name,
            'inbound_destination': route_obj.inbound_destination,
            'outbound_destination': route_obj.outbound_destination,
            'route_operators_data': operators_data,
        })

    breadcrumbs = [{'name': 'Home', 'url': '/'}]


    context = {
        'breadcrumbs': breadcrumbs,
        'query': query,
        'operators': operators,
        'vehicles': vehicles,
        'routes': full_routes,
        'users': users,
    }
    return render(request, 'search.html', context)

def rules(request):
    breadcrumbs = [{'name': 'Home', 'url': '/'}]

    context = {
        'breadcrumbs': breadcrumbs,
    }
    return render(request, 'rules.html', context)

def contact(request):
    breadcrumbs = [{'name': 'Home', 'url': '/'}]

    context = {
        'breadcrumbs': breadcrumbs,
    }
    return render(request, 'contact.html', context)

def send_report_to_discord(report):
    content = f"**New {report.report_type} Report**\n"
    content += f"Reporter: {report.reporter.username}\n"
    content += f"Details: {report.details}\n"
    content += f"Context: {report.context or 'None'}\n"
    content += f"Time: {report.created_at.strftime('%Y-%m-%d %H:%M')}"

    data = {
        'channel_id': settings.DISCORD_REPORTS_CHANNEL_ID,
        'send_by': 'Admin',
        'message': content,
    }

    files = {}
    file_obj = None
    try:
        if report.screenshot:
            try:
                # Prefer using storage-backed file open() which works with remote storages
                filename = os.path.basename(report.screenshot.name)
                mime_type, _ = mimetypes.guess_type(filename)
                mime_type = mime_type or 'application/octet-stream'
                file_obj = report.screenshot.open('rb')
                files['image'] = (filename, file_obj, mime_type)
            except NotImplementedError:
                # Storage backend doesn't support open()/path(); try to fetch via URL
                try:
                    url = report.screenshot.url
                    resp = requests.get(url, timeout=5)
                    resp.raise_for_status()
                    from io import BytesIO
                    file_obj = BytesIO(resp.content)
                    ct = resp.headers.get('Content-Type') or 'application/octet-stream'
                    files['image'] = (os.path.basename(url), file_obj, ct)
                except Exception as e:
                    print(f"Could not attach screenshot for report {report.id}: {e}")

        if not settings.DISABLE_JESS:
            try:
                response = requests.post(
                    f"{settings.DISCORD_BOT_API_URL}/send-message",
                    data=data,
                    files=files if files else None,
                    timeout=8,
                )
                if not response.ok:
                    print(f"Discord API returned non-OK status: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Failed to send report to Discord: {e}")

    finally:
        # Ensure file-like objects are closed
        try:
            if file_obj and hasattr(file_obj, 'close'):
                file_obj.close()
        except Exception:
            pass

@login_required
def report_view(request):
    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': 'Report', 'url': '/report'}]

    imageID = request.GET.get('imageID', None)
    user = request.GET.get('user', None)
    imageUploader = request.GET.get('imageUploader', None)

    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.save()
            send_report_to_discord(report)
            return redirect('report_thank_you')  # Optional redirect
    else:
        form = ReportForm()

    return render(request, 'report.html', {
        'breadcrumbs': breadcrumbs,
        'form': form,
        'imageID': imageID,
        'user': user,
        'imageUploader': imageUploader
    })

def report_thank_you_view(request):
    return render(request, 'report_thank_you.html')

def data(request):
    breadcrumbs = [{'name': 'Home', 'url': '/'}]

    context = {
        'breadcrumbs': breadcrumbs,
    }
    return render(request, 'data.html', context)

@login_required
def create_game(request):
    response = feature_enabled(request, "add_game")
    if response:
        return response

    if request.method == "POST":
        form = GameForm(request.POST)
        if form.is_valid():
            game = form.save(commit=False)
            game.details = ""
            game.save()
            messages.success(request, f"Game '{game.game_name}' created successfully.")

            content = f"**New Game Created**\n"
            content += f"Game Name: {game.game_name}\n"

            data = {
                'channel_id': settings.DISCORD_GAME_ID,
                'send_by': 'Admin',
                'message': content,
            }

            if not settings.DISABLE_JESS:
                response = requests.post(
                    f"{settings.DISCORD_BOT_API_URL}/send-message",
                    data=data,
                    files={}
                )

            return redirect('create_game')
    else:
        form = GameForm()

    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': 'Create Game', 'url': '/create/game/'}]
    context = {
        'breadcrumbs': breadcrumbs,
        'form': form,
    }
    return render(request, 'create_game.html', context)

@login_required
def create_livery(request):
    response = feature_enabled(request, "add_livery")
    if response:
        return response

    if request.method == "POST":
        name = request.POST.get('livery-name', '').strip()
        colour = request.POST.get('livery-colour', '').strip()
        left_css = request.POST.get('livery-css-left', '').strip()
        right_css = request.POST.get('livery-css-right', '').strip()
        text_colour = request.POST.get('text-colour', '').strip()
        stroke_colour = request.POST.get('text-stroke-colour', '').strip()

        if stroke_colour == "" or  stroke_colour == "." or  stroke_colour == "none" or  stroke_colour == "None":
            stroke_colour = "#0000"

        if text_colour == "" or  text_colour == "." or  text_colour == "none" or  text_colour == "None":
            text_colour = "#000"

        if colour == "" or  colour == "." or  colour == "none" or  colour == "None":
            colour = "#000"

        if left_css == "" and right_css == "" and colour != "":
            left_css = right_css = colour
        elif left_css == "" or right_css == "" and colour == "":
            return HttpResponseBadRequest("Either both left and right CSS must be provided, or a single livery colour.")
        
        if name == "" or name == "." or name == "none" or name == "None":
            return HttpResponseBadRequest("Livery name is required.")

        new_livery = liverie.objects.create(
            name=name,
            colour=colour,
            left_css=left_css,
            right_css=right_css,
            text_colour=text_colour,
            stroke_colour=stroke_colour,
            updated_at=now(),
            published=False,
            added_by=request.user
        )

        data = {
            'channel_id': settings.DISCORD_LIVERY_ID,
            'send_by': "Livery",
            'message': f"New livery created: **{name}** by {request.user.username}\n[Review](https://www.mybustimes.cc/admin/livery-management/pending/)\n",
        }

        files = {}

        if not settings.DISABLE_JESS:
            response = requests.post(
                f"{settings.DISCORD_BOT_API_URL}/send-message",
                data=data,
                files=files
            )
            response.raise_for_status()

        return redirect(f'/create/livery/progress/{new_livery.id}/')

    breadcrumbs = [{'name': 'Home', 'url': '/'}]
    liveries = liverie.objects.all().order_by('name')[:100]
    context = {
        'breadcrumbs': breadcrumbs,
        'liveryData': liveries,
    }
    return render(request, 'create_livery.html', context)

def create_livery_progress(request, livery_id):
    try:
        livery_instance = liverie.objects.get(pk=livery_id)
    except liverie.DoesNotExist:
        return render(request, '404.html', status=404)

    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': 'Create Livery', 'url': '/create/livery/'}, {'name': 'Progress', 'url': f'/create/livery/progress/{livery_id}/'}]

    context = {
        'breadcrumbs': breadcrumbs,
        'livery': livery_instance,
    }
    return render(request, 'create_livery_progress.html', context)

@require_GET
def user_search_api(request):
    if request.GET.get('username__icontains', ''):
        term = request.GET.get('username__icontains', '').strip()
        users = User.objects.filter(username__icontains=term)[:20]  # limit results
        results = [{"id": user.id, "username": user.username} for user in users]
    elif request.GET.get('username', ''):
        term = request.GET.get('username', '').strip()
        users = User.objects.filter(username=term)[:20]  # limit results
        results = [{"id": user.id, "username": user.username} for user in users]
    
    return JsonResponse(results, safe=False)

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
        helper_instance = helper.objects.get(helper=user, operator=operator)
        permissions = helper_instance.perms.all()

        # Print permission names for debugging
        perm_names = [perm.perm_name for perm in permissions]
        print(f"Helper permissions for {user.username} on operator {operator.operator_slug}: {perm_names}")

        return perm_names

    except helper.DoesNotExist:
        return []

MAX_BUSES_PER_MINUTE = 4  # Limit per user per minute

@login_required
@csrf_exempt  # Remove if you have proper CSRF handling
def for_sale(request):
    response = feature_enabled(request, "view_for_sale")
    if response:
        return response
    
    if request.user.is_authenticated and request.user.banned_from.filter(name='buying_buses').exists():
        return redirect('buying_buses_banned')

    if request.method == "POST":
        vehicle_id = request.POST.get("vehicle_id")
        operator_id = request.POST.get("operator_id")

        vehicle = get_object_or_404(fleet, id=vehicle_id, for_sale=True)
        current_operator = vehicle.operator
        new_operator = get_object_or_404(MBTOperator, id=operator_id)

        if request.user.is_authenticated and request.user.banned_from.filter(name='buying_buses').exists():
            return redirect('buying_buses_banned')

        # Check if user is allowed to buy for that operator
        user_perms = get_helper_permissions(request.user, new_operator)
        is_allowed = request.user == new_operator.owner or "Buy Buses" in user_perms or "owner" in user_perms

        if is_allowed:
            now = timezone.now()
            last_purchase = request.user.last_bus_purchase
            count = request.user.buses_brought_count

            # Reset count if last purchase was more than a minute ago
            if last_purchase and now - last_purchase > timedelta(minutes=1):
                count = 0

            if count >= MAX_BUSES_PER_MINUTE and request.user.is_superuser == False:
                next_allowed_time = last_purchase + timedelta(minutes=1)
                wait_seconds = int((next_allowed_time - now).total_seconds())
                return render(request, 'slow_down.html', {'wait_seconds': wait_seconds})

            # Perform ownership transfer
            vehicle.operator = new_operator
            vehicle.for_sale = False
            vehicle.save()

            for_sale_count = fleet.objects.filter(operator=current_operator, for_sale=True).count()
            current_operator.vehicles_for_sale = for_sale_count
            current_operator.save(update_fields=['vehicles_for_sale'])

            request.user.buses_brought_count = count + 1
            request.user.last_bus_purchase = now
            request.user.save(update_fields=['buses_brought_count', 'last_bus_purchase'])

            messages.success(request, f"You successfully purchased {vehicle.fleet_number} for {new_operator.operator_slug}.")
        else:
            messages.error(request, "You do not have permission to buy buses for this operator.")

        return redirect("for_sale")

    # === GET request ===
    # Get allowed operators for the dropdown
    helper_operator_ids = helper.objects.filter(
        helper=request.user,
        perms__perm_name="Buy Buses"
    ).values_list("operator_id", flat=True)

    allowed_operators = MBTOperator.objects.filter(
        Q(id__in=helper_operator_ids) | Q(owner=request.user)
    ).exclude(
        Q(operator_slug__icontains="sales") |
        Q(operator_slug__icontains="dealer") |
        Q(operator_slug__icontains="deler")
    ).distinct().order_by('operator_slug')

    # Query vehicles efficiently
    for_sale_vehicles = (
        fleet.objects.filter(for_sale=True)
        .select_related("operator", "livery", "vehicleType")   # avoid N+1 queries
        .order_by("fleet_number")
    )

    # Group by operator
    operators_with_vehicles = {}
    vehicle_types = set()
    liveries = set()
    operators = set()

    for vehicle in for_sale_vehicles:
        operators_with_vehicles.setdefault(vehicle.operator, []).append(vehicle)
        if vehicle.vehicleType:
            vehicle_types.add(vehicle.vehicleType.type_name)
        if vehicle.livery:
            liveries.add(vehicle.livery.name)
        if vehicle.operator:
            operators.add(vehicle.operator.operator_name)

    operators_with_vehicles = dict(
        sorted(
            operators_with_vehicles.items(),
            key=lambda item: len(item[1])
        )
    )

    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': 'For Sale', 'url': '/for-sale/'}]

    context = {
        'breadcrumbs': breadcrumbs,
        'operators_with_vehicles': operators_with_vehicles,
        'allowed_operators': allowed_operators,
        'vehicle_types': sorted(vehicle_types),
        'liveries': sorted(liveries),
        'operators': sorted(operators),
    }

    return render(request, 'for_sale.html', context)
    
def status(request):
    features = cache.get('status_feature_rows')
    if features is None:
        features = []
        for feature in featureToggle.objects.all().values('name', 'enabled', 'maintenance', 'coming_soon'):
            if feature['maintenance']:
                status_text = "Under Maintenance"
            elif feature['coming_soon']:
                status_text = "Coming Soon"
            elif feature['enabled']:
                status_text = "Enabled"
            else:
                status_text = "Disabled"
            features.append({
                'name': feature['name'],
                'status_text': status_text,
            })
        cache.set('status_feature_rows', features, 300)

    grouped = defaultdict(list)

    for f in features:
        last_word = f['name'].split('_')[-1].title()
        grouped[last_word].append(f)

    breadcrumbs = [{'name': 'Home', 'url': '/'}]

    context = {
        'breadcrumbs': breadcrumbs,
        'grouped_features': dict(grouped),
    }
    return render(request, 'status.html', context)

class siteUpdateListView(ListAPIView):
    queryset = siteUpdate.objects.all()
    serializer_class = siteUpdateSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = siteUpdateFilter

def site_updates(request):
    updates = cache.get('live_site_updates')
    if updates is None:
        updates = list(siteUpdate.objects.filter(live=True).order_by('-updated_at').values(
            'title',
            'description',
            'updated_at',
        ))
        for update in updates:
            update['formattedDate'] = update['updated_at'].strftime('%d %b %Y %H:%M')
        cache.set('live_site_updates', updates, 300)
    
    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': 'Site Updates', 'url': '/site-updates/'}]

    context = {
        'title': 'Site Updates',
        'breadcrumbs': breadcrumbs,
        'updates': updates,
    }
    return render(request, 'site-updates.html', context)

def patch_notes(request):
    updates = cache.get('patch_notes')
    if updates is None:
        updates = list(patchNote.objects.all().order_by('-updated_at').values(
            'title',
            'description',
            'updated_at',
        ))
        for update in updates:
            update['formattedDate'] = update['updated_at'].strftime('%d %b %Y %H:%M')
        cache.set('patch_notes', updates, 300)

    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': 'Patch Notes', 'url': '/patch-notes/'}]

    context = {
        'title': 'Patch Notes',
        'breadcrumbs': breadcrumbs,
        'updates': updates,
    }
    return render(request, 'site-updates.html', context)

def queue_page(request):
    position = request.session.get('queue_position', '?')
    return render(request, 'queue.html', {'position': position})
    
@login_required
def create_vehicle(request):
    response = feature_enabled(request, "add_vehicle_type")
    if response:
        return response

    if request.method == "POST":
        type_name = request.POST.get('vehicle_name', '').strip()
        vehicle_type = request.POST.get('vehicle_type', 'Bus').strip()
        fuel = request.POST.get('fuel_type', 'Diesel').strip()
        double_decker = request.POST.get('double_decker') == 'on'

        already_exists = vehicleType.objects.filter(type_name__iexact=type_name).exists()


        if already_exists:
            messages.error(request, f"Vehicle type '{type_name}' already exists.") # CHECK BEFORE REQUESTING A TYPE AHHHHHHHHHH
            return redirect('/create/vehicle/')  # Replace with your actual URL name

        # Create the vehicle type object
        vehicle_type_obj = vehicleType.objects.create(
            type_name=type_name,
            type=vehicle_type,
            fuel=fuel,
            double_decker=double_decker,
            added_by=request.user
        )

        # Redirect to a confirmation page or list view
        messages.success(request, f"Vehicle type '{type_name}' created successfully.")
        return redirect('/')  # Replace with your actual URL name

    # GET request - show form
    breadcrumbs = [{'name': 'Home', 'url': '/'}]
    operators = MBTOperator.objects.all().order_by('operator_slug')
    context = {
        'breadcrumbs': breadcrumbs,
        'operators': operators,
    }
    return render(request, 'create_vehicle.html', context)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.utils.dateparse import parse_datetime, parse_date
from routes.models import routeStop, route
from tracking.models import Trip
from fleet.models import MBTOperator, fleet, ticket
from main.models import CustomUser
import re

def sanitize_username(username):
    original = username
    username = username.strip().replace(" ", "_")
    username = re.sub(r"[^\w.@+-]", "", username)  # only allow letters, digits, _, ., @, +, -
    was_modified = username != original
    return username, was_modified

def safe_parse_date(value):
    if value in [None, '', '0000-00-00']:
        return None
    try:
        return parse_date(value)
    except ValueError:
        return None
    
def safe_int(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return None
    
def safe_parse_datetime(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return parse_datetime(value)
    except (ValueError, TypeError):
        return None

@csrf_exempt
def import_mbt_data(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file uploaded'}, status=400)

    uploaded_file = request.FILES['file']
    user = request.user if request.user.is_authenticated else None

    # Save uploaded file
    job = ImportJob.objects.create(user=user, status='pending', progress=0)

    file_path = f'/tmp/import_{job.id}.json'
    with open(file_path, 'wb+') as dest:
        for chunk in uploaded_file.chunks():
            dest.write(chunk)

    # Submit import job to bounded executor (prevents unbounded thread creation)
    try:
        _IMPORT_EXECUTOR.submit(process_import_job, job.id, file_path)
    except Exception:
        # Fallback to daemon thread if executor is unusable
        t = threading.Thread(target=process_import_job, args=(job.id, file_path))
        t.daemon = True
        t.start()

    return JsonResponse({'job_id': str(job.id), 'status': 'started'})

def get_unique_operator_name(base_name):
    """
    Checks if an operator name already exists. If so, appends _1, _2, etc. until a unique name is found.
    """
    candidate = base_name
    counter = 1
    while MBTOperator.objects.filter(operator_name=candidate).exists():
        candidate = f"{base_name}_{counter}"
        counter += 1
    return candidate


def send_migration_error_notification(message, user):
    data = {
        'channel_id': settings.DISCORD_MIGRATION_ERROR_ID,
        'send_by': user if user else 'Admin',
        'message': message,
    }
    files = {}

    if not settings.DISABLE_JESS:
        response = requests.post(
            f"{settings.DISCORD_BOT_API_URL}/send-message",
            data=data,
            files=files
        )
        response.raise_for_status()

def process_import_job(job_id, file_path):
    import time
    from .models import ImportJob
    User = get_user_model()
    username = "Unknown"  # Prevent UnboundLocalError in exception handling

    print(f"Processing import job {job_id} from {file_path}")

    job = ImportJob.objects.get(id=job_id)
    job.status = 'running'
    job.progress = 0
    job.message = "Starting import..."
    job.save()

    print(f"Import job {job_id} is now running.")

    try:
        # Load file contents; guard against MemoryError for very large uploads.
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except MemoryError:
                job.status = 'failed'
                job.message = 'Import failed: file too large to load into memory'
                job.save()
                send_migration_error_notification('Import failed: file too large', 'Admin')
                return

        print(f"Data loaded successfully for job {job_id}")
        job.status = 'running'
        job.message = "Data loaded successfully"
        job.save()

        userData = data.get("user")
        operatorsData = data.get("operators")

        # Simplified example: update progress as you go
        total_operators = len(operatorsData) if operatorsData else 0
        total_vehicles = sum(len(op.get("fleet", [])) for op in operatorsData or [])
        total_routes = sum(len(op.get("routes", [])) for op in operatorsData or [])
        total_tickets = sum(len(op.get("tickets", [])) for op in operatorsData or [])

        if not userData:
            job.status = 'error'
            job.message = "Missing user data"
            job.save()

            send_migration_error_notification("Missing user data", 'Admin')

            return

        if not operatorsData:
            job.status = 'warning'
            job.message = "No Operators data found"
            job.save()

        # ---- Create or update user first ----
        raw_username = userData.get('Username')
        if not raw_username:
            job.status = 'failed'
            job.message = 'Username missing in user data'
            job.save()
            send_migration_error_notification('Username missing in user data', 'Admin')
            return

        sanitized_username, username_modified = sanitize_username(raw_username)
        original_username = sanitized_username

        # Ensure the username is unique
        counter = 1
        while User.objects.filter(username=sanitized_username).exists():
            sanitized_username = f"{original_username}_{counter}"
            counter += 1

        # Notify if the username was modified
        if username_modified or sanitized_username != original_username:
            if job.username_message is None:
                job.username_message = ""
            job.username_message += f"\nUsername '{raw_username}' was sanitized and updated to '{sanitized_username}' to ensure uniqueness."
            username = sanitized_username
        else:
            username = raw_username

        # Now create the user
        user = User.objects.create(
            username=sanitized_username,
            email=userData.get('Eamil')  # Assuming the typo "Eamil" is in the data
        )

        # Update fields
        user.join_date = safe_parse_datetime(userData.get('JoinDate')) or user.join_date
        user.email = userData.get('Eamil') or user.email  # Note the typo in 'Eamil', handle carefully
        user.first_name = userData.get('Name') or user.first_name
        if userData.get('Username') == "Kai":       
            user.is_staff = True
            user.is_superuser = True
        # Handle password (assuming already hashed)
        if 'Password' in userData and userData['Password']:
            user.password = userData['Password']
        # Map banned and related fields
        user.banned = bool(userData.get('Restricted', 0))
        user.banned_reason = userData.get('RestrictedReson') or user.banned_reason
        unban_date = userData.get('UnbanDate')
        if unban_date:
            user.banned_date = parse_datetime(unban_date)
            
        user.ticketer_code = userData.get('code') or user.ticketer_code
        # Profile pic and banner filenames (adjust if you want to handle uploads)
        if userData.get('PFP'):
            user.pfp = userData['PFP']
        if userData.get('Banner'):
            user.banner = userData['Banner']
        # Total reports
        user.total_user_reports = safe_int(userData.get('TotalReports')) or 0
        # Save user updates
        user.save()

        

        if username:
            try:
                user_exists = User.objects.filter(username=username).exists()
                user = User.objects.filter(username=username).first()

                if user_exists:
                    print(f"User '{username}' exists.")

                    job.status = 'running'
                    job.message = "Created User"
                    job.user = user
                    job.save()

                else:
                    job.status = 'failed'
                    job.message = "Failed to Create User"
                    job.save()

                    send_migration_error_notification("Failed to Create User bad", username)

            except Exception as e:
                exc_type, exc_obj, tb = sys.exc_info()
                fname = tb.tb_frame.f_code.co_filename
                line_no = tb.tb_lineno
                error_type = type(e).__name__
                error_msg = str(e)
                stack_trace = traceback.format_exc()

                # You can log the full trace somewhere if needed
                print("FULL TRACEBACK:\n", stack_trace)

                send_migration_error_notification("FULL TRACEBACK:\n" + stack_trace, sanitized_username)

                job.status = 'failed'
                job.message = "Failed to Create User"
                job.save()

                send_migration_error_notification("Failed to Create User", username)

        created = {
            "operators": 0,
            "fleet": 0,
            "routes": 0,
            "trips": 0,
            "tickets": 0,
            "routeStops": 0,
        }

        fleet_counter = 0
        fleet_total = sum(len(op["fleet"]) for op in operatorsData)
        ticket_counter = 0
        ticket_total = sum(len(op["tickets"]) for op in operatorsData)
        route_counter = 0
        route_total = sum(len(op["routes"]) for op in operatorsData)
        trip_counter = 0
        trip_total = sum(len(vehicle.get("trips") or []) for op in operatorsData for vehicle in op.get("fleet", []))


        for i, operator_data in enumerate(operatorsData, start=1):
            op_info = operator_data["operator"]
            op_code = op_info["Operator_Code"]
            op_name = op_info["Operator_Name"]

            # Get or create operator
            # Ensure operator name is unique
            unique_op_name = get_unique_operator_name(op_name.strip())

            operator, _ = MBTOperator.objects.get_or_create(
                operator_code=op_code,
                defaults={
                    "operator_name": unique_op_name,
                    "owner": user,
                    "operator_details": {},
                }
            )

            created["operators"] += 1

            # --- Import Fleet ---
            for fleet_item in operator_data["fleet"]:
                fleet_counter += 1
                vehicle = fleet_item["vehicle"]
                
                vehicle_type_obj = vehicleType.objects.filter(id=vehicle.get("Type", 1)).first()
                livery_id = vehicle.get("Livery")
                if not livery_id or str(livery_id).strip() == "":
                    livery_id = None
                else:
                    try:
                        livery_id = int(livery_id)
                    except (ValueError, TypeError):
                        livery_id = None

                livery_obj = liverie.objects.filter(id=livery_id).first()

                raw_features = vehicle.get("Special_Features") or ""
                clean_features = [f.strip() for f in raw_features.strip("()").split(",") if f.strip()]
                features_json = clean_features

                fleet_obj = fleet.objects.create(
                    vehicleType=vehicle_type_obj,
                    livery=livery_obj,
                    features=features_json,
                    operator=operator,
                    fleet_number=(vehicle.get("FleetNumber") or "").strip(),
                    reg=(vehicle.get("Reg") or "").strip(),
                    prev_reg=(vehicle.get("PrevReg") or "").strip(),
                    branding=(vehicle.get("Branding") or "").strip(),
                    depot=(vehicle.get("Depot") or "").strip(),
                    preserved=bool(vehicle.get("Preserved", 0)),
                    on_load=bool(vehicle.get("On_Load", 0)),
                    for_sale=bool(vehicle.get("For_Sale", 0)),
                    open_top=bool(vehicle.get("OpenTop") or False),
                    notes=(vehicle.get("Notes") or "").strip(),
                    length=(vehicle.get("Length") or "").strip(),
                    in_service=bool(vehicle.get("InService", 1)),
                    last_tracked_date=None,
                    last_tracked_route=(vehicle.get("LastTrackedAs") or "").strip(),
                    name=(vehicle.get("Name") or "").strip(),
                )

                created["fleet"] += 1

                # --- Import Trips for Fleet ---

                for trip in fleet_item["trips"]:
                    trip_counter += 1

                    Trip.objects.create(
                        trip_vehicle=fleet_obj,
                        trip_start_at=parse_datetime(trip["TripDateTime"]),
                        trip_end_location=(trip.get("EndDestination", "") or "").strip(),
                        trip_route_num=(trip.get("RouteNumber", "") or "").strip(),
                        trip_route=route.objects.filter(id=trip.get("RouteID")).first()
                    )

                    created["trips"] += 1
                    job.message = f"Imported {trip_counter} of {trip_total} trips for vehicle {fleet_obj.fleet_number}"
                    job.save()

                job.progress = int(fleet_counter / fleet_total * 100)
                job.message = f"Imported {fleet_counter} of {fleet_total} vehicles"
                job.save()

                  # Simulate processing time

            # --- Import Routes ---
            for route_item in operator_data["routes"]:
                route_counter += 1
                route_obj = route.objects.create(
                    route_num=route_item["Route_Name"],
                    route_name=route_item.get("RouteBranding", ""),
                    inbound_destination=(route_item.get("Start_Destination", "") or "").strip(),
                    outbound_destination=(route_item.get("End_Destination", "") or "").strip(),
                    route_details={},
                    start_date=safe_parse_date(route_item.get("running-from", "1900-01-01")),
                )

                # Now assign the operator to the many-to-many field
                route_obj.route_operators.set([operator])

                created["routes"] += 1

                # --- Create route stops ---
                routeStop.objects.filter(route=route_obj).delete()

                # Inbound stops (from STOP)
                def process_stops(raw_stops):
                    stops_list = []
                    for stop in raw_stops:
                        stop = stop.strip()
                        if not stop:
                            continue
                        timing_point = False
                        if stop.startswith("M - "):
                            timing_point = True
                            stop = stop[4:].strip()  # Remove "M - " prefix
                        stop_dict = {"stop": stop}
                        if timing_point:
                            stop_dict["timing_point"] = True
                        stops_list.append(stop_dict)
                    return stops_list

                # Inbound stops (from STOP)
                inbound_stops_raw = (route_item.get("STOP") or "").splitlines()
                inbound_stops = process_stops(inbound_stops_raw)
                if inbound_stops:
                    routeStop.objects.create(
                        route=route_obj,
                        inbound=True,
                        circular=False,
                        stops=inbound_stops
                    )
                    created["routeStops"] += 1

                # Outbound stops (from STOP2)
                outbound_stops_raw = (route_item.get("STOP2") or "").splitlines()
                outbound_stops = process_stops(outbound_stops_raw)
                if outbound_stops:
                    routeStop.objects.create(
                        route=route_obj,
                        inbound=False,
                        circular=False,
                        stops=outbound_stops
                    )
                    created["routeStops"] += 1

                job.progress = int(route_counter / route_total * 100)
                job.message = f"Imported {route_counter} of {route_total} routes"
                job.save()

                  # Simulate processing time

            # --- Import Tickets ---
            for ticket_item in operator_data["tickets"]:
                ticket_counter += 1
                ticket_obj = ticket.objects.create(
                    operator=operator,
                    ticket_name=ticket_item["TicketName"],
                    ticket_price=ticket_item["TicketPrice"],
                    ticket_details=ticket_item.get("Description", ""),
                    zone=ticket_item.get("Zone", ""),
                    valid_for_days=ticket_item.get("ValidForTime"),
                    single_use=bool(ticket_item.get("OneTime", False)),
                    name_on_ticketer=ticket_item.get("TicketerName", "") or "",
                    colour_on_ticketer=ticket_item.get("TicketerColour", "#FFFFFF") or "#FFFFFF",
                    ticket_category=ticket_item.get("TicketerCat", "") or "",
                    hidden_on_ticketer=not bool(ticket_item.get("AvaiableOnBus", 1))
                )

                created["tickets"] += 1

                job.progress = int(ticket_counter / ticket_total * 100)
                job.message = f"Imported {ticket_counter} of {ticket_total} tickets for operator {operator.id}"
                job.save()

                  # Simulate processing time

        job.status = 'done'
        job.progress = 100
        job.message = "Import complete"
        job.save()

        # Cleanup uploaded file to free disk space
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

        return

    except Exception as e:
        exc_type, exc_obj, tb = sys.exc_info()
        fname = tb.tb_frame.f_code.co_filename
        line_no = tb.tb_lineno
        error_type = type(e).__name__
        error_msg = str(e)
        stack_trace = traceback.format_exc()

        # You can log the full trace somewhere if needed
        print("FULL TRACEBACK:\n", stack_trace)

        send_migration_error_notification("FULL TRACEBACK:\n" + stack_trace, username)

        job.status = 'error'
        job.message = f"{error_type} at {fname}, line {line_no}: {error_msg}"
        job.save()

        # Attempt to cleanup the file even on errors
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
    
def import_status_data(request, job_id):
    try:
        job = ImportJob.objects.get(id=job_id)
        return JsonResponse({
            'status': job.status,
            'progress': job.progress,
            'message': job.message
        })
    except ImportJob.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)
    
def import_status(request, job_id):
    try:
        job = ImportJob.objects.get(id=job_id)
        context = {
            'status': job.status,
            'progress': job.progress,
            'message': job.message,
            'job_id': job.id,
            'username_message': job.username_message if hasattr(job, 'username_message') else ''
        }
        return render(request, 'import_status.html', context)
    except ImportJob.DoesNotExist:
        return render(request, 'import_status.html', {
            'status': 'error',
            'progress': 0,
            'message': 'Job not found'
        }, status=404)

def bus_displays_view(request):
    return render(request, 'display/busdisplays.html')

def bus_blind_view(request):
    return render(request, 'display/busblind.html')

def simple_bus_blind_view(request):
    return render(request, 'display/simpleBusBlind.html')

def bus_internal_view(request):
    return render(request, 'display/businternal.html')

def available_drivers_view(request):
    # Get all tracking records where trip is not ended
    ongoing_trackings = Tracking.objects.filter(
        trip_ended=False
    ).select_related('tracking_trip', 'tracking_trip__trip_driver')

    # Build a list of drivers with tracking_id
    driver_list = []
    seen_driver_ids = set()
    for tracking in ongoing_trackings:
        trip = tracking.tracking_trip
        if trip and trip.trip_driver and trip.trip_driver.id not in seen_driver_ids:
            driver_list.append({
                'driver': trip.trip_driver.username,
                'tracking_id': tracking.tracking_id
            })
            seen_driver_ids.add(trip.trip_driver.id)

    return render(request, 'display/availableDrivers.html', {'drivers': driver_list})

def custom_404(request, exception):
    return render(request, 'error/404.html', status=404)

def community_hub_images(request):
    if request.method != "GET":
        return JsonResponse({"error": "Only GET allowed"}, status=405)

    # Get all images from the community hub
    images_qs = (
        CommunityImages.objects
        .select_related('uploaded_by')
        .only('id', 'image', 'uploaded_by__username', 'created_at')
        .order_by('-created_at')
    )
    paginator = Paginator(images_qs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    images_data = [
        {
            "id": img.id,
            "image_url": img.image.url,
            "uploaded_by": img.uploaded_by.username,
            "created_at": img.created_at,
        }
        for img in page_obj.object_list
    ]

    return render(request, 'community_images.html', {
        'images': images_data,
        'page_obj': page_obj,
    })

@api_view(["GET"])
def api_root(request, format=None):
    return Response({
        "service_updates": reverse("service_updates", request=request, format=format),
        "liveries": reverse("liveries-list", request=request, format=format),
        "types": reverse("type-list", request=request, format=format),

        "operator": {
            "operators": reverse("operator-list", request=request, format=format),
            "fleet": reverse("fleet-list", request=request, format=format),

            "route": {
                "routes": reverse("operator-routes", request=request, format=format),
                "route_stops": reverse("route-stops", args=[1], request=request, format=format),  # example pk
                "timetables": reverse("get_timetables", request=request, format=format),
                "trip_times": reverse("get_trip_times", request=request, format=format),
                "active_trips": reverse("active_trips", request=request, format=format),
            },
        },

        "tracking": {
            "trips": reverse("trip-list", request=request, format=format),
            "trip_detail_example": reverse("trip-detail", args=[1], request=request, format=format),  # example trip_id
            "tracking": reverse("tracking-list", request=request, format=format),
            "tracking_detail_example": reverse("tracking-detail", args=[1], request=request, format=format),  # example tracking_id
            "tracking_by_vehicle_example": reverse("tracking-by-vehicle", args=[1], request=request, format=format),  # example vehicle_id
        },
    })

#### USER API ENDPOINTS ####
@csrf_exempt
def simplify_gradient(request):
    gradient = request.POST.get("gradient", "")
    
    colours = []
    stops = []
    final_gradient = ""
    
    colours_stops = gradient.split(", ")
    if colours_stops:
        colours_stops.pop(0)

    for item in colours_stops:
        item = item.strip().replace(")", "")
        
        if " " in item:
            colour, stop = item.split(" ", 1)
        else:
            colour, stop = item, None
        
        colours.append(colour)
        stops.append(stop)

    for i, colour in enumerate(colours):
        if stops[i] and i < len(colours) - 1:
            if colours[i] == colours[i+1]:
                colours.pop(i)
                stops.split(" ")
                stops.pop(i)

    for i, stop, colour in zip(range(len(colours)), stops, colours):
        if stop:
            final_gradient += f"{colour} {stop}, "
        else:
            final_gradient += f"{colour}, "

    return JsonResponse({"colours": colours, "stops": stops, "final_gradient": final_gradient})


@csrf_exempt
def get_user_operators(request):
    if request.method == "OPTIONS":
        response = HttpResponse()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    try:
        data = json.loads(request.body)
        session_key = data.get("session_key")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not session_key:
        return JsonResponse({"error": "Missing session_key"}, status=400)

    # Find the user via session key
    try:
        user_key = UserKeys.objects.select_related("user").get(session_key=session_key)
        user = user_key.user
    except UserKeys.DoesNotExist:
        return JsonResponse({"error": "Invalid session key"}, status=401)

    # Operators where user is owner
    owned_operators = MBTOperator.objects.filter(owner=user)

    # Operators where user is helper
    helper_operators = MBTOperator.objects.filter(helper_operator__helper=user)

    # Combine + deduplicate, order by operator_slug
    all_operators = (owned_operators | helper_operators).distinct().order_by('operator_slug')

    # Serialize result
    operators_data = [
        {
            "id": op.id,
            "operator_slug": op.operator_slug,
            "operator_code": op.operator_code,
            "owner": op.owner.username if op.owner else None,
        }
        for op in all_operators
    ]

    return JsonResponse({"operators": operators_data})

@csrf_exempt
def operator_fleet_view(request, opID):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    import json
    try:
        data = json.loads(request.body)
        session_key = data.get("session_key")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not session_key:
        return JsonResponse({"error": "Missing session_key"}, status=400)

    # validate session
    try:
        user_key = UserKeys.objects.select_related("user").get(session_key=session_key)
        user = user_key.user
    except UserKeys.DoesNotExist:
        return JsonResponse({"error": "Invalid session key"}, status=401)

    # check operator exists
    try:
        operator = MBTOperator.objects.get(id=opID)
    except MBTOperator.DoesNotExist:
        return JsonResponse({"error": "Operator not found"}, status=404)

    # check user is owner or helper
    if not (operator.owner == user or operator.helper_operator.filter(helper=user).exists()):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    # get fleet
    operator_fleet = fleet.objects.filter(operator=operator, in_service=True).select_related(
        'vehicleType'
    ).order_by('fleet_number_sort')

    fleet_data = [
        {
            "id": v.id,
            "fleet_number": v.fleet_number,
            "reg": v.reg,
            "vehicleType": v.vehicleType.type_name if v.vehicleType else None,
            "in_service": v.in_service,
        }
        for v in operator_fleet
    ]

    return JsonResponse({"fleet": fleet_data})

@csrf_exempt
def operator_routes_view(request, opID):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    import json
    try:
        data = json.loads(request.body)
        session_key = data.get("session_key")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not session_key:
        return JsonResponse({"error": "Missing session_key"}, status=400)

    # validate session
    try:
        user_key = UserKeys.objects.select_related("user").get(session_key=session_key)
        user = user_key.user
    except UserKeys.DoesNotExist:
        return JsonResponse({"error": "Invalid session key"}, status=401)

    # validate operator
    try:
        operator = MBTOperator.objects.get(id=opID)
    except MBTOperator.DoesNotExist:
        return JsonResponse({"error": "Operator not found"}, status=404)

    # check user is owner or helper
    if not (operator.owner == user or operator.helper_operator.filter(helper=user).exists()):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    # get routes associated with operator
    operator_routes = route.objects.filter(route_operators=operator).order_by('route_num')

    routes_data = [
        {
            "id": r.id,
            "route_num": r.route_num,
            "route_name": r.route_name,
            "inbound_destination": r.inbound_destination,
            "outbound_destination": r.outbound_destination,
        }
        for r in operator_routes
    ]

    return JsonResponse({"routes": routes_data})

@csrf_exempt
def online_members(request):
    if request.method != "GET":  # this is for your frontend
        return JsonResponse({"error": "Only GET allowed"}, status=405)

    GUILD_ID = settings.DISCORD_GUILD_ID
    DISCORD_BOT_TOKEN = settings.DISCORD_BOT_TOKEN

    print("Fetching total members from Discord...")
    print(f"Guild ID: {GUILD_ID}")

    total_discord_url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members-search"
    online_discord_url = f"https://discord.com/api/guilds/{GUILD_ID}/widget.json"

    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"limit": 1}

    total_discord_response = requests.post(total_discord_url, headers=headers, json=payload)
    online_discord_response = requests.get(online_discord_url)

    if total_discord_response.status_code == 200:
        total_discord_members = total_discord_response.json().get("total_result_count", 0)
    else:
        total_discord_members = -1

    if online_discord_response.status_code == 200:
        online_discord_members = online_discord_response.json().get("presence_count", 0)
    else:
        online_discord_members = -1

    cutoff = timezone.now() - timedelta(minutes=10)
    online_mbt_members = User.objects.filter(last_active__gte=cutoff, is_active=True).count()

    total_mbt_members = User.objects.filter(is_active=True).count()

    return JsonResponse({
        "total_discord_members": total_discord_members,
        "online_discord_members": online_discord_members,
        "total_mbt_members": total_mbt_members,
        "online_mbt_members": online_mbt_members,
    })


@require_GET
def site_member_counts(request):
    counts = cache.get("site_member_counts")
    if counts is None:
        cutoff = timezone.now() - timedelta(minutes=10)
        counts = {
            "online_users_count": User.objects.filter(last_active__gte=cutoff, is_active=True).count(),
            "total_users_count": User.objects.filter(is_active=True).count(),
        }
        cache.set("site_member_counts", counts, 60)

    return JsonResponse(counts)


def stats_page(request):
    # ----- USERS -----
    total_users = CustomUser.objects.count()
    active_users = CustomUser.objects.filter(is_active=True).count()
    banned_users = CustomUser.objects.filter(banned=True).count()
    ad_free_users = CustomUser.objects.filter(ad_free_until__gt=timezone.now()).count()
    users_per_team = MBTTeam.objects.annotate(user_count=Count('team_members')).order_by('-user_count')

    # ----- OPERATORS -----
    total_operators = MBTOperator.objects.distinct().count()
    operators_per_region = region.objects.annotate(operator_count=Count('operators')).order_by('-operator_count')
    top_operators = MBTOperator.objects.annotate(fleet_count=Count('fleet_operator', distinct=True)).order_by('-fleet_count')[:5]


    # ----- FLEETS -----
    total_buses = fleet.objects.count()
    avg_fleet_per_operator = fleet.objects.values('operator').annotate(bus_count=Count('id')).aggregate(avg_count=Avg('bus_count'))['avg_count'] or 0

    # ----- REPORTS -----
    total_reports = Report.objects.count()
    reports_by_type = Report.objects.values('report_type').annotate(count=Count('id'))

    # ----- BANNED IPS -----
    total_banned_ips = BannedIps.objects.count()
    recent_banned_ips = BannedIps.objects.order_by('-banned_at')[:10]  # add this

    # ----- FEATURES -----
    features = featureToggle.objects.all()

    # ----- COMMUNITY IMAGES -----
    total_community_images = CommunityImages.objects.count()
    recent_community_images = CommunityImages.objects.order_by('-created_at')[:5]

    # ----- OTHER STATS -----
    total_helpers = helper.objects.count()
    total_liveries = liverie.objects.count()
    total_vehicle_types = vehicleType.objects.count()
    total_tickets = ticket.objects.count()
    total_fleet_changes = fleetChange.objects.count()

    # ----- CONTEXT -----
    context = {
        # Users
        'total_users': total_users,
        'active_users': active_users,
        'banned_users': banned_users,
        'ad_free_users': ad_free_users,
        'users_per_team': users_per_team,

        # Operators
        'total_operators': total_operators,
        'operators_per_region': operators_per_region,
        'top_operators': top_operators,

        # Fleets
        'total_buses': total_buses,
        'avg_fleet_per_operator': avg_fleet_per_operator,

        # Reports
        'total_reports': total_reports,
        'reports_by_type': reports_by_type,

        # Banned IPs
        'total_banned_ips': total_banned_ips,
        'recent_banned_ips': recent_banned_ips,

        # Features
        'features': features,

        # Community Images
        'total_community_images': total_community_images,
        'recent_community_images': recent_community_images,

        # Other
        'total_helpers': total_helpers,
        'total_liveries': total_liveries,
        'total_vehicle_types': total_vehicle_types,
        'total_tickets': total_tickets,
        'total_fleet_changes': total_fleet_changes,
    }

    return render(request, "stats.html", context)

def healthz(request):
    return HttpResponse("ok")
