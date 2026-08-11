from django.shortcuts import render
from .models import *
from fleet.models import MBTOperator, helper, group as OperatorGroup, mapTileSet
from mybustimes.permissions import ReadOnly
from rest_framework import generics
from .serializers import trackingSerializer, trackingDataSerializer, TripSerializer, TrackingSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
#from rest_framework_api_key.permissions import HasAPIKey
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import trackingForm
from django.shortcuts import redirect, get_object_or_404
import math
from main.models import UserKeys
from rest_framework import generics, serializers
from routes.models import routeStop
from fleet.models import fleet
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseForbidden
from django.core.management import call_command
from django.core.cache import cache
from django.conf import settings
from django.views.decorators.http import require_POST
from django.utils import timezone
import time
import secrets

@csrf_exempt
def get_user_from_key(request):
    session_key = request.headers.get("Authorization")
    if not session_key:
        return None, Response({"detail": "Missing Authorization header"}, status=status.HTTP_401_UNAUTHORIZED)

    if session_key.startswith("SessionKey "):
        session_key = session_key.split("SessionKey ")[1]

    try:
        user_key = UserKeys.objects.select_related("user").get(session_key=session_key)
    except UserKeys.DoesNotExist:
        return None, Response({"detail": "Invalid session key"}, status=status.HTTP_401_UNAUTHORIZED)

    return user_key.user, None


@csrf_exempt
class create_tracking(generics.CreateAPIView):
    serializer_class = trackingSerializer

    def post(self, request, *args, **kwargs):
        user, error = get_user_from_key(request)
        if error:
            return error  # Unauthorized

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# List all trips
class TripListView(generics.ListAPIView):
    queryset = Trip.objects.all().order_by("-trip_start_at")
    serializer_class = TripSerializer


# Get a single trip by ID
class TripDetailView(generics.RetrieveAPIView):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    lookup_field = "trip_id"


# List all tracking records
class TrackingListView(generics.ListAPIView):
    queryset = Tracking.objects.select_related('tracking_route').order_by("-tracking_updated_at")
    serializer_class = TrackingSerializer


# Get a single tracking record by ID
class TrackingDetailView(generics.RetrieveAPIView):
    queryset = Tracking.objects.select_related('tracking_route').all()
    serializer_class = TrackingSerializer
    lookup_field = "tracking_id"


# Filter tracking by vehicle (useful for live bus display)
class TrackingByVehicleView(generics.ListAPIView):
    serializer_class = TrackingSerializer

    def get_queryset(self):
        vehicle_id = self.kwargs["vehicle_id"]
        return Tracking.objects.select_related('tracking_route').filter(
            tracking_vehicle_id=vehicle_id
        ).order_by("-tracking_updated_at")

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .models import Trip, Tracking, fleet, route, CustomUser  # adjust imports

