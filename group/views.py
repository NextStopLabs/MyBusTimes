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
    group_instance = get_object_or_404(group, group_name=group_name)
    withdrawn = request.GET.get('withdrawn')
    show_withdrawn = withdrawn and withdrawn.lower() == 'true'

    user = request.user
    owner = False

    if user.is_authenticated and group_instance.group_owner == user:
        owner = True

    all_group_operators = MBTOperator.objects.filter(group=group_instance)
    all_group_vehicles = []

    for operator in all_group_operators:
        def alphanum_key(fleet_number):
            return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', fleet_number or '')]
        
        if show_withdrawn:
            vehicles = fleet.objects.filter(operator=operator) \
            .annotate(fleet_number_int=Cast('fleet_number', IntegerField())) \
            .order_by('fleet_number_int')
        else:
            vehicles = fleet.objects.filter(operator=operator, in_service=True) \
            .annotate(fleet_number_int=Cast('fleet_number', IntegerField())) \
            .order_by('fleet_number_int')

        vehicles = list(vehicles)  # Add this before sorting
        vehicles.sort(key=lambda v: alphanum_key(v.fleet_number))

        serialized_vehicles = fleetSerializer(vehicles, many=True)
        all_group_vehicles.extend(serialized_vehicles.data)
                                  
    def has_non_null_field(data_list, field):
        return any(item.get(field) not in [None, '', [], {}] for item in data_list)

    show_livery = has_non_null_field(all_group_vehicles, 'livery') or has_non_null_field(all_group_vehicles, 'colour')
    show_branding = (
        has_non_null_field(all_group_vehicles, 'branding') and
        has_non_null_field(all_group_vehicles, 'livery')
    )
    show_prev_reg = has_non_null_field(all_group_vehicles, 'prev_reg')
    show_name = has_non_null_field(all_group_vehicles, 'name')
    show_depot = has_non_null_field(all_group_vehicles, 'depot')
    show_features = has_non_null_field(all_group_vehicles, 'features')

    now = timezone.localtime(timezone.now())

    for item in all_group_vehicles:
        raw_date_value = item.get('last_trip_date')

        if raw_date_value:
            if isinstance(raw_date_value, str):
                raw_date = parse_datetime(raw_date_value)
                if raw_date is None:
                    item['last_trip_display'] = ''
                    continue
            elif hasattr(raw_date_value, 'strftime'):
                raw_date = raw_date_value
            else:
                item['last_trip_display'] = ''
                continue

            raw_date_local = timezone.localtime(raw_date)
            diff = now - raw_date_local

            if diff <= timedelta(days=1):
                item['last_trip_display'] = raw_date_local.strftime('%H:%M')
            elif raw_date_local.year != now.year:
                item['last_trip_display'] = raw_date_local.strftime('%d %b %Y')
            else:
                item['last_trip_display'] = raw_date_local.strftime('%d %b')
        else:
            item['last_trip_display'] = ''

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Groups', 'url': '/groups/'},
        {'name': group_instance.group_name, 'url': f'/group/{group_instance.group_name}/'}
    ]

    all_group_vehicles.sort(key=lambda v: alphanum_key(v.fleet_number))

    context = {
        'group': group_instance,
        'operators': all_group_operators,
        'vehicles': all_group_vehicles,
        'breadcrumbs': breadcrumbs,
        'show_livery': show_livery,
        'show_branding': show_branding,
        'show_prev_reg': show_prev_reg,
        'show_name': show_name,
        'show_depot': show_depot,
        'show_features': show_features,
        'owner': owner,
    }

    return render(request, 'group.html', context)

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
