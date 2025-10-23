from django.shortcuts import render
from rest_framework import generics, permissions, viewsets, status, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse, Http404
from django.views import View
from mybustimes.permissions import ReadOnly
from .models import *
from .filters import *
from .serializers import *
from collections import defaultdict
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
import json

class routesListView(generics.ListCreateAPIView):
    queryset = route.objects.all()
    serializer_class = routesSerializer
    permission_classes = [ReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = routesFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)

        if search:
            search_terms = search.split()
            
            filter_condition = Q()
            for term in search_terms:
                filter_condition |= (
                    Q(route_num__icontains=term) | 
                    Q(inbound_destination__icontains=term) | 
                    Q(outbound_destination__icontains=term)
                )
            
            queryset = queryset.filter(filter_condition)
        
        return queryset

class routeStops(View):
    def get(self, request, pk):
        direction = request.GET.get('direction', 'inbound').lower()
        if direction not in ('inbound', 'outbound'):
            return JsonResponse({'error': 'Invalid direction'}, status=400)

        inbound_flag = (direction == 'inbound')

        # Validate route exists
        try:
            route_instance = route.objects.get(pk=pk)
        except route.DoesNotExist:
            raise Http404("Route not found")

        # Get the first matching routeStop (if more than one exists)
        route_stop = routeStop.objects.filter(route=route_instance, inbound=inbound_flag).first()

        if not route_stop:
            return JsonResponse({'stops': []})

        return JsonResponse(route_stop.stops, safe=False)

class routesDetailView(generics.RetrieveAPIView):
    queryset = route.objects.all()
    serializer_class = routesSerializer
    permission_classes = [ReadOnly] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = routesFilter

class routesUpdateView(generics.UpdateAPIView):
    queryset = route.objects.all()
    serializer_class = routesSerializer
    permission_classes = [ReadOnly]

class routesCreateView(generics.CreateAPIView):
    queryset = route.objects.all()
    serializer_class = routesSerializer
    permission_classes = [ReadOnly]

