from datetime import date
import re
import os
import json

from itertools import groupby
from django.shortcuts import render, redirect, get_object_or_404
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, permissions, viewsets, status
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.urls import reverse
from .models import *
from routes.models import *
from .filters import *
from .serializers import *
from routes.serializers import *
from mybustimes.permissions import ReadOnlyOrAuthenticatedCreate
from rest_framework.response import Response
from rest_framework.views import APIView
from functools import cmp_to_key
from collections import defaultdict
from itertools import chain
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.forms.models import model_to_dict

class fleetListView(generics.ListCreateAPIView):
    queryset = fleet.objects.all()
    serializer_class = fleetSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = fleetsFilter

class fleetDetailView(generics.RetrieveAPIView):
    queryset = fleet.objects.all()
    serializer_class = fleetSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = fleetsFilter

class fleetUpdateView(generics.UpdateAPIView):
    queryset = fleet.objects.all()
    serializer_class = fleetSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

class fleetDeleteView(generics.DestroyAPIView):
    queryset = fleet.objects.all()
    serializer_class = fleetSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

class fleetCreateView(generics.CreateAPIView):
    queryset = fleet.objects.all()
    serializer_class = fleetSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        instance = self.get_queryset().get(pk=response.data['id'])
        full_data = self.get_serializer(instance).data
        return Response(full_data, status=status.HTTP_201_CREATED)