@csrf_exempt
def StartNewTripView(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only API"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        data_session_key = data.get("session_key")
        vehicle_id = data.get("vehicle_id")
        route_id = data.get("route_id")
        route_number = data.get("route_number")
        trip_end_location = data.get("outbound_destination")
        trip_start_at_raw = data.get("trip_date_time")  # should be ISO8601 string
        trip_start_at = None
        if trip_start_at_raw:
            parsed = parse_datetime(trip_start_at_raw)
            # If parse_datetime returned None, the input wasn't valid ISO8601
            if parsed is None:
                return JsonResponse({"error": "trip_date_time is invalid ISO8601"}, status=400)
            # Make timezone-aware if naive
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
            trip_start_at = parsed
    except Exception as e:
        return JsonResponse({"error": "Invalid request data", "details": str(e)}, status=400)

    if not data_session_key:
        return JsonResponse({"error": "Missing session_key"}, status=400)
    if not vehicle_id:
        return JsonResponse({"error": "Missing vehicle_id"}, status=400)
    
    try:
        user_key = UserKeys.objects.select_related("user").get(session_key=data_session_key)
        user = user_key.user
    except UserKeys.DoesNotExist:
        return JsonResponse({"error": "Invalid session key"}, status=400)

    # Get related objects
    try:
        vehicle = fleet.objects.get(id=vehicle_id)
        operator_inst = vehicle.operator
    except fleet.DoesNotExist:
        return JsonResponse({"error": "Vehicle not found"}, status=404)
            
    # Permission check
    if operator_inst.owner != user:
        # See if this user is listed as a helper for this operator
        is_helper = helper.objects.filter(
            operator=operator_inst,
            helper=user
        ).exists()

        if not is_helper:
            return JsonResponse({"error": "Permission denied"}, status=403)

    route_obj = None
    if route_id:
        try:
            route_obj = route.objects.get(id=route_id)
        except route.DoesNotExist:
            route_obj = None

    # Create Trip
    trip = Trip.objects.create(
        trip_vehicle=vehicle,
        trip_route=route_obj,
        trip_route_num=route_number,
        trip_end_location=trip_end_location,
        trip_start_at=trip_start_at or timezone.now(),
        trip_driver = user
        # You may want to attach the driver via session_key -> CustomUser lookup
    )

    # Create Tracking (initial data)
    tracking = Tracking.objects.create(
        tracking_vehicle=vehicle,
        tracking_route=route_obj,
        tracking_trip=trip,
        tracking_data={"X": 0, "Y": 0, "delay": 0, "heading": 0, "current_stop_idx": "0"},
        tracking_start_location="Depot",  # optional: replace with real value
        tracking_end_location=trip_end_location,
        tracking_start_at=trip_start_at or timezone.now(),
    )

    return JsonResponse(
        {
            "message": "Trip started",
            "session_key": data_session_key,
            "trip_id": trip.trip_id,
            "tracking_id": tracking.tracking_id,
        },
        status=201
    )

def active_trips(request):
    active_trips = Tracking.objects.filter(trip_ended=False).all()
    serializer = TrackingSerializer(active_trips, many=True)
    return JsonResponse({"active_trips": serializer.data}, status=200)

def update_tracking(request, tracking_id):
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "Invalid method"}, status=400)

    new_tracking_data = request.POST.get('tracking_data')
    tracking = get_object_or_404(Tracking, tracking_id=tracking_id)
    tracking.tracking_data = new_tracking_data
    tracking.save()

    data = {
        'tracking_id': tracking.tracking_id,
        'tracking_data': tracking.tracking_data,
    }

    return JsonResponse({"success": True, "data": data}, status=200)

def update_tracking_template(request, tracking_id):
    tracking = get_object_or_404(Tracking, tracking_id=tracking_id)
    return render(request, 'update.html', {
        'tracking': tracking,
        'mapTile': mapTileSet.default_for_user(request.user),
    })

def create_tracking_template(request, operator_slug):
    operator_instance = MBTOperator.objects.filter(operator_slug=operator_slug).first()
    form = trackingForm(operator=operator_instance)  # 👈 Pass operator_instance to form

    if request.method == 'POST':
        form = trackingForm(request.POST, operator=operator_instance)  # 👈 Again, pass it for POST too

        try:
            vehicle = fleet.objects.get(id=request.POST.get('tracking_vehicle'))
            route_obj = route.objects.get(id=request.POST.get('tracking_route'))
        except (fleet.DoesNotExist, route.DoesNotExist):
            return JsonResponse({"success": False, "error": "Vehicle or route not found."}, status=404)

        if form.is_valid():
            trip = Trip.objects.create(
                trip_vehicle=vehicle,
                trip_route=route_obj,
                trip_start_location=form.cleaned_data.get('tracking_start_location'),
                trip_end_location=form.cleaned_data.get('tracking_end_location'),
                trip_start_at=form.cleaned_data.get('tracking_start_at'),
            )
            form.instance.tracking_trip = trip
            form.save()

            return redirect('update-tracking-template', tracking_id=form.instance.tracking_id)
        else:
            return JsonResponse({"success": False, "errors": form.errors, "data": form.data}, status=400)

    return render(request, 'create.html', {'form': form})

def end_trip(request, tracking_id):
    try:
        tracking = Tracking.objects.get(tracking_id=tracking_id)
        tracking.trip_ended = True
        tracking.save()
        if tracking.tracking_trip:
            tracking.tracking_trip.trip_end_at = timezone.now()
            tracking.tracking_trip.save()
        return redirect('vehicle_detail', operator_slug=tracking.tracking_vehicle.operator, vehicle_id=tracking.tracking_vehicle.id)
    except Tracking.DoesNotExist:
        return JsonResponse({"success": False, "error": "Tracking ID not found"}, status=404)

