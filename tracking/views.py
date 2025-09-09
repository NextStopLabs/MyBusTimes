from django.shortcuts import render
from .models import *
from fleet.models import MBTOperator, helper
from mybustimes.permissions import ReadOnlyOrAuthenticatedCreate
from rest_framework import generics
from .serializers import trackingSerializer, trackingDataSerializer, TripSerializer, TrackingSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
#from rest_framework_api_key.permissions import HasAPIKey
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import trackingForm
from django.shortcuts import redirect
from main.models import UserKeys

from django.views.decorators.csrf import csrf_exempt

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
    queryset = Tracking.objects.all().order_by("-tracking_updated_at")
    serializer_class = TrackingSerializer


# Get a single tracking record by ID
class TrackingDetailView(generics.RetrieveAPIView):
    queryset = Tracking.objects.all()
    serializer_class = TrackingSerializer
    lookup_field = "tracking_id"


# Filter tracking by vehicle (useful for live bus display)
class TrackingByVehicleView(generics.ListAPIView):
    serializer_class = TrackingSerializer

    def get_queryset(self):
        vehicle_id = self.kwargs["vehicle_id"]
        return Tracking.objects.filter(tracking_vehicle_id=vehicle_id).order_by("-tracking_updated_at")

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
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
        trip_start_at = data.get("trip_date_time")  # should be ISO8601 string
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
    return JsonResponse({"active_trips": list(active_trips)}, status=200)

def update_tracking(request, tracking_id):
    if request.method == 'POST':
        new_tracking_data = request.POST.get('tracking_data')

        tracking = Tracking.objects.get(tracking_id=tracking_id)
        tracking.tracking_data = new_tracking_data
        tracking.save()

        data = {
            'tracking_id': tracking.tracking_id,
            'tracking_data': tracking.tracking_data,
        }

        return JsonResponse({"success": True, "data": data}, status=200)
    else:
        return JsonResponse({"success": False, "error": "Invalid method"}, status=400)

def update_tracking_template(request, tracking_id):
    tracking = Tracking.objects.get(tracking_id=tracking_id)
    return render(request, 'update.html', {'tracking': tracking})

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
        return redirect('vehicle_detail', operator_slug=tracking.tracking_vehicle.operator, vehicle_id=tracking.tracking_vehicle.id)
    except Tracking.DoesNotExist:
        return JsonResponse({"success": False, "error": "Tracking ID not found"}, status=404)

class map_view(generics.ListAPIView):
    serializer_class = trackingDataSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

    def get_queryset(self):
        tracking_game = self.kwargs.get('game_id')
        tracking_id = self.kwargs.get('tracking_id')
        if tracking_id:
            return Tracking.objects.filter(tracking_id=tracking_id)
        if tracking_game:
            return Tracking.objects.filter(game_id=tracking_game, trip_ended=False)
        return Tracking.objects.filter(trip_ended=False)

class map_view_history(generics.ListAPIView):
    serializer_class = trackingDataSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

    def get_queryset(self):
        tracking_game = self.kwargs.get('game_id')
        tracking_id = self.kwargs.get('tracking_id')
        if tracking_id:
            return Tracking.objects.filter(tracking_id=tracking_id)
        if tracking_game:
            return Tracking.objects.filter(game_id=tracking_game)
        return Tracking.objects.all()