class fleetEditUpVote(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            change = fleetChange.objects.get(pk=pk)
        except fleetChange.DoesNotExist:
            return Response({'error': 'Change not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user in change.voters.all():
            return Response({'error': 'You have already voted.'}, status=status.HTTP_400_BAD_REQUEST)

        change.up_vote += 1
        change.voters.add(request.user)
        change.save()

        return Response({'message': 'Upvoted successfully.', 'up_votes': change.up_vote})

class fleetEditDownVote(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            change = fleetChange.objects.get(pk=pk)
        except fleetChange.DoesNotExist:
            return Response({'error': 'Change not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user in change.voters.all():
            return Response({'error': 'You have already voted.'}, status=status.HTTP_400_BAD_REQUEST)

        change.down_vote += 1
        change.voters.add(request.user)
        change.save()

        return Response({'message': 'Downvoted successfully.', 'down_votes': change.down_vote})

class updateListView(generics.ListCreateAPIView):
    serializer_class = companyUpdateSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = companyUpdateFilter

    def get_queryset(self):
        operator_name = self.kwargs.get('name')
        if operator_name:
            return companyUpdate.objects.filter(operator__operator_name=operator_name)
        return companyUpdate.objects.all()

class updateDetailView(generics.RetrieveAPIView):
    serializer_class = companyUpdateSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = companyUpdateFilter

    def get_queryset(self):
        operator_name = self.kwargs.get('name')
        if operator_name:
            return companyUpdate.objects.filter(operator__operator_name=operator_name)
        return companyUpdate.objects.all()

class operatorListView(generics.ListCreateAPIView):
    queryset = MBTOperator.objects.all()
    serializer_class = operatorSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = operatorsFilter

class operatorDetailView(RetrieveAPIView):
    queryset = MBTOperator.objects.all()
    serializer_class = operatorSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = operatorsFilter

    def retrieve(self, request, *args, **kwargs):
        operator_name = self.kwargs.get('name')
        try:
            operator = MBTOperator.objects.get(operator_name=operator_name)
            serializer = self.get_serializer(operator)
            return Response(serializer.data)
        except MBTOperator.DoesNotExist:
            return Response({"message": "Operator not found", "found": False}, status=status.HTTP_200_OK)

class operatorUpdateView(UpdateAPIView):
    queryset = MBTOperator.objects.all()
    serializer_class = operatorSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = operatorsFilter
    lookup_field = 'operator_name'  # lookup by operator_name field

    def get_object(self):
        operator_name = self.kwargs.get('name')
        try:
            return MBTOperator.objects.get(operator_name=operator_name)
        except MBTOperator.DoesNotExist:
            return None

    def update(self, request, *args, **kwargs):
        operator = self.get_object()
        if not operator:
            return Response({"message": "Operator not found", "found": False}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(operator, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

class liveriesListView(generics.ListCreateAPIView):
    queryset = liverie.objects.filter(published=True)
    serializer_class = liveriesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = liveriesFilter 

class liveriesDetailView(generics.RetrieveAPIView):
    queryset = liverie.objects.filter(published=True)
    serializer_class = liveriesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = liveriesFilter 

class organisationsListView(generics.ListCreateAPIView):
    queryset = organisation.objects.all()
    serializer_class = organisationsSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = organisationFilter

class organisationsDetailView(generics.RetrieveAPIView):
    queryset = organisation.objects.all()
    serializer_class = organisationsSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = organisationFilter

class groupsListView(generics.ListCreateAPIView):
    queryset = group.objects.all()
    serializer_class = groupsSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = groupFilter

class groupsDetailView(generics.RetrieveAPIView):
    queryset = group.objects.all()
    serializer_class = groupsSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = groupFilter

class fleetChangesListView(generics.ListCreateAPIView):
    queryset = fleetChange.objects.all()
    serializer_class = fleetChangesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = historyFilter

class fleetChangesDetailView(generics.RetrieveAPIView):
    queryset = fleetChange.objects.all()
    serializer_class = fleetChangesSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = historyFilter

class helperListView(generics.ListCreateAPIView):
    queryset = helper.objects.all()
    serializer_class = helperSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = helperFilter

class helperDetailView(generics.RetrieveAPIView):
    queryset = helper.objects.all()
    serializer_class = helperSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = helperFilter

class helperPermsListView(generics.ListCreateAPIView):
    queryset = helperPerm.objects.all()
    serializer_class = helperPermSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = helperPermFilter

class helperPermsDetailView(generics.RetrieveAPIView):
    queryset = helperPerm.objects.all()
    serializer_class = helperPermSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = helperPermFilter

class typeListView(generics.ListCreateAPIView):
    queryset = vehicleType.objects.filter(active=True).order_by('type_name')
    serializer_class = typeSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = typeFilter

class typeDetailView(generics.RetrieveAPIView):
    queryset = vehicleType.objects.filter(active=True).order_by('type_name')
    serializer_class = typeSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate] 
    filter_backends = (DjangoFilterBackend,)
    filterset_class = typeFilter

class operatorTypeListView(generics.ListCreateAPIView):
    queryset = operatorType.objects.all()
    serializer_class = operatorTypeSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

class operatorTypeDetailView(generics.RetrieveAPIView):
    queryset = operatorType.objects.all()
    serializer_class = operatorTypeSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]

class operatorNameListView(generics.ListCreateAPIView):
    queryset = MBTOperator.objects.all()
    serializer_class = operatorNameSerializer
    permission_classes = [ReadOnlyOrAuthenticatedCreate]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = operatorNameFilter

#templates
def parse_route_key(route):
    route_num = getattr(route, 'route_num', '')

    # Match patterns
    normal = re.match(r'^(\d+)$', route_num)
    suffix = re.match(r'^(\d+)([A-Za-z]+)$', route_num)
    xprefix = re.match(r'^X(\d+)$', route_num, re.IGNORECASE)
    other = re.match(r'^[A-Za-z]+(\d+)$', route_num)

    if normal:
        return (0, int(normal.group(1)), route_num.upper())
    elif suffix:
        return (1, int(suffix.group(1)), route_num.upper())
    elif xprefix:
        return (2, int(xprefix.group(1)), route_num.upper())
    elif other:
        return (3, int(other.group(1)), route_num.upper())
    else:
        return (4, float('inf'), route_num.upper()) 

def get_unique_linked_routes(initial_routes):
    route_set = set(initial_routes)

    for r in initial_routes:
        route_set.update(r.linked_route.all())
        # related routes are NOT added into this set intentionally

    route_map = {r.id: r for r in route_set}
    graph = {r.id: set() for r in route_set}

    # Only build edges based on 'linked' routes
    for r in route_set:
        for linked in r.linked_route.all():
            if linked.id in graph:
                graph[r.id].add(linked.id)
                graph[linked.id].add(r.id)

    visited = set()
    groups = []

    def dfs(route_id, group):
        if route_id in visited or route_id not in route_map:
            return
        visited.add(route_id)
        group.append(route_map[route_id])
        for neighbor in graph.get(route_id, []):
            dfs(neighbor, group)

    for r in route_set:
        if r.id not in visited:
            group = []
            dfs(r.id, group)
            if group:
                primary = next((g for g in group if g in initial_routes), group[0])
                groups.append({
                    "primary": primary,
                    "linked": [r for r in group if r != primary]
                })

    return sorted(groups, key=lambda g: parse_route_key(g["primary"]))

def get_helper_permissions(user, operator):
    if not user.is_authenticated:
        return []

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

def generate_tabs(active, operator, show_withdrawn=None):

    if show_withdrawn is None:
        vehicle_qs = fleet.objects.filter(operator=operator, in_service=True)
    else:
        vehicle_qs = fleet.objects.filter(operator=operator)
    vehicle_count = vehicle_qs.count()

    duty_count = duty.objects.filter(duty_operator=operator).count()
    route_count = route.objects.filter(route_operators=operator).count()
    update_count = companyUpdate.objects.filter(operator=operator).count()

    tabs = []

    if route_count > 0:
        tab_name = f"{route_count} routes" if active == "routes" else "Routes"
        tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_name}/", "active": active == "routes"})

    tab_name = f"{vehicle_count} vehicles" if active == "vehicles" else "Vehicles"
    tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_name}/vehicles/", "active": active == "vehicles"})

    if duty_count > 0:
        tab_name = f"{duty_count} duties" if active == "duties" else "Duties"
        tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_name}/duties/", "active": active == "duties"})

    if update_count > 0:
        tab_name = f"{update_count} updates" if active == "updates" else "Updates"
        tabs.append({"name": tab_name, "url": f"/operator/{operator.operator_name}/updates/", "active": active == "updates"})

    return tabs

def operator(request, operator_name):
    try:
        operator = MBTOperator.objects.get(operator_name=operator_name)
        routes = list(route.objects.filter(route_operators=operator).order_by('route_num'))
        transit_authority = operator.operator_details.get('transit_authority') or operator.operator_details.get('transit_authorities')
    except MBTOperator.DoesNotExist:
        return render(request, '404.html', status=404)

    regions = operator.region.all()

    transit_authority_details = None
    if transit_authority:
        # if transit_authority contains multiple comma-separated authorities, pick the first or handle accordingly
        first_authority_code = transit_authority.split(",")[0].strip()
        # Get transit authority colours from your model transitAuthoritiesColour (not route)
        transit_authority_details = transitAuthoritiesColour.objects.filter(authority_code=first_authority_code).first()

    helper_permissions = get_helper_permissions(request.user, operator)
    unique_routes = get_unique_linked_routes(routes)
    unique_routes = sorted(unique_routes, key=lambda x: parse_route_key(x['primary']))

    for r in routes:
        print(r.route_name)  # ✅ This also works


    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': operator_name, 'url': f'/operator/{operator_name}/'}]

    tabs = generate_tabs("routes", operator)


    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'routes': unique_routes,
        'regions': regions,
        'helper_permissions': helper_permissions,
        'transit_authority_details': transit_authority_details,
        'tabs': tabs,
    }
    return render(request, 'operator.html', context)

def route_detail(request, operator_name, route_id):
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    days = dayType.objects.all()

    selected_day_id = request.GET.get('day')
    selectedDay = None
    if selected_day_id:
        try:
            selectedDay = dayType.objects.get(id=selected_day_id)
        except dayType.DoesNotExist:
            selectedDay = None

    serialized_route = routesSerializer(route_instance).data
    full_route_num = serialized_route.get('full_searchable_name', '')

    helper_permissions = get_helper_permissions(request.user, operator)

    # Breadcrumbs
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': route_instance.route_num or 'Route Details', 'url': f'/operator/{operator_name}/route/{route_id}/'}
    ]

    # Operators
    mainOperator = next((op for op in route_instance.route_operators.all() if op.operator_name == operator_name), None)
    otherOperators = [op for op in route_instance.route_operators.all() if op.operator_name != operator_name]
    allOperators = [mainOperator] + otherOperators if mainOperator else otherOperators

    # Timetable entries
    timetable_entries = timetableEntry.objects.filter(route=route_instance, day_type=selectedDay).order_by('stop_times__stop_time')
    timetableData = timetable_entries.first().stop_times if timetable_entries.exists() else {}

    flat_schedule = list(chain.from_iterable(
        entry.operator_schedule for entry in timetable_entries
    )) if timetable_entries.exists() else []

    groupedSchedule = []
    for code, group in groupby(flat_schedule):
        count = len(list(group))
        try:
            op = MBTOperator.objects.get(operator_code=code)
            name = op.operator_name
        except MBTOperator.DoesNotExist:
            name = code
        groupedSchedule.append({
            "code": code,
            "name": name,
            "colspan": count
        })

    current_updates = route_instance.service_updates.all().filter(end_date__gte=date.today())

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'full_route_num': full_route_num,
        'route': route_instance,
        'helperPermsData': helper_permissions,  # renamed for template match
        'allOperators': allOperators,
        'timetableData': timetableData if isinstance(timetableData, dict) else {},
        'stops': list(timetableData.keys()) if isinstance(timetableData, dict) else [],
        'groupedSchedule': groupedSchedule,
        'uniqueOperators': list({group['code'] for group in groupedSchedule}),
        'otherRoutes': route.objects.filter(linked_route__id=route_instance.id),
        'days': days,
        'selectedDay': selectedDay,
        'current_updates': current_updates,
        'transit_authority_details': getattr(operator.operator_details, 'transit_authority_details', None),
    }

    return render(request, 'route_detail.html', context)

