from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from fleet.models import group, MBTOperator, fleet
from fleet.serializers import fleetSerializer
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timedelta
from django.db.models import IntegerField
from django.db.models.functions import Cast
import re
from django.shortcuts import get_object_or_404, render
from django.core.paginator import Paginator
from django.db.models import Q
from tracking.models import Trip
from fleet.views import vehicles

@login_required
@require_http_methods(["GET", "POST"])
def create_group(request):
    if request.method == "POST":
        group_name = request.POST.get('group_name', '').strip()
        group_description = request.POST.get('group_description', '').strip()
        group_private = request.POST.get('group_private') == 'on'

        if not group_name:
            messages.error(request, "Group name cannot be empty.")
            return redirect('/create-group/')

        if group.objects.filter(group_name=group_name).exists():
            messages.error(request, "A group with this name already exists.")
            return redirect('/create-group/')

        new_group = group.objects.create(
            group_name=group_name,
            private=group_private,
            group_owner=request.user
        )

        messages.success(request, "Group created successfully.")
        return redirect(f'/group/{new_group.group_name}/')

    return render(request, 'create_group.html')

def group_view(request, group_name):
    grp = get_object_or_404(group, group_name=group_name)
    show_wd = request.GET.get('withdrawn', '').lower() == 'true'
    owner = request.user.is_authenticated and (grp.group_owner == request.user)

    ops_ids = MBTOperator.objects.filter(group=grp).values_list('id', flat=True)
    qs = fleet.objects.filter(operator_id__in=ops_ids)

    if not show_wd:
        qs = qs.filter(in_service=True)

    qs = qs.select_related('livery', 'vehicleType', 'operator').only(
        'id', 'fleet_number', 'fleet_number_sort', 'reg', 'prev_reg', 'colour',
        'branding', 'depot', 'name', 'features', 'last_tracked_date',
        'livery__name', 'livery__left_css',
        'vehicleType__type_name',
        'operator__operator_name', 'operator__operator_code', 'in_service'
    ).order_by('fleet_number_sort')

    show_livery   = qs.filter(Q(livery__isnull=False) | Q(colour__isnull=False)).exists()
    show_branding = qs.filter(Q(branding__isnull=False) & Q(livery__isnull=False)).exists()
    show_prev_reg = qs.filter(~Q(prev_reg__in=[None, ''])).exists()
    show_name     = qs.filter(~Q(name__in=[None, ''])).exists()
    show_depot    = qs.filter(~Q(depot__in=[None, ''])).exists()
    show_features = qs.filter(~Q(features__in=[None, ''])).exists()

    paginator = Paginator(qs, 250)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)

    serialized_vehicles = list(page_obj.object_list.values(
        'id', 'fleet_number', 'reg', 'prev_reg', 'colour',
        'branding', 'depot', 'name', 'features',
        'livery__name', 'livery__left_css', 'vehicleType__type_name', 'operator__operator_name',
        'operator__operator_code', 'last_tracked_date', 'in_service'
    ))

    vehicle_ids = [v['id'] for v in serialized_vehicles]

    latest_trips = {}
    for trip in (
        Trip.objects
        .filter(trip_vehicle_id__in=vehicle_ids, trip_start_at__lte=timezone.now())
        .order_by('trip_vehicle_id', '-trip_start_at')
    ):
        if trip.trip_vehicle_id not in latest_trips:
            latest_trips[trip.trip_vehicle_id] = trip

    def format_last_trip_display(trip_date):
        local = timezone.localtime(trip_date)
        now = timezone.localtime(timezone.now())
        diff = now - local

        if diff <= timedelta(days=1):
            return local.strftime('%H:%M')
        if local.year != now.year:
            return local.strftime('%d %b %Y')
        return local.strftime('%d %b')

    for item in serialized_vehicles:
        trip = latest_trips.get(item['id'])
        if trip:
            item['last_trip_route'] = str(trip.trip_route.route_num) if trip.trip_route else str(trip.trip_route_num)
            item['last_trip_display'] = format_last_trip_display(trip.trip_start_at)
        else:
            item['last_trip_route'] = None
            item['last_trip_display'] = None

    operators = MBTOperator.objects.filter(group=grp).values('id', 'operator_name')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Groups', 'url': '/groups/'},
        {'name': grp.group_name, 'url': f'/group/{grp.group_name}/'}
    ]

    return render(request, 'group.html', {
        'group':         grp,
        'operators':     operators,
        'vehicles':      serialized_vehicles,
        'breadcrumbs':   breadcrumbs,
        'show_livery':   show_livery,
        'show_branding': show_branding,
        'show_prev_reg': show_prev_reg,
        'show_name':     show_name,
        'show_depot':    show_depot,
        'show_features': show_features,
        'owner':         owner,
        'is_paginated':  page_obj.has_other_pages(),
        'page_obj':      page_obj,
        'total_count':   qs.count(),
    })


@login_required
@require_http_methods(["GET", "POST"])
def group_edit(request, group_name):
    group_instance = get_object_or_404(group, group_name=group_name)

    if request.user != group_instance.group_owner:
        messages.error(request, "You do not have permission to edit this group.")
        return redirect(f'/group/{group_instance.group_name}/')

    if request.method == "POST":
        new_group_name = request.POST.get('group_name', '').strip()
        new_group_description = request.POST.get('group_description', '').strip()
        new_private = request.POST.get('group_private') == 'on'

        if not new_group_name:
            messages.error(request, "Group name cannot be empty.")
            return redirect(f'/group/{group_instance.group_name}/edit/')

        if new_group_name != group_instance.group_name and group.objects.filter(group_name=new_group_name).exists():
            messages.error(request, "A group with this name already exists.")
            return redirect(f'/group/{group_instance.group_name}/edit/')

        group_instance.group_name = new_group_name
        group_instance.group_description = new_group_description
        group_instance.private = new_private
        group_instance.save()

        messages.success(request, "Group updated successfully.")
        return redirect(f'/group/{group_instance.group_name}/')

    context = {
        'group': group_instance
    }
    return render(request, 'group_edit.html', context)

@login_required
@require_http_methods(["POST"])
def group_delete(request, group_name):
    group_instance = get_object_or_404(group, group_name=group_name)

    if request.user != group_instance.group_owner:
        messages.error(request, "You do not have permission to delete this group.")
        return redirect(f'/group/{group_instance.group_name}/')

    group_instance.delete()
    messages.success(request, "Group deleted successfully.")
    return redirect('/')