class map_view(generics.ListAPIView):
    serializer_class = trackingDataSerializer
    permission_classes = [ReadOnly]

    def get_queryset(self):
        tracking_game = self.kwargs.get('game_id')
        tracking_id = self.kwargs.get('tracking_id')
        if tracking_id:
            return Tracking.objects.select_related(
                'tracking_vehicle',
                'tracking_vehicle__vehicleType',
                'tracking_vehicle__operator',
                'tracking_vehicle__livery',
                'tracking_route'
            ).filter(tracking_id=tracking_id)
        if tracking_game:
            return Tracking.objects.select_related(
                'tracking_vehicle',
                'tracking_vehicle__vehicleType',
                'tracking_vehicle__operator',
                'tracking_vehicle__livery',
                'tracking_route'
            ).filter(game_id=tracking_game, trip_ended=False)
        return Tracking.objects.select_related(
            'tracking_vehicle',
            'tracking_vehicle__vehicleType',
            'tracking_vehicle__operator',
            'tracking_vehicle__livery',
            'tracking_route'
        ).filter(trip_ended=False)

class map_view_history(generics.ListAPIView):
    serializer_class = trackingDataSerializer
    permission_classes = [ReadOnly]

    def get_queryset(self):
        tracking_game = self.kwargs.get('game_id')
        tracking_id = self.kwargs.get('tracking_id')
        if tracking_id:
            return Tracking.objects.select_related(
                'tracking_vehicle',
                'tracking_vehicle__vehicleType',
                'tracking_vehicle__operator',
                'tracking_vehicle__livery',
                'tracking_route'
            ).filter(tracking_id=tracking_id)
        if tracking_game:
            return Tracking.objects.select_related(
                'tracking_vehicle',
                'tracking_vehicle__vehicleType',
                'tracking_vehicle__operator',
                'tracking_vehicle__livery',
                'tracking_route'
            ).filter(game_id=tracking_game)
        return Tracking.objects.select_related(
            'tracking_vehicle',
            'tracking_vehicle__vehicleType',
            'tracking_vehicle__operator',
            'tracking_vehicle__livery',
            'tracking_route'
        ).all()

class current_vehicle_trips(generics.ListAPIView):
    serializer_class = TripSerializer
    permission_classes = [ReadOnly]
    def get_queryset(self):
        current_time = timezone.now()
        queryset = Trip.objects.filter(
            trip_start_at__lte=current_time,
            trip_end_at__gte=current_time
        )
        return queryset
    
from django.db.models import Q, Prefetch
from tracking.utils import get_progress


class EstimatedPositionSerializer(serializers.Serializer):
    """Optimized position serializer - all serialization inlined to minimize overhead."""
    
    def to_representation(self, obj):
        ct = obj.current_trip
        trip_route = ct.trip_route if ct else None
        
        # Get progress if trip exists
        progress = get_progress(ct) if ct else None
        
        # --- Inline vehicle serialization ---
        livery = obj.livery
        has_livery = livery is not None
        
        livery_colour = livery.colour if has_livery else (obj.colour or "#000000")
        livery_text = livery.text_colour if has_livery else "#ffffff"
        livery_left = livery.left_css if has_livery else ""
        livery_right = livery.right_css if has_livery else ""
        livery_stroke = livery.stroke_colour if has_livery else ""
        
        left_css = obj.colour if obj.colour else livery_left
        right_css = obj.colour if obj.colour else livery_right
        
        vehicle_name = f"{obj.fleet_number} - {obj.reg}" if obj.fleet_number else (obj.reg or "Unknown Vehicle")
        
        features = ""
        if obj.features:
            features = "<br>".join(obj.features) if isinstance(obj.features, list) else str(obj.features)
        
        operator_slug = obj.operator.operator_slug
        operator_name = obj.operator.operator_name
        
        vehicle_data = {
            "url": f"/operator/{operator_slug}/vehicles/{obj.id}/",
            "name": vehicle_name,
            "operator_slug": operator_slug,
            "operator_name": operator_name,
            "features": features,
            "livery": {
                "id": livery.id if has_livery else None,
                "name": livery.name if has_livery else "Default",
                "colour": livery_colour,
                "text_colour": livery_text,
                "left_css": livery_left,
                "right_css": livery_right,
                "stroke_colour": livery_stroke,
            },
            "colour": livery_colour,
            "text_colour": livery_text,
            "white_text": livery_text.lower() in ("#fff", "#ffffff", "white"),
            "left_css": left_css,
            "right_css": right_css,
            "stroke_colour": livery_stroke,
            "custom_features": obj.advanced_details or None,
        }
        
        # --- Inline service serialization ---
        if trip_route:
            operators = getattr(trip_route, '_prefetched_operators', None)
            if operators is None:
                op = trip_route.route_operators.first()
            else:
                op = operators[0] if operators else None
            
            service_data = {
                "url": f"/operator/{op.operator_slug}/route/{trip_route.id}/" if op else None,
                "line_name": trip_route.route_num or "Unknown Service"
            }
        else:
            service_data = {"url": None, "line_name": "Unknown Service"}
        
        return {
            "trip_id": ct.trip_id if ct else None,
            "vehicle": vehicle_data,
            "service_id": trip_route.id if trip_route else None,
            "service": service_data,
            "progress": progress,
            "lat": obj.sim_lat,
            "lng": obj.sim_lon,
            "destination": ct.trip_end_location if ct else "",
            "heading": obj.sim_heading,
            "delay": obj.sim_delay,
            "updated_at": obj.updated_at,
        }