def vehicles(request, operator_name):
    withdrawn = request.GET.get('withdrawn')

    show_withdrawn = withdrawn and withdrawn.lower() == 'true'

    try:
        operator = MBTOperator.objects.get(operator_name=operator_name)
        if show_withdrawn:
            vehicles = fleet.objects.filter(operator=operator).order_by('fleet_number')  # all vehicles
        else:
            vehicles = fleet.objects.filter(operator=operator, in_service=True).order_by('fleet_number')  # only in-service

        # Serialize the queryset
        serialized_vehicles = fleetSerializer(vehicles, many=True)

    except MBTOperator.DoesNotExist:
        return render(request, '404.html', status=404)

    regions = operator.region.all()

    helper_permissions = get_helper_permissions(request.user, operator)

    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': operator_name, 'url': f'/operator/{operator_name}/'}, {'name': 'Vehicles', 'url': f'/operator/{operator_name}/vehicles/'}]

    tabs = generate_tabs("vehicles", operator, show_withdrawn)

    def has_non_null_field(data_list, field):
        return any(item.get(field) not in [None, '', [], {}] for item in data_list)

    show_livery = has_non_null_field(serialized_vehicles.data, 'livery') or has_non_null_field(serialized_vehicles.data, 'colour')
    show_branding = (
        has_non_null_field(serialized_vehicles.data, 'branding') and
        has_non_null_field(serialized_vehicles.data, 'livery')
    )
    show_prev_reg = has_non_null_field(serialized_vehicles.data, 'prev_reg')
    show_name = has_non_null_field(serialized_vehicles.data, 'name')
    show_depot = has_non_null_field(serialized_vehicles.data, 'depot')
    show_features = has_non_null_field(serialized_vehicles.data, 'features')


    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'vehicles': serialized_vehicles.data,
        'helper_permissions': helper_permissions,
        'tabs': tabs,
        'regions': regions,
        'show_livery': show_livery,
        'show_branding': show_branding,
        'show_prev_reg': show_prev_reg,
        'show_name': show_name,
        'show_depot': show_depot,
        'show_features': show_features,
    }
    return render(request, 'vehicles.html', context)