class timetableView(generics.ListCreateAPIView):
    queryset = timetableEntry.objects.all()
    serializer_class = timetableSerializer
    permission_classes = [ReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = timetableFilter

class dayTypeListView(generics.ListCreateAPIView):
    queryset = dayType.objects.all()
    serializer_class = dayTypeSerializer
    permission_classes = [ReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = dayTypeFilter

class stopRouteSearchView(APIView):
    def get(self, request):
        stop_name = request.query_params.get('stop', '').strip()
        day = request.query_params.get('day', '').strip()

        if not stop_name:
            return Response({"error": "Missing 'stop' query parameter."}, status=status.HTTP_400_BAD_REQUEST)

        all_entries = timetableEntry.objects.select_related('route').prefetch_related('day_type')

        route_timings = defaultdict(list)

        for entry in all_entries:
            try:
                stop_times_data = json.loads(entry.stop_times or "{}")
            except json.JSONDecodeError:
                continue

            if stop_name not in stop_times_data:
                continue

            time_at_stop = stop_times_data[stop_name]
            days = entry.day_type.all()
            day_names = [d.name for d in days]

            if day and day not in day_names:
                continue

            route_timings[entry.route.id].append({
                'timing_point': True,
                'stopname': stop_name,
                'times': time_at_stop.get('times', []),
                'inbound': entry.inbound,
                'circular': entry.circular,
                'days': day_names,
            })

        unique_route_ids = list(route_timings.keys())
        routes_qs = route.objects.filter(id__in=unique_route_ids).prefetch_related('route_operators')

        response_data = []
        for r in routes_qs:
            response_data.append({
                'route_id': r.id,
                'route_num': r.route_num,
                'route_name': r.route_name,
                'inbound_destination': r.inbound_destination,
                'outbound_destination': r.outbound_destination,
                'route_operators': operatorFleetSerializer(r.route_operators.all(), many=True).data,
                'stop_timings': sorted(route_timings[r.id], key=lambda x: x['times']),
            })

        return Response(response_data)
    
class stopServicesListView(APIView):
    def get(self, request):
        stop_name = request.query_params.get('stop', '').strip()
        
        if not stop_name:
            return Response({"error": "Missing 'stop' query parameter."}, status=status.HTTP_400_BAD_REQUEST)

        all_entries = timetableEntry.objects.select_related('route').prefetch_related('day_type')

        route_timings = defaultdict(list)

        for entry in all_entries:
            stop_times_raw = entry.stop_times or "{}"
            # Accept already-parsed dicts or JSON strings
            if isinstance(stop_times_raw, str):
                try:
                    stop_times_data = json.loads(stop_times_raw)
                except json.JSONDecodeError:
                    continue
            elif isinstance(stop_times_raw, dict):
                stop_times_data = stop_times_raw
            else:
                continue

            matched_key = None
            for key in stop_times_data.keys():
                base_key = key.split('_idx_')[0].strip()
                if base_key.lower() == stop_name.lower():
                    matched_key = key
                    break

            if not matched_key:
                continue

            stop_data = stop_times_data.get(matched_key, {})

            route_timings[entry.route.id].append({
                'stopname': stop_name,
            })

        unique_route_ids = list(route_timings.keys())
        routes_qs = route.objects.filter(id__in=unique_route_ids).prefetch_related('route_operators')

        response_data = []
        for r in routes_qs:
            response_data.append({
                'route_id': r.id,
                'route_num': r.route_num,
                'route_name': r.route_name,
                'inbound_destination': r.inbound_destination,
                'outbound_destination': r.outbound_destination,
                'route_operators': operatorFleetSerializer(r.route_operators.all(), many=True).data,
                'stop_timings': sorted(route_timings[r.id], key=lambda x: x.get('times', [])),
            })

        return Response(response_data)
class stopUpcomingTripsView(APIView):

    def get(self, request):
        stop_name = request.query_params.get('stop', '').strip()
        day = request.query_params.get('day', '').strip()
        current_time_str = request.query_params.get('current_time', '').strip()
        limit = int(request.query_params.get('limit', 5))

        if not stop_name:
            return Response({"error": "Missing 'stop' query parameter."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            current_time = datetime.strptime(current_time_str, "%H:%M").time() if current_time_str else None
        except ValueError:
            return Response({"error": "Invalid 'current_time' format. Use HH:MM."}, status=status.HTTP_400_BAD_REQUEST)

        all_entries = timetableEntry.objects.select_related('route').prefetch_related('day_type', 'route__route_operators')
        upcoming_trips = []

        for entry in all_entries:
            stop_times_data = entry.stop_times
            if isinstance(stop_times_data, str):
                try:
                    stop_times_data = json.loads(stop_times_data)
                except json.JSONDecodeError:
                    continue

            if not isinstance(stop_times_data, dict):
                continue

            matched_key = None
            for key in stop_times_data.keys():
                base_key = key.split('_idx_')[0].strip()
                if base_key.lower() == stop_name.lower():
                    matched_key = key
                    break

            if not matched_key:
                continue

            valid_days = list(entry.day_type.values_list('name', flat=True))
            if day and day not in valid_days:
                continue

            stop_data = stop_times_data.get(matched_key, {})
            times = stop_data.get('times', [])
            operator_schedule = entry.operator_schedule or []

            for idx, time_str in enumerate(times):
                try:
                    trip_time = datetime.strptime(time_str.strip(), "%H:%M").time()
                except ValueError:
                    continue

                if current_time and trip_time < current_time:
                    continue

                operator_string = operator_schedule[idx] if idx < len(operator_schedule) else (
                    entry.route.route_operators.first().operator_code if entry.route.route_operators.exists() else None
                )

                operator_obj = MBTOperator.objects.filter(operator_code__iexact=operator_string).first()
                operator_data = {
                    'operator_code': operator_obj.operator_code if operator_obj else None,
                    'operator_name': operator_obj.operator_name if operator_obj else (operator_string or "Unknown"),
                    'operator_slug': operator_obj.operator_slug if operator_obj else None,
                }

                if entry.inbound or entry.route.outbound_destination == None:
                    route_dest = entry.route.inbound_destination
                else:
                    route_dest = entry.route.outbound_destination

                upcoming_trips.append({
                    'route_id': entry.route.id,
                    'route_num': entry.route.route_num,
                    'route_dest': route_dest,
                    'route_operator': operator_data,
                    'time': trip_time.strftime("%H:%M")
                })

        upcoming_trips.sort(key=lambda x: x['time'])
        return Response(upcoming_trips[:limit])


class timetableDaysView(APIView):
    permission_classes = [ReadOnly]

    def get(self, request, *args, **kwargs):
        queryset = timetableEntry.objects.all()

        # Optional: apply filters if using DjangoFilterBackend
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)

        merged = {}
        for entry in queryset:
            route_id = entry.route.id
            if route_id not in merged:
                merged[route_id] = {
                    'route': entry.route,
                    'day_type': set(entry.day_type.values_list('name', flat=True))  # Assuming name field
                }
            else:
                merged[route_id]['day_type'].update(entry.day_type.values_list('name', flat=True))

        # Prepare final list
        results = []
        for item in merged.values():
          results.append({
                'route': item['route'],
                'day_type': sorted(item['day_type'])  # Optional sorting
            })

        serializer = timetableDaysSerializer(results, many=True)
        return Response({
            "count": len(results),
            "next": None,
            "previous": None,
            "results": serializer.data
        })

    # Support for `filter_backends` if desired
    filter_backends = (DjangoFilterBackend,)
    filterset_class = timetableDaysFilter

class dutyListView(generics.ListCreateAPIView):
    queryset = duty.objects.all()
    serializer_class = dutySerializer
    permission_classes = [ReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = dutyFilter

class dutyDetailView(generics.RetrieveAPIView):
    queryset = duty.objects.all()
    serializer_class = dutySerializer
    permission_classes = [ReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = dutyFilter

class transitAuthoritiesColourView(generics.ListCreateAPIView):
    queryset = transitAuthoritiesColour.objects.all()
    serializer_class = transitAuthoritiesColourSerializer
    permission_classes = [ReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = transitAuthoritiesColourFilter

class transitAuthoritiesColourDetailView(generics.RetrieveAPIView):
    serializer_class = transitAuthoritiesColourSerializer
    permission_classes = [ReadOnly]

    def get_object(self):
        code = self.kwargs.get('code')
        return transitAuthoritiesColour.objects.get(authority_code=code)

def stop(request):
    stop_name = request.GET.get('name', '')
    stop_name_idx = stop_name
    stop_name = stop_name.split("_idx_")[0]

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Stops', 'url': '/'},
        {'name': stop_name, 'url': f'/stop/?name={stop_name}'}
    ]

    return render(request, 'stop.html', {
        'stop_name': stop_name,
        'stop_name_idx': stop_name_idx,
        'date': request.GET.get('date', ''),
        'time': request.GET.get('time', ''),
        'breadcrumbs': breadcrumbs
    })


def get_timetables(request):
    route_id = request.GET.get('route_id')
    if not route_id:
        return JsonResponse({'timetables': {}})
    
    entries = timetableEntry.objects.filter(route_id=route_id)
    data = {entry.id: str(entry) for entry in entries}
    return JsonResponse({'timetables': data})

from django.http import JsonResponse
import json

def get_trip_times(request):
    timetable_id = request.GET.get('timetable_id')
    try:
        tt = timetableEntry.objects.get(id=timetable_id)

        # Parse stop_times if it's a JSON string
        stop_times = tt.stop_times
        if isinstance(stop_times, str):
            stop_times = json.loads(stop_times)

        # Sort stops by order (if order exists, otherwise keep insertion order)
        ordered_stops = sorted(stop_times.items(), key=lambda x: x[1].get('order', 0))
        stop_keys = [stop[0] for stop in ordered_stops]

        # Use stopname from each stop object
        start_key = stop_keys[0]
        end_key = stop_keys[-1]
        start_stop_name = stop_times[start_key]["stopname"]
        end_stop_name = stop_times[end_key]["stopname"]

        start_times = stop_times[start_key]["times"]
        end_times = stop_times[end_key]["times"]

        times_data = {}
        for i, start_time in enumerate(start_times):
            end_time = end_times[i] if i < len(end_times) else None
            label = f"{start_time} — {start_stop_name} ➝ {end_stop_name}"
            times_data[start_time] = {
                "label": label,
                "start_time": start_time,
                "end_time": end_time
            }

        return JsonResponse({
            "times": times_data,
            "start_stop": start_stop_name,
            "end_stop": end_stop_name
        })

    except timetableEntry.DoesNotExist:
        return JsonResponse({'error': 'Timetable entry not found.'}, status=404)
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        return JsonResponse({'error': f'Invalid timetable data: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


class RouteTripETAView(APIView):
    """
    Given a route ID and a trip start time, returns all stops and expected times.
    Optionally takes current_stop_index to return only current + next stop.
    """

    def get(self, request):
        route_id = request.query_params.get("route_id")
        start_time_str = request.query_params.get("start_time")  # format "HH:MM"
        inbound = request.query_params.get("inbound", "true").lower() == "true"
        current_stop_index = request.query_params.get("current_stop_index")

        if not route_id or not start_time_str:
            return Response({"error": "route_id and start_time required"}, status=status.HTTP_400_BAD_REQUEST)

        route_obj = get_object_or_404(route, pk=route_id)

        try:
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
        except ValueError:
            return Response({"error": "Invalid start_time format. Use HH:MM"}, status=status.HTTP_400_BAD_REQUEST)

        timetable = timetableEntry.objects.filter(route=route_obj, inbound=inbound).first()
        if not timetable or not timetable.stop_times:
            return Response({"error": "No timetable found for this route and direction"}, status=status.HTTP_404_NOT_FOUND)

        try:
            stop_times = json.loads(timetable.stop_times)
        except Exception as e:
            return Response({"error": f"Invalid stop_times data: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        today = datetime.today().date()
        start_dt = datetime.combine(today, start_time)

        closest_index = None
        min_diff = None

        first_stop_name = list(stop_times.keys())[0]
        first_stop_times = stop_times[first_stop_name]["times"]

        for idx, t in enumerate(first_stop_times):
            stop_time_obj = datetime.strptime(t, "%H:%M").time()
            stop_dt = datetime.combine(today, stop_time_obj)
            diff = abs((stop_dt - start_dt).total_seconds())
            if min_diff is None or diff < min_diff:
                min_diff = diff
                closest_index = idx

        if closest_index is None:
            return Response({"error": "No matching times found"}, status=status.HTTP_404_NOT_FOUND)

        if current_stop_index is not None:
            try:
                current_stop_index = int(current_stop_index)
            except ValueError:
                return Response({"error": "current_stop_index must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

            stops_list = list(stop_times.items())
            result = {}

            if 0 <= current_stop_index < len(stops_list):
                stop_name, stop_data = stops_list[current_stop_index]
                expected_time_str = stop_data["times"][closest_index]
                expected_time = datetime.strptime(expected_time_str, "%H:%M").time()

                extra = {}

                if current_stop_index == len(stops_list) - 1:
                    extra = {"terminus": "true"}

                result["current_stop"] = {
                    "stop_name": stop_name,
                    "expected_time": expected_time.strftime("%H:%M:%S"),
                    **extra
                }

            next_index = current_stop_index + 1
            if next_index < len(stops_list):
                stop_name, stop_data = stops_list[next_index]
                expected_time_str = stop_data["times"][closest_index]
                expected_time = datetime.strptime(expected_time_str, "%H:%M").time()

                extra = {}

                if current_stop_index == len(stops_list) - 2:
                    extra = {"terminus_is_next": "true"}

                result["next_stop"] = {
                    "stop_name": stop_name,
                    "expected_time": expected_time.strftime("%H:%M:%S"),
                    **extra
                }

            return Response(result)

        # Default: return all stops
        output = []
        for stop_name, stop_data in stop_times.items():
            expected_time_str = stop_data["times"][closest_index]
            expected_time = datetime.strptime(expected_time_str, "%H:%M").time()
            output.append({
                "stop_name": stop_name,
                "expected_time": expected_time.strftime("%H:%M:%S"),
            })

        return Response(output)