class trackingAPIView(generics.ListAPIView):
    serializer_class = EstimatedPositionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        params = self.request.query_params
        now = timezone.now()
        
        # Convert bounding box params safely
        try:
            min_lat = float(params.get("ymin"))
            max_lat = float(params.get("ymax"))
            min_lng = float(params.get("xmin"))
            max_lng = float(params.get("xmax"))
        except (TypeError, ValueError):
            return fleet.objects.none()

        operator_id = params.get("operator_id")
        group_name = params.get("group_name") or self.kwargs.get("group_name")
        route_id = params.get("route_id")
        vehicle_id = params.get("vehicle_id")
        
        # Handle hidden operators - comma-separated list of operator IDs to exclude
        hide_operator_ids = params.get("hide_operator_ids", "")
        hidden_ids = [int(x) for x in hide_operator_ids.split(",") if x.strip().isdigit()]

        filters = Q(
            sim_lat__isnull=False,
            sim_lon__isnull=False,
            sim_lat__gte=min_lat,
            sim_lat__lte=max_lat,
            sim_lon__gte=min_lng,
            sim_lon__lte=max_lng,
            current_trip__isnull=False,
            current_trip__trip_start_at__lte=now,
            current_trip__trip_end_at__gte=now,
            current_trip__trip_ended=False,
            current_trip__trip_missed=False,
        )

        if operator_id:
            filters &= Q(operator_id=operator_id) | Q(loan_operator__id=operator_id)

        if group_name:
            operator_group = get_object_or_404(OperatorGroup, group_name=group_name)
            operator_ids = MBTOperator.objects.filter(group=operator_group).values_list("id", flat=True)
            filters &= Q(operator_id__in=operator_ids) | Q(loan_operator_id__in=operator_ids)

        if route_id:
            filters &= Q(current_trip__trip_route_id=route_id)

        if vehicle_id:
            filters &= Q(id=vehicle_id)
        
        # Exclude hidden operators
        if hidden_ids:
            filters &= ~Q(operator_id__in=hidden_ids)

        # Optimized query with prefetch for route_operators
        return fleet.objects.select_related(
            "operator",
            "livery",
            "current_trip",
            "current_trip__trip_route",
        ).prefetch_related(
            Prefetch(
                "current_trip__trip_route__route_operators",
                queryset=MBTOperator.objects.only("id", "operator_slug"),
                to_attr="_prefetched_operators"
            )
        )        .only(
            # Fleet fields
            "id", "fleet_number", "reg", "colour", "advanced_details", "features",
            "sim_lat", "sim_lon", "sim_heading", "sim_delay", "updated_at",
            # Operator fields
            "operator__id", "operator__operator_slug", "operator__operator_name",
            # Livery fields
            "livery__id", "livery__name", "livery__colour", "livery__text_colour",
            "livery__left_css", "livery__right_css", "livery__stroke_colour",
            # Trip fields
            "current_trip__trip_id", "current_trip__trip_end_location",
            "current_trip__trip_start_at", "current_trip__trip_end_at",
            # Route fields
            "current_trip__trip_route__id", "current_trip__trip_route__route_num",
        ).filter(filters)
    