def vehicle_detail(request, operator_name, vehicle_id):
    try:
        operator = MBTOperator.objects.get(operator_name=operator_name)
        vehicle = fleet.objects.get(id=vehicle_id, operator=operator)
    except (MBTOperator.DoesNotExist, fleet.DoesNotExist):
        return render(request, '404.html', status=404)

    helper_permissions = get_helper_permissions(request.user, operator)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Vehicles', 'url': f'/operator/{operator_name}/vehicles/'},
        {'name': f'{vehicle.fleet_number} - {vehicle.reg}', 'url': f'/operator/{operator_name}/vehicles/{vehicle_id}/'}
    ]

    tabs = generate_tabs("vehicles", operator)

    serialized_vehicle = fleetSerializer(vehicle)  # single object, no many=True

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'vehicle': serialized_vehicle.data,
        'helper_permissions': helper_permissions,
        'tabs': tabs,
    }
    return render(request, 'vehicle_detail.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def vehicle_edit(request, operator_name, vehicle_id):
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    vehicle = get_object_or_404(fleet, id=vehicle_id, operator=operator)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Buses' not in userPerms and not request.user.is_superuser:
        return redirect(f'/operator/{operator_name}/vehicles/{vehicle_id}/')

    # Load related data needed for selects and checkboxes
    operators = MBTOperator.objects.all()
    types = vehicleType.objects.all()
    liveries_list = liverie.objects.all()

    features_path = os.path.join(settings.MEDIA_ROOT, 'JSON', 'features.json')
    with open(features_path, 'r') as f:
        features_json = json.load(f)
        features_list = features_json.get("features", [])

    if request.method == "POST":
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

        try:
            vehicle.livery = liverie.objects.get(id=request.POST.get('livery'))
        except liverie.DoesNotExist:
            vehicle.livery = None

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
        return redirect('vehicle_detail', operator_name=operator_name, vehicle_id=vehicle_id)

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
            {'name': operator_name, 'url': f'/operator/{operator_name}/'},
            {'name': 'Vehicles', 'url': f'/operator/{operator_name}/vehicles/'},
            {'name': f'{vehicle.fleet_number} - {vehicle.reg}', 'url': f'/operator/{operator_name}/vehicles/{vehicle_id}/edit/'}
        ]

        tabs = []  # populate as needed or reuse your generate_tabs method

        context = {
            'fleetData': vehicle,
            'operatorData': operators,
            'typeData': types,
            'liveryData': liveries_list,
            'features': features_list,
            'userData': user_data,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
        }
        return render(request, 'edit.html', context)
    
