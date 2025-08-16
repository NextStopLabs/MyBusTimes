from django.shortcuts import render
from .models import *
from fleet.models import MBTOperator
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

#class update_tracking(generics.UpdateAPIView):
#    queryset = Tracking.objects.all()
#    serializer_class = trackingSerializer
#    permission_classes = [ReadOnlyOrAuthenticatedCreate]
#
#class create_tracking(generics.CreateAPIView):
#    permission_classes = [HasAPIKey]
#
#    def post(self, request):
#        serializer = trackingSerializer(data=request.data)
#        if serializer.is_valid():
#            serializer.save()
#            return Response({"success": True, "data": serializer.data}, status=status.HTTP_201_CREATED)
#        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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

def create_tracking_template(request, operator_name):
    operator_instance = MBTOperator.objects.filter(operator_name=operator_name).first()
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
        return redirect('vehicle_detail', operator_name=tracking.tracking_vehicle.operator, vehicle_id=tracking.tracking_vehicle.id)
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

