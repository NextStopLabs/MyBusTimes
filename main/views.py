#python imports
import json
import random
import os
import requests
import traceback

#app imports
from main.models import *
from fleet.models import *
from routes.models import *
from routes.serializers import *
from .serializers import *
from tracking.models import Tracking
from .forms import ReportForm
from .filters import siteUpdateFilter

#django imports
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.utils.timezone import now
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from collections import defaultdict
from django.http import HttpResponse, Http404

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from tracking.models import Trip
from fleet.models import fleet, MBTOperator
from routes.models import route
from main.models import CustomUser

@csrf_exempt
def get_user_profile(request):
    if request.method == 'OPTIONS':
        # Respond with OK to preflight
        response = HttpResponse()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        code = data.get('code')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not user_id or not code:
        return JsonResponse({'error': 'Missing user_id or code'}, status=400)

    try:
        user = User.objects.get(id=user_id, ticketer_code=code)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Invalid login'}, status=401)

    user_data = {
        'id': user.id,
        'username': user.username,
        'ticketer_code': user.ticketer_code,
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
    
@require_POST
def set_theme(request):
    theme_id = request.POST.get('theme_id')

    try:
        selected_theme = theme.objects.get(pk=theme_id)
    except theme.DoesNotExist:
        return JsonResponse({'error': 'Invalid theme'}, status=400)

    if request.user.is_authenticated:
        # Save theme to user model
        request.user.theme = selected_theme
        request.user.save()
        response = JsonResponse({'message': 'Theme updated for user'})
    else:
        # Set theme cookie for anonymous users
        response = JsonResponse({'message': 'Theme set in cookie'})
        css_filename = selected_theme.css.name  # This might be "themes/MBT_Light.css"
        css_name_only = css_filename.split('/')[-1]  # This will give "MBT_Light.css"

        response.set_cookie('theme', css_name_only, max_age=60*60*24*365)
        response.set_cookie('themeDark', selected_theme.dark_theme, max_age=60*60*24*365)
        response.set_cookie('brandColour', selected_theme.main_colour, max_age=60*60*24*365)
        response.set_cookie('themeID', selected_theme.id, max_age=60*60*24*365)

    return response

def index(request):
    # Load mod.json messages as before
    for_sale_vehicles = fleet.objects.filter(for_sale=True).order_by('fleet_number').count()

    mod_path = os.path.join(settings.MEDIA_ROOT, 'JSON', 'mod.json')
    with open(mod_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    messages = data.get('messages', [])
    message = random.choice(messages) if messages else "Welcome!"

    # Get all regions from DB, order by country and then name
    regions = region.objects.all().order_by('region_country', 'region_name')

    breadcrumbs = [{'name': 'Home', 'url': '/'}]

    context = {
        'breadcrumbs': breadcrumbs,
        'message': message,
        'regions': regions,
        'for_sale_vehicles': for_sale_vehicles,
    }
    return render(request, 'index.html', context)

def live_map(request):
    response = feature_enabled(request, "live_map")
    if response:
        return response
    
    active_trips = Tracking.objects.filter(trip_ended=False)

    vehicles_data = []
    for trip in active_trips:
        data = trip.tracking_data  # This is a dict (JSONField)
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
    }
    return render(request, 'map.html', context)

def live_route_map(request, route_id):
    response = feature_enabled(request, "route_map")
    if response:
        return response
    
    route_instance = get_object_or_404(route, id=route_id)
    operator = route_instance.route_operators.first()
    mapTiles = operator.mapTile if operator else mapTiles.objects.filter(is_default=True).first()

    context = {
        'route': route_instance,
        'full_route_num': route_instance.route_num or "Route",
        'operator': operator,
        'mapTile': mapTiles,
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

def region_view(request, region_code):
    try:
        region_instance = region.objects.get(region_code=region_code)
        operators = MBTOperator.objects.filter(region=region_instance).order_by('operator_name')
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
    operators = MBTOperator.objects.filter(
        Q(operator_name__icontains=query) | Q(operator_code__icontains=query)
    ).order_by('operator_name')

    vehicles = fleet.objects.filter(
        Q(reg__icontains=query) | Q(fleet_number__icontains=query)
    ).order_by('fleet_number')
    
    routes_qs = route.objects.filter(
        Q(route_name__icontains=query) | Q(route_num__icontains=query)
    ).order_by('route_num')

    users = CustomUser.objects.filter(
        Q(username__icontains=query)
    ).order_by('username')

    # Serialize the queryset
    full_routes = routesSerializer(routes_qs, many=True).data

    breadcrumbs = [{'name': 'Home', 'url': '/'}]

    print(f"Search query: {query}")
    print(f"Found {operators.count()} operators and {vehicles.count()} vehicles and {routes_qs.count()} routes and {users.count()} users for query '{query}'")

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

DISCORD_BOT_TOKEN = settings.DISCORD_BOT_TOKEN
DISCORD_CHANNEL_ID = settings.DISCORD_REPORTS_CHANNEL

def send_report_to_discord(report):
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    content = f"**New {report.report_type} Report**\n"
    content += f"Reporter: {report.reporter.username}\n"
    content += f"Details: {report.details}\n"
    content += f"Context: {report.context or 'None'}\n"
    content += f"Time: {report.created_at.strftime('%Y-%m-%d %H:%M')}"

    payload = {
        "content": content
    }

    url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages"
    requests.post(url, headers=headers, json=payload)

def report_view(request):
    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': 'Report', 'url': '/report'}]

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
        'form': form
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

        # Send message to Discord webhook
        webhook_url = settings.DISCORD_LIVERY_REQUESTS_CHANNEL_WEBHOOK
        message = {
            "content": f"New livery created: **{name}** by {request.user.username}\n[Review](https://mybustimes.cc/admin/livery-management/pending/)\n",
        }
        try:
            requests.post(webhook_url, json=message, timeout=5)
        except Exception as e:
            # Optionally log the error
            print(f"Failed to send Discord webhook: {e}")

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

@login_required
@csrf_exempt  # Remove this if using proper CSRF handling
def for_sale(request):
    response = feature_enabled(request, "view_for_sale")
    if response:
        return response

    all_operators = MBTOperator.objects.all()
    allowed_operators = []

    # Get all for sale vehicles (visible to everyone)
    for_sale_vehicles = fleet.objects.filter(for_sale=True).order_by('fleet_number')

    if request.method == "POST":
        vehicle_id = request.POST.get("vehicle_id")
        operator_id = request.POST.get("operator_id")

        vehicle = get_object_or_404(fleet, id=vehicle_id, for_sale=True)
        new_operator = get_object_or_404(MBTOperator, id=operator_id)

        # Check if user is allowed to buy for that operator
        user_perms = get_helper_permissions(request.user, new_operator)
        is_allowed = request.user == new_operator.owner or "Buy Buses" in user_perms or "owner" in user_perms

        if is_allowed:
            # Perform ownership transfer
            vehicle.operator = new_operator
            vehicle.for_sale = False
            vehicle.save()
            messages.success(request, f"You successfully purchased {vehicle.fleet_number} for {new_operator.operator_name}.")
        else:
            messages.error(request, "You do not have permission to buy buses for this operator.")

        return redirect("for_sale")  # Replace with your actual URL name if using `name="for_sale"` in urls.py

    else:
        helper_operator_ids = helper.objects.filter(
            helper=request.user,
            perms__perm_name="Buy Buses"
        ).values_list("operator_id", flat=True)

        # 3. Combined queryset (owners + allowed helpers)
        allowed_operators = MBTOperator.objects.filter(
            Q(id__in=helper_operator_ids) | Q(owner=request.user)
        ).distinct()

        # Group vehicles by operator
        operators_with_vehicles = {}
        for vehicle in for_sale_vehicles:
            if vehicle.operator not in operators_with_vehicles:
                operators_with_vehicles[vehicle.operator] = []
            operators_with_vehicles[vehicle.operator].append(vehicle)

        # Breadcrumbs
        breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': 'For Sale', 'url': '/for-sale/'}]

        context = {
            'breadcrumbs': breadcrumbs,
            'for_sale_vehicles': for_sale_vehicles,
            'operators_with_vehicles': operators_with_vehicles,
            'allowed_operators': allowed_operators,
        }

        return render(request, 'for_sale.html', context)
    
def status(request):
    features = featureToggle.objects.all()

    grouped = defaultdict(list)

    for f in features:
        last_word = f.name.split('_')[-1].title()
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
    updates = siteUpdate.objects.all().order_by('-updated_at')
    
    # Add formatted date to each update
    for update in updates:
        update.formattedDate = update.updated_at.strftime('%d %b %Y %H:%M')
    
    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': 'Service Updates', 'url': '/service-updates/'}]

    context = {
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
    operators = MBTOperator.objects.all().order_by('operator_name')
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
from django.utils.dateparse import parse_date

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

@csrf_exempt
def import_mbt_data(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        data = json.load(file)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    created = {
        "operators": 0,
        "fleet": 0,
        "routes": 0,
        "trips": 0,
        "tickets": 0,
        "routeStops": 0,
    }

    for operator_data in data:
        op_info = operator_data["operator"]
        op_code = op_info["Operator_Code"]
        op_name = op_info["Operator_Name"]

        # Get or create operator
        operator, _ = MBTOperator.objects.get_or_create(
            operator_code=op_code,
            defaults={
                "operator_name": op_name,
                "owner": CustomUser.objects.filter(username=op_info["Owner"]).first(),
                "operator_details": {},
            }
        )
        created["operators"] += 1

        # --- Import Fleet ---
        for fleet_item in operator_data["fleet"]:
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

            raw_features = vehicle.get("Special_Features", "")
            clean_features = [f.strip() for f in raw_features.strip("()").split(",") if f.strip()]
            features_json = clean_features

            fleet_obj, _ = fleet.objects.get_or_create(
                id=vehicle["ID"],
                vehicleType=vehicle_type_obj,
                livery=livery_obj,
                features=features_json,

                defaults={
                    "operator": operator,
                    "fleet_number": vehicle["FleetNumber"],
                    "reg": vehicle["Reg"],
                    "prev_reg": vehicle["PrevReg"],
                    "branding": vehicle.get("Branding", "") or "",
                    "depot": vehicle.get("Depot", "") or "",
                    "preserved": bool(vehicle.get("Preserved", 0)),
                    "on_load": bool(vehicle.get("On_Load", 0)),
                    "for_sale": bool(vehicle.get("For_Sale", 0)),
                    "open_top": bool(vehicle.get("OpenTop") or False),
                    "notes": vehicle.get("Notes", "") or "",
                    "length": vehicle.get("Lenth", "") or "",
                    "in_service": bool(vehicle.get("InService", 1)),
                    "last_tracked_date": None,
                    "last_tracked_route": vehicle.get("LastTrackedAs") or "",
                    "name": vehicle.get("Name", "") or "",
                }
            )
            created["fleet"] += 1

            # --- Import Trips for Fleet ---
            for trip in fleet_item["trips"]:
                Trip.objects.get_or_create(
                    trip_vehicle=fleet_obj,
                    trip_start_at=parse_datetime(trip["TripDateTime"]),
                    trip_end_location=trip.get("EndDestination", ""),
                    trip_route_num=trip.get("RouteNumber", ""),
                    trip_route = route.objects.filter(id=trip.get("RouteID")).first()
                )
                created["trips"] += 1

        # --- Import Routes ---
        for route_item in operator_data["routes"]:
            route_obj, _ = route.objects.get_or_create(
                id=route_item["Route_ID"],
                defaults={
                    "route_num": route_item["Route_Name"],
                    "route_name": route_item.get("RouteBranding", ""),
                    "inbound_destination": route_item.get("Start_Destination"),
                    "outbound_destination": route_item.get("End_Destination"),
                    "route_details": {},
                    "start_date": safe_parse_date(route_item.get("running-from", "1900-01-01")),
                }
            )
            route_obj.route_operators.add(operator)
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

        # --- Import Tickets ---
        for ticket_item in operator_data["tickets"]:
            ticket.objects.get_or_create(
                id=ticket_item["ID"],
                defaults={
                    "operator": operator,
                    "ticket_name": ticket_item["TicketName"],
                    "ticket_price": ticket_item["TicketPrice"],
                    "ticket_details": ticket_item.get("Description", ""),
                    "zone": ticket_item.get("Zone", ""),
                    "valid_for_days": ticket_item.get("ValidForTime"),
                    "single_use": bool(ticket_item.get("OneTime", False)),
                    "name_on_ticketer": ticket_item.get("TicketerName", "") or "",
                    "colour_on_ticketer": ticket_item.get("TicketerColour", "#FFFFFF") or "#FFFFFF",
                    "ticket_category": ticket_item.get("TicketerCat", "") or "",
                    "hidden_on_ticketer": not bool(ticket_item.get("AvaiableOnBus", 1))
                }
            )
            created["tickets"] += 1

    return JsonResponse({
        "status": "success",
        "created": created
    })