@login_required
@require_http_methods(["GET", "POST"])
def operator_edit(request, operator_name):
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)

    # Make these available to both POST and GET
    groups = group.objects.filter(Q(group_owner=request.user) | Q(private=False))
    organisations = organisation.objects.filter(organisation_owner=request.user)
    operator_types = operatorType.objects.all()

    regions = region.objects.all().order_by('region_country', 'region_name')
    grouped_regions = defaultdict(list)
    for r in regions:
        grouped_regions[r.region_country].append(r)
    regionData = dict(grouped_regions)

    if request.user != operator.owner and not request.user.is_superuser:
        return redirect(f'/operator/{operator_name}')

    if request.method == "POST":
        operator.operator_name = request.POST.get('operator_name', '').strip()
        operator.operator_code = request.POST.get('operator_code', '').strip()
        region_ids = request.POST.getlist('operator_region')
        operator.region.set(region_ids)

        operator_details = {
            'website': request.POST.get('website', '').strip(),
            'twitter': request.POST.get('twitter', '').strip(),
            'game': request.POST.get('game', '').strip(),
            'type': request.POST.get('type', '').strip(),
            'transit_authorities': request.POST.get('transit_authorities', '').strip(),
        }

        operator.operator_details = operator_details
        operator.save()

        messages.success(request, "Operator updated successfully.")
        return redirect(f'/operator/{operator_name}')

    else:
        # GET request — prepare context for the form
        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator_name, 'url': f'/operator/{operator_name}/'},
            {'name': 'Edit Operator', 'url': f'/operator/{operator_name}/edit/'}
        ]

        tabs = generate_tabs("routes", operator)

        context = {
            'operator': operator,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
            'groups': groups,
            'organisations': organisations,
            'regionData': regionData,
            'operator_types': operator_types,
        }
        return render(request, 'edit_operator.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def vehicle_add(request, operator_name):
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Buses' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add a bus for this operator.")
        return redirect(f'/operator/{operator_name}/vehicles/')

    # Load dropdown/related data
    operators = MBTOperator.objects.all()
    types = vehicleType.objects.all()
    liveries_list = liverie.objects.all()

    features_path = os.path.join(settings.MEDIA_ROOT, 'JSON', 'features.json')
    with open(features_path, 'r') as f:
        features_json = json.load(f)
        features_list = features_json.get("features", [])

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

        vehicle.features = features_selected
        vehicle.save()

        messages.success(request, "Vehicle added successfully.")
        return redirect(f'/operator/{operator_name}/vehicles/')

    else:
        # GET: Prepare blank form
        vehicle = fleet()  # Blank for add form

        features_selected = []

        user_data = [request.user]

        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': operator_name, 'url': f'/operator/{operator_name}/'},
            {'name': 'Vehicles', 'url': f'/operator/{operator_name}/vehicles/'},
            {'name': 'Add Vehicle', 'url': f'/operator/{operator_name}/vehicles/add/'}
        ]

        tabs = []

        context = {
            'fleetData': vehicle,
            'operatorData': operators,
            'typeData': types,
            'liveryData': liveries_list,
            'features': features_list,
            'userData': user_data,
            'breadcrumbs': breadcrumbs,
            'tabs': tabs,
        }
        return render(request, 'add.html', context)
    