#@require_POST
#@csrf_exempt
#def simulate_positions_view(request):
#    # shared-secret auth
#    expected = settings.CRON_SECRET
#    provided = request.headers.get("X-Cron-Secret")
#    if not expected or not provided or not secrets.compare_digest(expected, provided):
#         return JsonResponse({"status": "nope"}, status=200)
#
#    now = int(time.time())
#    window = now // 60  # current minute bucket
#    key = f"simulate_positions_calls_{window}"
#
#    calls = cache.get(key, 0)
#    if calls >= 2:
#        return JsonResponse(
#            {"status": "rate limit exceeded"},
#            status=429
#        )
#
#    # increment counter (expire after 60s)
#    cache.set(key, calls + 1, timeout=60)
#
#    # overlap protection
#    if not cache.add("simulate_positions_lock", True, timeout=300):
#        return JsonResponse({"status": "already running"}, status=202)
#
#    try:
#        call_command("simulate_positions")
#        return JsonResponse({"status": "ok", "updating": True}, status=200)
#    finally:
#        cache.delete("simulate_positions_lock")


@csrf_exempt
def push_sim_position(request, vehicle_id=None):
    """Push a simulated lat/lon (plus optional rotation) onto a vehicle.

    Auth: same method as the ticketer code system - the caller logs in via
    get_user_profile (user_id + ticketer_code) to obtain a session_key stored
    in UserKeys. That session key must be supplied either as the JSON field
    "session_key" or via the Authorization header ("SessionKey <key>").

    Only the owner of the operator a vehicle belongs to (or is loaned to)
    may push a position for it.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed", "status": 405, "method": request.method}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # session key from body, falling back to the Authorization header
    session_key = data.get("session_key")
    if not session_key:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("SessionKey "):
            session_key = auth_header[len("SessionKey "):]

    vehicle_id = vehicle_id or data.get("vehicle_id")
    if not vehicle_id:
        return JsonResponse({"error": "Missing vehicle_id"}, status=400)
    if not session_key:
        return JsonResponse({"error": "Missing session_key"}, status=401)

    try:
        user_key = UserKeys.objects.select_related("user").get(session_key=session_key)
        user = user_key.user
    except UserKeys.DoesNotExist:
        return JsonResponse({"error": "Invalid session key"}, status=401)

    try:
        vehicle = fleet.objects.select_related("operator", "loan_operator").get(id=vehicle_id)
    except fleet.DoesNotExist:
        return JsonResponse({"error": "Vehicle not found"}, status=404)

    # Permission: user must own the operator the vehicle belongs to (or is loaned to)
    if vehicle.operator.owner != user and not (
        vehicle.loan_operator and vehicle.loan_operator.owner == user
    ):
        return JsonResponse({"error": "Permission denied"}, status=403)

    try:
        lat = float(data.get("lat"))
        lon = float(data.get("lon"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "lat and lon are required numeric fields"}, status=400)

    if not (-90.0 <= lat <= 90.0):
        return JsonResponse({"error": "lat must be between -90 and 90"}, status=400)
    if not (-180.0 <= lon <= 180.0):
        return JsonResponse({"error": "lon must be between -180 and 180"}, status=400)

    rotation = data.get("rotation")
    if rotation is not None:
        try:
            rotation = float(rotation)
        except (TypeError, ValueError):
            return JsonResponse({"error": "rotation must be numeric"}, status=400)
        if not (0.0 <= rotation <= 360.0):
            return JsonResponse({"error": "rotation must be between 0 and 360"}, status=400)
    else:
        rotation = vehicle.sim_heading

    vehicle.sim_lat = lat
    vehicle.sim_lon = lon
    vehicle.sim_heading = rotation
    vehicle.updated_at = timezone.now()
    vehicle.save(update_fields=["sim_lat", "sim_lon", "sim_heading", "updated_at"])

    return JsonResponse({
        "success": True,
        "vehicle_id": vehicle.id,
        "lat": vehicle.sim_lat,
        "lon": vehicle.sim_lon,
        "rotation": vehicle.sim_heading,
        "updated_at": vehicle.updated_at.isoformat() if vehicle.updated_at else None,
    }, status=200)
