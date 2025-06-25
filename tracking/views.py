from django.shortcuts import render
from .models import *
from mybustimes.permissions import ReadOnlyOrAuthenticatedCreate
from rest_framework import generics
from .serializers import trackingSerializer, trackingDataSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_api_key.permissions import HasAPIKey
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import trackingForm
from django.shortcuts import redirect

class update_tracking(generics.UpdateAPIView):
    queryset = Trip.objects.all()
    serializer_class = trackingSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

class create_tracking(generics.CreateAPIView):
    permission_classes = [HasAPIKey]

    def post(self, request):
        serializer = trackingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
def update_tracking(request, tracking_id):
    if request.method == 'POST':
        new_tracking_data = request.POST.get('tracking_data')

        tracking = Trip.objects.get(tracking_id=tracking_id)
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
    tracking = Trip.objects.get(tracking_id=tracking_id)
    return render(request, 'update.html', {'tracking': tracking})

def create_tracking_template(request):
    form = trackingForm()
    if request.method == 'POST':
        form = trackingForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('update-tracking-template', tracking_id=form.instance.tracking_id)
            #return JsonResponse({"success": True})
        return JsonResponse({"success": False, "errors": form.errors, "data": form.data}, status=400)

    return render(request, 'create.html', {'form': form})


class map_view(generics.ListAPIView):
    serializer_class = trackingDataSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

    def get_queryset(self):
        tracking_game = self.kwargs.get('game_id')
        tracking_id = self.kwargs.get('tracking_id')
        if tracking_id:
            return Trip.objects.filter(tracking_id=tracking_id)
        if tracking_game:
            return Trip.objects.filter(game_id=tracking_game, trip_ended=False)
        return Trip.objects.filter(trip_ended=False)

class map_view_history(generics.ListAPIView):
    serializer_class = trackingDataSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

    def get_queryset(self):
        tracking_game = self.kwargs.get('game_id')
        tracking_id = self.kwargs.get('tracking_id')
        if tracking_id:
            return Trip.objects.filter(tracking_id=tracking_id)
        if tracking_game:
            return Trip.objects.filter(game_id=tracking_game)
        return Trip.objects.all()