@login_required
@require_http_methods(["GET", "POST"])
def route_add(request, operator_name):
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Routes' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add a route for this operator.")
        return redirect(f'/operator/{operator_name}/vehicles/')

    if request.method == "POST":
        # Extract form data
        route_num = request.POST.get('route_number')
        route_name = request.POST.get('route_name')
        inbound = request.POST.get('inbound_destination')
        outbound = request.POST.get('outbound_destination')
        other_dests = request.POST.get('other_destinations')
        school_service = request.POST.get('school_service') == 'on'

        # Related many-to-many fields
        linkable_routes_ids = request.POST.getlist('linkable_routes')
        related_routes_ids = request.POST.getlist('related_routes')
        payment_method_ids = request.POST.getlist('payment_methods')

        # Convert other destinations to list
        other_dest_list = [d.strip() for d in other_dests.split(',')] if other_dests else []

        # Build route_details
        route_details = {
            "route_colour": "var(--background-color)",
            "route_text_colour": "var(--text-color)",
            "details": {
                "school_service": str(school_service).lower(),
                "contactless": str('1' in payment_method_ids).lower(),
                "cash": str('2' in payment_method_ids).lower()
            }
        }

        # Create the route
        new_route = route.objects.create(
            route_num=route_num,
            route_name=route_name,
            inboud_destination=inbound,
            outboud_destination=outbound,
            other_destination=other_dest_list,
            route_details=route_details
        )
        new_route.route_operators.add(operator)

        if linkable_routes_ids:
            new_route.linked_route.set(route.objects.filter(id__in=linkable_routes_ids))
        if related_routes_ids:
            new_route.related_route.set(route.objects.filter(id__in=related_routes_ids))

        messages.success(request, "Route added successfully.")
        return redirect(f'/operator/{operator_name}/')

    # GET request
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Add Route', 'url': f'/operator/{operator_name}/add-route/'}
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
        'linkableAndRelatedRoutes': route.objects.all(),
        'paymentMethods': [
            MockPaymentMethod(1, 'Contactless'),
            MockPaymentMethod(2, 'Cash')
        ]
    }

    return render(request, 'add_route.html', context)
    
