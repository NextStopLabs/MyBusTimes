from django.shortcuts import render
from django.core.cache import cache
from main.models import featureToggle
from rest_framework import generics, permissions, viewsets, status, filters
import re
from rest_framework.pagination import LimitOffsetPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.db.models.functions import Lower
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse, Http404
from django.views import View
from mybustimes.permissions import ReadOnly
from .models import *
from .filters import *
from .serializers import *
from fleet.models import MBTOperator, group as OperatorGroup
from collections import defaultdict
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
import json
import logging

logger = logging.getLogger(__name__)

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

        return queryset.prefetch_related(
                'route_operators',
                'linked_route',
                'related_route',
                'service_updates',
                'service_updates__effected_route'
            )

class groupRoutesListView(routesListView):
    def get_queryset(self):
        operator_group = get_object_or_404(OperatorGroup, group_name=self.kwargs["group_name"])
        return super().get_queryset().filter(route_operators__group=operator_group).distinct()
    
class routeStops(View):
    def get(self, request, pk):
        direction = request.GET.get("direction", "inbound").lower()
        if direction not in ("inbound", "outbound"):
            return JsonResponse({"error": "Invalid direction"}, status=400)

        inbound_flag = direction == "inbound"

        # Only load what you actually need
        try:
            route_instance = (
                route.objects
                .only("id", "route_details")
                .get(pk=pk)
            )
        except route.DoesNotExist:
            raise Http404("Route not found")

        route_stop = (
            routeStop.objects
            .only("stops", "snapped_route")
            .filter(route_id=pk, inbound=inbound_flag)
            .first()
        )

        if not route_stop:
            return JsonResponse({
                "has_snapped_route": False,
                "stops": [],
                "snapped_route": [],
                "route_colour": route_instance.route_details.get("route_colour", "#2f80ed"),
            })

        # --- HARD LIMITS (critical) ---
        MAX_STOPS = 500
        MAX_ROUTE_POINTS = 2000

        # Handle stops safely
        stops = route_stop.stops or []
        if isinstance(stops, list) and len(stops) > MAX_STOPS:
            stops = stops[:MAX_STOPS]

        # Handle snapped route WITHOUT full expansion
        snapped_route = []

        if route_stop.snapped_route:
            raw = route_stop.snapped_route

            # ⚠️ Do NOT fully json.loads huge payloads blindly
            try:
                parsed = json.loads(raw)

                if isinstance(parsed, list) and len(parsed) > MAX_ROUTE_POINTS:
                    # Downsample instead of slicing blindly
                    step = max(1, len(parsed) // MAX_ROUTE_POINTS)
                    snapped_route = parsed[::step]
                else:
                    snapped_route = parsed

            except (ValueError, TypeError) as e:
                logger.debug("Failed to parse snapped_route for routeStop %s: %s", getattr(route_stop, 'pk', None), e)
                snapped_route = []

        output = {
            "has_snapped_route": bool(snapped_route),
            "stops": stops,
            "snapped_route": snapped_route,
            "route_colour": route_instance.route_details.get("route_colour", "#2f80ed"),
        }

        return JsonResponse(output)

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

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        # Build a single operator_code -> name map so the serializer doesn't
        # issue one query per operator code per row.
        try:
            ctx['_operator_code_map'] = dict(
                MBTOperator.objects.values_list('operator_code', 'operator_name')
            )
        except Exception:
            logger.debug("Failed to build operator code map", exc_info=True)
            ctx['_operator_code_map'] = {}
        return ctx

    def get_queryset(self):
        return timetableEntry.objects.select_related('route').prefetch_related('day_type')

class dayTypeListView(generics.ListCreateAPIView):
    queryset = dayType.objects.all()
    serializer_class = dayTypeSerializer
    permission_classes = [ReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = dayTypeFilter

class boardCategoryListView(generics.ListAPIView):
    """API endpoint for board categories.

    Supports filtering by operator (operator=id) and search on name (search=term).
    Results are ordered by name for predictable display.
    """
    serializer_class = boardCategorySerializer
    permission_classes = [ReadOnly]
    pagination_class = LimitOffsetPagination
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_fields = ['operator']
    search_fields = ['name']

    def get_queryset(self):
        qs = board_category.objects.all()
        operator = self.request.query_params.get('operator')
        if operator:
            qs = qs.filter(operator__id=operator)

        # Let DRF/DjangoFilterBackend/SearchFilter do their work first, then sort in Python if needed
        # This ensures we always return a QuerySet for filtering/searching, and only sort after filtering
        qs = qs.order_by('name')  # fallback ordering for DB
        return qs

    def filter_queryset(self, queryset):
        # Use default filtering/searching first
        queryset = super().filter_queryset(queryset)

        # Now apply numeric-aware ordering in Python
        def parse_name_key(name):
            route_num = (name or '').upper()

            normal = re.match(r'^([0-9]+)$', route_num)
            xprefix = re.match(r'^X([0-9]+)$', route_num)
            suffix = re.match(r'^([0-9]+)([A-Z]+)$', route_num)
            other = re.match(r'^([A-Z]+)([0-9]+)$', route_num)

            if normal:
                return (int(normal.group(1)), 0, route_num)
            elif suffix:
                return (int(suffix.group(1)), 1, route_num)
            elif xprefix:
                return (int(xprefix.group(1)), 2, route_num)
            elif other:
                match = re.match(r"([A-Za-z]+)([0-9]+)", route_num)
                if match:
                    prefix, number = match.groups()
                    number = int(number)
                else:
                    prefix, number = route_num, float('inf')
                return (float('inf'), 3, prefix, number)
            else:
                return (float('inf'), 4, route_num)

        try:
            items = list(queryset)
            items.sort(key=lambda c: parse_name_key(c.name))
            return items
        except Exception:
            logger.debug("Error sorting board categories, falling back to name ordering", exc_info=True)
            return queryset

class stopRouteSearchView(APIView):
    def get(self, request):
        stop_name = request.query_params.get('stop', '').strip()
        day = request.query_params.get('day', '').strip()

        if not stop_name:
            return Response({"error": "Missing 'stop' query parameter."}, status=status.HTTP_400_BAD_REQUEST)

        all_entries = (
            timetableEntry.objects
            .select_related('route')
            .prefetch_related('day_type', 'route__route_operators')
            .only(
                'id', 'route', 'stop_times', 'inbound', 'circular',
                'route__id', 'route__route_num', 'route__route_name',
                'route__inbound_destination', 'route__outbound_destination'
            )
        )
        if day:
            all_entries = all_entries.filter(day_type__name=day).distinct()

        route_timings = defaultdict(list)

        for entry in all_entries:
            try:
                stop_times_data = json.loads(entry.stop_times or "{}")
            except json.JSONDecodeError:
                continue

            if stop_name not in stop_times_data:
                continue

            time_at_stop = stop_times_data[stop_name]
            day_names = [d.name for d in entry.day_type.all()]

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
            return Response(
                {"error": "Missing 'stop' query parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )

        stop_name_lower = stop_name.lower()

        # HARD SAFETY LIMITS (prevents OOM no matter what)
        MAX_ENTRIES_TO_SCAN = 2000
        MAX_MATCHED_ROUTES = 200

        queryset = (
            timetableEntry.objects
            .filter(stop_times__icontains=stop_name)  # 🔥 critical: filter in DB first
            .select_related('route')
            .only(
                'id', 'route', 'stop_times',
                'route__id', 'route__route_num', 'route__route_name',
                'route__inbound_destination', 'route__outbound_destination'
            )[:MAX_ENTRIES_TO_SCAN]  # 🔥 hard cap
        )

        matched_route_ids = set()

        # STREAM results instead of loading everything into memory
        for entry in queryset.iterator(chunk_size=200):
            if len(matched_route_ids) >= MAX_MATCHED_ROUTES:
                break

            stop_times_raw = entry.stop_times
            if not stop_times_raw:
                continue

            # Parse JSON safely
            if isinstance(stop_times_raw, str):
                try:
                    stop_times_data = json.loads(stop_times_raw)
                except json.JSONDecodeError:
                    continue
            elif isinstance(stop_times_raw, dict):
                stop_times_data = stop_times_raw
            else:
                continue

            # Check if stop exists in this entry
            found = False
            for key in stop_times_data.keys():
                base_key = key.split('_idx_')[0].strip().lower()
                if base_key == stop_name_lower:
                    found = True
                    break

            if not found:
                continue

            matched_route_ids.add(entry.route.id)

        if not matched_route_ids:
            return Response([])

        # Fetch only the routes we actually need
        routes_qs = (
            route.objects
            .filter(id__in=matched_route_ids)
            .prefetch_related('route_operators')
        )

        response_data = []
        for r in routes_qs:
            response_data.append({
                'route_id': r.id,
                'route_num': r.route_num,
                'route_name': r.route_name,
                'inbound_destination': r.inbound_destination,
                'outbound_destination': r.outbound_destination,
                'route_operators': operatorFleetSerializer(
                    r.route_operators.all(),
                    many=True
                ).data,
            })

        return Response(response_data)
    
class stopUpcomingTripsView(APIView):

    def get(self, request):
        stop_name = request.query_params.get('stop', '').strip()
        day = request.query_params.get('day', '').strip()
        current_time_str = request.query_params.get('current_time', '').strip()
        try:
            limit = int(request.query_params.get('limit', 5))
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid 'limit' parameter. Must be an integer."},
                status=status.HTTP_400_BAD_REQUEST
            )
        date_str = request.query_params.get('date', '').strip()

        if not stop_name:
            return Response(
                {"error": "Missing 'stop' query parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            current_time = datetime.strptime(current_time_str, "%H:%M").time() if current_time_str else None
        except ValueError:
            return Response(
                {"error": "Invalid 'current_time' format. Use HH:MM."},
                status=status.HTTP_400_BAD_REQUEST
            )

        date_filter = None
        if date_str:
            try:
                date_filter = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": "Invalid 'date' format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        stop_name_lower = stop_name.lower()

        # 🔒 HARD LIMITS (protect server)
        MAX_ENTRIES = 2000
        MAX_TRIPS_SCAN = 5000

        queryset = (
            timetableEntry.objects
            .filter(stop_times__icontains=stop_name)  # 🔥 critical
            .select_related('route')
            .prefetch_related('day_type', 'route__route_operators')
            .only(
                'id', 'route', 'stop_times', 'inbound', 'circular', 'operator_schedule',
                'start_date', 'end_date',
                'route__id', 'route__route_num',
                'route__inbound_destination', 'route__outbound_destination'
            )[:MAX_ENTRIES]
        )

        # Build operator map ONLY from filtered dataset
        operator_codes = set()

        for entry in queryset.iterator(chunk_size=200):
            if isinstance(entry.operator_schedule, list):
                operator_codes.update([c for c in entry.operator_schedule if c])

            for op in entry.route.route_operators.all():
                if op.operator_code:
                    operator_codes.add(op.operator_code)

        operator_map = {
            op.operator_code.lower(): op
            for op in MBTOperator.objects.annotate(code_lower=Lower('operator_code')).filter(
                code_lower__in={c.lower() for c in operator_codes}
            )
            if op.operator_code
        }

        upcoming_trips = []
        scanned_trips = 0

        for entry in queryset.iterator(chunk_size=200):

            if len(upcoming_trips) >= limit:
                break

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
                base_key = key.split('_idx_')[0].strip().lower()
                if base_key == stop_name_lower:
                    matched_key = key
                    break

            if not matched_key:
                continue

            valid_days = [d.name for d in entry.day_type.all()]
            if day and day not in valid_days:
                continue

            if date_filter:
                if entry.start_date and entry.start_date > date_filter:
                    continue
                if entry.end_date and entry.end_date < date_filter:
                    continue

            stop_data = stop_times_data.get(matched_key, {})
            times = stop_data.get('times', [])

            operator_schedule = entry.operator_schedule if isinstance(entry.operator_schedule, list) else []
            route_ops = list(entry.route.route_operators.all())

            for idx, time_str in enumerate(times):

                if scanned_trips >= MAX_TRIPS_SCAN:
                    break

                scanned_trips += 1

                try:
                    trip_time = datetime.strptime(time_str.strip(), "%H:%M").time()
                except ValueError:
                    continue

                if current_time and trip_time < current_time:
                    continue

                operator_string = (
                    operator_schedule[idx]
                    if idx < len(operator_schedule)
                    else (route_ops[0].operator_code if route_ops else None)
                )

                operator_obj = operator_map.get((operator_string or '').lower())

                operator_data = {
                    'operator_code': operator_obj.operator_code if operator_obj else None,
                    'operator_name': operator_obj.operator_name if operator_obj else (operator_string or "Unknown"),
                    'operator_slug': operator_obj.operator_slug if operator_obj else None,
                }

                if entry.inbound or entry.route.outbound_destination is None:
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

                if len(upcoming_trips) >= limit:
                    break

        upcoming_trips.sort(key=lambda x: x['time'])

        return Response(upcoming_trips[:limit])

class timetableDaysView(APIView):
    permission_classes = [ReadOnly]

    def get(self, request, *args, **kwargs):
        queryset = timetableEntry.objects.select_related('route').prefetch_related('day_type')

        # Optional: apply filters if using DjangoFilterBackend
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)

        merged = {}
        for entry in queryset:
            route_id = entry.route.id
            day_names = [d.name for d in entry.day_type.all()]
            if route_id not in merged:
                merged[route_id] = {
                    'route': entry.route,
                    'day_type': set(day_names)
                }
            else:
                merged[route_id]['day_type'].update(day_names)

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
    serializer_class = dutySerializer
    permission_classes = [ReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = dutyFilter

    def get_queryset(self):
        return duty.objects.prefetch_related(
            'duty_day', 'duty_trips', 'duty_trips__route'
        ).select_related('duty_operator')

class dutyDetailView(generics.RetrieveAPIView):
    serializer_class = dutySerializer
    permission_classes = [ReadOnly]

    def get_queryset(self):
        return duty.objects.prefetch_related(
            'duty_day', 'duty_trips', 'duty_trips__route'
        ).select_related('duty_operator')
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
        return get_object_or_404(transitAuthoritiesColour, authority_code=code)


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

def stop(request):
    response = feature_enabled(request, "view_stop")
    if response:
        return response
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
    
    entries = (
        timetableEntry.objects
        .filter(route_id=route_id)
        .select_related('route')
        .prefetch_related('day_type')
    )
    data = {}
    for entry in entries:
        direction = "Inbound" if entry.inbound else "Outbound"
        if entry.circular or entry.route.outbound_destination is None:
            direction = "Circular"
        day_names = [d.name for d in entry.day_type.all()]
        data[entry.id] = f"{entry.route.route_num} - {direction} - ({', '.join(day_names)})"
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