@login_required
@require_http_methods(["GET", "POST"])
def route_edit(request, operator_name, route_id):
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    has_inbound_stops = routeStop.objects.filter(route=route_instance, inbound=True).exists()
    has_outbound_stops = routeStop.objects.filter(route=route_instance, inbound=False).exists()
    is_circular = routeStop.objects.filter(route=route_instance, circular=True).exists()

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Routes' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route.")
        return redirect(f'/operator/{operator_name}/routes/')

    if request.method == "POST":
        # Extract form data
        route_num = request.POST.get('route_number')
        route_name = request.POST.get('route_name')
        inbound = request.POST.get('inbound_destination')
        outbound = request.POST.get('outbound_destination')
        other_dests = request.POST.get('other_destinations')
        school_service = request.POST.get('school_service') == 'on'

        # Related many-to-many fields
        linkable_routes_ids = request.POST.getlist('linkable_routes')
        related_routes_ids = request.POST.getlist('related_routes')
        payment_method_ids = request.POST.getlist('payment_methods')

        # Convert other destinations to list
        other_dest_list = [d.strip() for d in other_dests.split(',')] if other_dests else []

        # Build route_details
        route_details = {
            "route_colour": "var(--background-color)",
            "route_text_colour": "var(--text-color)",
            "details": {
                "school_service": str(school_service).lower(),
                "contactless": str('1' in payment_method_ids).lower(),
                "cash": str('2' in payment_method_ids).lower()
            }
        }

        # Update the route instance
        route_instance.route_num = route_num
        route_instance.route_name = route_name
        route_instance.inboud_destination = inbound
        route_instance.outboud_destination = outbound
        route_instance.other_destination = other_dest_list
        route_instance.route_details = route_details
        route_instance.save()

        # Update relationships
        route_instance.route_operators.set([operator])

        if linkable_routes_ids:
            route_instance.linked_route.set(route.objects.filter(id__in=linkable_routes_ids))
        else:
            route_instance.linked_route.clear()

        if related_routes_ids:
            route_instance.related_route.set(route.objects.filter(id__in=related_routes_ids))
        else:
            route_instance.related_route.clear()

        messages.success(request, "Route updated successfully.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    # GET request - Pre-fill existing data
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Edit Route', 'url': f'/operator/{operator_name}/route/{route_id}/edit/'}
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

    context = {
        'operatorData': operator,
        'userData': [request.user],
        'breadcrumbs': breadcrumbs,
        'linkableAndRelatedRoutes': route.objects.exclude(id=route_id),
        'paymentMethods': [
            MockPaymentMethod(1, 'Contactless'),
            MockPaymentMethod(2, 'Cash')
        ],
        'routeData': route_instance,
        'selectedLinkables': route_instance.linked_route.values_list('id', flat=True),
        'selectedRelated': route_instance.related_route.values_list('id', flat=True),
        'selectedPaymentMethods': selected_payment_ids,
        'has_inbound_stops': has_inbound_stops,
        'has_outbound_stops': has_outbound_stops,
        'is_circular': is_circular,
    }

    return render(request, 'edit_route.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def vehicle_delete(request, operator_name, vehicle_id):
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    vehicle = get_object_or_404(fleet, id=vehicle_id)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Buses' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this vehicle.")
        return redirect(f'/operator/{operator_name}/vehicles/')

    if request.method == "POST":
        vehicle.delete()
        messages.success(request, f"Vehicle '{vehicle.fleet_number or vehicle.reg or 'unnamed'}' deleted successfully.")
        return redirect(f'/operator/{operator_name}/vehicles/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': 'Vehicles', 'url': f'/operator/{operator_name}/vehicles/'},
        {'name': 'Delete Vehicle', 'url': f'/operator/{operator_name}/vehicle/edit/{vehicle.id}/delete/'}
    ]

    return render(request, 'confirm_delete.html', {
        'vehicle': vehicle,
        'operator': operator,
        'breadcrumbs': breadcrumbs
    })

@login_required
@require_http_methods(["GET", "POST"])
def create_operator(request):
    groups = group.objects.filter(Q(group_owner=request.user) | Q(private=False))
    organisations = organisation.objects.filter(organisation_owner=request.user)
    operator_types = operatorType.objects.all()
    games = game.objects.all()
    regions = region.objects.all().order_by('region_country', 'region_name')

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

        new_operator = MBTOperator.objects.create(
            operator_name=operator_name,
            operator_code=operator_code,
            owner=request.user,
            operator_group_id=operator_group_id if operator_group_id != '0' else None,
            organisation_id=operator_org_id if operator_org_id != '0' else None,
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

        messages.success(request, "Operator created successfully.")
        return redirect(f'/operator/{new_operator.operator_name}/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
    ]

    context = {
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
def route_timetable_options(request, operator_name, route_id):
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    all_timetables = timetableEntry.objects.filter(route=route_instance).prefetch_related('day_type').order_by('id')


    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Timetables' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route's timetable.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    # Get all days
    days = dayType.objects.all()

    if request.method == "POST":
        # Handle timetable editing logic here
        pass  # Placeholder for actual logic

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_name}/route/{route_id}/timetable/'}
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
def route_edit_stops(request, operator_name, route_id, direction):
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Stops' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route's stops.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    # Load existing stops for this route and direction
    try:
        existing_route_stops = routeStop.objects.get(route=route_instance, inbound=(direction == "inbound"))
        existing_stops = existing_route_stops.stops
    except routeStop.DoesNotExist:
        existing_stops = []

    if request.method == "POST":
        try:
            raw_data = request.POST.get("routeData")
            if not raw_data:
                raise ValueError("Missing routeData")

            parsed_stops = json.loads(raw_data)

            # Update or create routeStop record
            routeStop.objects.update_or_create(
                route=route_instance,
                inbound=(direction == "inbound"),
                defaults={
                    "circular": False,  # Adjust if needed
                    "stops": parsed_stops
                }
            )

            messages.success(request, "Stops updated successfully.")
            return redirect(f'/operator/{operator_name}/route/{route_id}/')

        except Exception as e:
            messages.error(request, f"Failed to update stops: {e}")
            return redirect(request.path)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_name}/route/{route_id}/timetable/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'route': route_instance,
        'helper_permissions': userPerms,
        'direction': direction,
        'existing_stops': existing_stops,  # Pass existing stops here
    }
    return render(request, 'route_add_route.html', context)

def route_map(request, operator_name, route_id):
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    context = {
        'operator': operator,
        'route': route_instance,
        'full_route_num': route_instance.route_num or "Route",
    }
    return render(request, 'map.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def route_add_stops(request, operator_name, route_id, direction):
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Add Stops' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route's stops.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    if request.method == "POST":
        try:
            raw_data = request.POST.get("routeData")
            if not raw_data:
                raise ValueError("Missing routeData")

            parsed_stops = json.loads(raw_data)

            # Delete any existing stops for this route and direction first (optional but good for edits)
            routeStop.objects.filter(route=route_instance, inbound=(direction == "inbound")).delete()

            # Create new routeStop entry
            routeStop.objects.create(
                route=route_instance,
                inbound=(direction == "inbound"),
                circular=False,  # Or True if you detect that logic elsewhere
                stops=parsed_stops  # Save raw list of dictionaries directly
            )

            messages.success(request, "Stops saved successfully.")
            return redirect(f'/operator/{operator_name}/route/{route_id}/')

        except Exception as e:
            messages.error(request, f"Failed to save stops: {e}")
            return redirect(request.path)


    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_name}/route/{route_id}/timetable/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'route': route_instance,
        'helper_permissions': userPerms,
        'direction': direction,
    }
    return render(request, 'route_add_route.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def route_timetable_add(request, operator_name, route_id, direction):
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Timetables' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route's timetable.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    stops = routeStop.objects.filter(route=route_instance).first()

    if request.method == "POST":
        # Handle timetable editing logic here
        pass  # Placeholder for actual logic

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_name}/route/{route_id}/timetable/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'stops': stops,
        'route': route_instance,
        'helper_permissions': userPerms,
    }
    return render(request, 'timetable_add.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def route_timetable_edit(request, operator_name, route_id):
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Edit Timetables' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this route's timetable.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    # Get all days
    days = dayType.objects.all()

    if request.method == "POST":
        # Handle timetable editing logic here
        pass  # Placeholder for actual logic

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_name}/route/{route_id}/timetable/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'route': route_instance,
        'days': days,
        'helper_permissions': userPerms,
    }
    return render(request, 'timetable_edit.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def route_timetable_delete(request, operator_name, route_id, timetable_id):
    operator = get_object_or_404(MBTOperator, operator_name=operator_name)
    route_instance = get_object_or_404(route, id=route_id)
    timetable_entry = get_object_or_404(timetableEntry, id=timetable_id, route=route_instance)

    userPerms = get_helper_permissions(request.user, operator)

    if request.user != operator.owner and 'Delete Timetables' not in userPerms and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this timetable entry.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/')

    if request.method == "POST":
        timetable_entry.delete()
        messages.success(request, "Timetable entry deleted successfully.")
        return redirect(f'/operator/{operator_name}/route/{route_id}/timetable/')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': operator_name, 'url': f'/operator/{operator_name}/'},
        {'name': route_instance.route_num or 'Route Timetable', 'url': f'/operator/{operator_name}/route/{route_id}/timetable/'}
    ]

    context = {
        'breadcrumbs': breadcrumbs,
        'operator': operator,
        'route': route_instance,
        'timetable_entry': timetable_entry,
        'helper_permissions': userPerms,
    }
    return render(request, 'confirm_delete.html', context)