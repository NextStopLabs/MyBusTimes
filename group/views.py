from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from fleet.models import group, MBTOperator, fleet, organisation, mapTileSet, reservedOperatorName
from fleet.serializers import fleetSerializer
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import datetime, timedelta
from django.db.models import IntegerField, Case, When, Max
from django.db.models.functions import Cast
import re
from django.shortcuts import get_object_or_404, render
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from tracking.models import Trip
from routes.models import route, transitAuthoritiesColour
from fleet.views import feature_enabled, get_route_colours, get_unique_linked_routes, parse_route_key, vehicles
from words.models import bannedWord
from words.utils import banned_words_in_text


def group_name_banned_words(group_name):
    return banned_words_in_text(group_name, bannedWord.GROUP_NAME_SCOPE)


def group_name_banned_message(blocked_words):
    words = ', '.join(sorted(set(blocked_words)))
    return f"Group name contains a banned word: {words}."


def reserved_operator_name_message(reservation):
    return f"This operator name ({reservation.operator_name}) is reserved, if you think this is a mistake please open a ticket via discord or on the site"

@login_required
@require_http_methods(["GET", "POST"])
def create_group(request):
    if request.method == "POST":
        group_name = request.POST.get('group_name', '').strip()
        group_order_by = request.POST.get('order_by', 'fleet_number')
        group_private = request.POST.get('private') == 'on'

        if not group_name:
            messages.error(request, "Group name cannot be empty.")
            return redirect('/group/create/')

        blocked_words = group_name_banned_words(group_name)
        if blocked_words:
            messages.error(request, group_name_banned_message(blocked_words))
            return redirect('/group/create/')

        reservation = reservedOperatorName.blocking_reservation_for_user(group_name, request.user)
        if reservation:
            messages.error(request, reserved_operator_name_message(reservation))
            return redirect('/group/create/')

        if group.objects.filter(group_name=group_name).exists():
            messages.error(request, "A group with this name already exists.")
            return redirect('/group/create/')

        new_group = group.objects.create(
            group_name=group_name,
            private=group_private,
            order_by=group_order_by,
            group_owner=request.user
        )

        messages.success(request, "Group created successfully.")
        return redirect(f'/group/{new_group.group_name}/')
    
    order_by_choices = group.OrderBy.choices

    return render(request, 'create_group.html', {
        'order_by_choices': order_by_choices,
    })

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
        'last_trip_datetime', 'last_trip_route_num',
        'livery__name', 'livery__left_css', 'open_top',
        'vehicleType__type_name', 'type_details', 'operator__operator_name',
        'operator__operator_slug', 'operator__operator_code', 'in_service'
    )

    if grp.order_by == group.OrderBy.FLEET_NUMBER:
        qs = qs.order_by('fleet_number_sort')
    elif grp.order_by == group.OrderBy.OPERATOR_NAME:
        qs = qs.order_by('operator__operator_name', 'fleet_number_sort')
    else:
        qs = qs.order_by('fleet_number_sort')


    show_flags = qs.aggregate(
        show_livery=Max(Case(
            When(Q(livery__isnull=False) | Q(colour__isnull=False), then=1),
            default=0,
            output_field=IntegerField()
        )),
        show_branding=Max(Case(
            When(Q(branding__isnull=False) & Q(livery__isnull=False), then=1),
            default=0,
            output_field=IntegerField()
        )),
        show_prev_reg=Max(Case(
            When(~Q(prev_reg__in=[None, '']), then=1),
            default=0,
            output_field=IntegerField()
        )),
        show_name=Max(Case(
            When(~Q(name__in=[None, '']), then=1),
            default=0,
            output_field=IntegerField()
        )),
        show_depot=Max(Case(
            When(~Q(depot__in=[None, '']), then=1),
            default=0,
            output_field=IntegerField()
        )),
        show_features=Max(Case(
            When(~Q(features__in=[None, '']), then=1),
            default=0,
            output_field=IntegerField()
        )),
    )

    show_livery = bool(show_flags.get('show_livery'))
    show_branding = bool(show_flags.get('show_branding'))
    show_prev_reg = bool(show_flags.get('show_prev_reg'))
    show_name = bool(show_flags.get('show_name'))
    show_depot = bool(show_flags.get('show_depot'))
    show_features = bool(show_flags.get('show_features'))

    paginator = Paginator(qs, 250)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)

    serialized_vehicles = list(page_obj.object_list.values(
        'id', 'fleet_number', 'reg', 'prev_reg', 'colour', 'open_top',
        'branding', 'depot', 'name', 'features', 'type_details', 'operator__operator_name',
        'livery__name', 'livery__left_css', 'vehicleType__type_name', 'operator__operator_slug',
        'operator__operator_code', 'last_tracked_date', 'last_tracked_route',
        'last_trip_datetime', 'last_trip_route_num', 'in_service'
    ))

    vehicle_ids = [v['id'] for v in serialized_vehicles]

    latest_trips = {}
    if vehicle_ids:
        try:
            trips = (
                Trip.objects
                .filter(trip_vehicle_id__in=vehicle_ids, trip_start_at__lte=timezone.now())
                .select_related('trip_route')
                .only('trip_vehicle_id', 'trip_start_at', 'trip_route_num', 'trip_route__route_num')
                .order_by('trip_vehicle_id', '-trip_start_at')
                .distinct('trip_vehicle_id')
            )
            latest_trips = {trip.trip_vehicle_id: trip for trip in trips}
        except NotImplementedError:
            now_ts = timezone.now()
            trip_iter = (
                Trip.objects
                .filter(trip_vehicle_id__in=vehicle_ids, trip_start_at__lte=now_ts)
                .select_related('trip_route')
                .only('trip_vehicle_id', 'trip_start_at', 'trip_route_num', 'trip_route__route_num')
                .order_by('trip_vehicle_id', '-trip_start_at')
                .iterator()
            )
            for trip in trip_iter:
                if trip.trip_vehicle_id not in latest_trips:
                    latest_trips[trip.trip_vehicle_id] = trip
                    if len(latest_trips) == len(vehicle_ids):
                        break

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
            persisted_dt = item.get('last_trip_datetime')
            if persisted_dt:
                item['last_trip_route'] = item.get('last_trip_route_num') or None
                parsed_dt = None
                try:
                    parsed_dt = datetime.fromisoformat(persisted_dt)
                except (ValueError, TypeError):
                    pass
                if parsed_dt:
                    item['last_trip_display'] = format_last_trip_display(parsed_dt)
                else:
                    item['last_trip_route'] = None
                    item['last_trip_display'] = None
            else:
                legacy_dt = item.get('last_tracked_date')
                if legacy_dt:
                    item['last_trip_route'] = item.get('last_tracked_route') or None
                    item['last_trip_display'] = format_last_trip_display(legacy_dt)
                else:
                    item['last_trip_route'] = None
                    item['last_trip_display'] = None

    operators = MBTOperator.objects.filter(group=grp).values('id', 'operator_slug')
    route_count = route.objects.filter(route_operators__id__in=ops_ids, hidden=False).distinct().count()

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Groups', 'url': '/groups/'},
        {'name': grp.group_name, 'url': f'/group/{grp.group_name}/'}
    ]

    return render(request, 'group.html', {
        'group':         grp,
        'is_org':        False,
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
        'route_count':   route_count,
    })

def group_operator_map(request, group_name):
    response = feature_enabled(request, "route_map")
    if response:
        return response

    grp = get_object_or_404(group, group_name=group_name)
    operator = (
        MBTOperator.objects
        .filter(group=grp, mapTile__isnull=False)
        .select_related("mapTile")
        .first()
    )
    mapTiles_instance = operator.mapTile if operator and operator.mapTile and operator.mapTile.is_available_to_user(request.user) else mapTileSet.default_for_user(request.user)

    context = {
        'group': grp,
        'mapTile': mapTiles_instance,
        'mapTileSets': mapTileSet.available_to_user(request.user).order_by('name'),
    }
    return render(request, 'map-group-operator.html', context)

def group_routes(request, group_name):
    response = feature_enabled(request, "view_routes")
    if response:
        return response

    grp = get_object_or_404(group, group_name=group_name)
    show_hidden = request.GET.get('hidden', 'false').lower() == 'true'
    owner = request.user.is_authenticated and (grp.group_owner == request.user)

    operator_qs = MBTOperator.objects.filter(group=grp).order_by('operator_name')
    operator_ids = list(operator_qs.values_list('id', flat=True))

    route_query = route.objects.filter(route_operators__id__in=operator_ids).distinct()
    if not show_hidden:
        route_query = route_query.filter(hidden=False)

    authority_codes = set()
    for operator in operator_qs.only('operator_details'):
        details = operator.operator_details or {}
        transit_authority = details.get('transit_authority') or details.get('transit_authorities')
        if transit_authority:
            authority_codes.add(transit_authority.split(",")[0].strip())

    authority_lookup = {
        authority.authority_code: authority
        for authority in transitAuthoritiesColour.objects.filter(authority_code__in=authority_codes)
    }

    def apply_route_colour(route_instance, authority):
        colours_result = get_route_colours(route_instance, authority)
        if isinstance(colours_result, tuple):
            route_instance.colours = colours_result[0]
            route_instance.school_service = colours_result[1]
        else:
            route_instance.colours = colours_result
            route_instance.school_service = None

    def colour_routes(routes_for_operator, operator):
        details = operator.operator_details if operator else {}
        transit_authority = (details or {}).get('transit_authority') or (details or {}).get('transit_authorities')
        authority = None
        if transit_authority:
            authority = authority_lookup.get(transit_authority.split(",")[0].strip())

        for route_instance in routes_for_operator:
            route_instance.primary_operator = operator
            apply_route_colour(route_instance, authority)

    route_sections = []
    for operator in operator_qs:
        operator_routes = list(
            route_query
            .filter(route_operators=operator)
        )

        if not operator_routes:
            continue

        operator_routes = sorted(operator_routes, key=parse_route_key)
        colour_routes(operator_routes, operator)

        unique_routes = get_unique_linked_routes(operator_routes)
        for route_group in unique_routes:
            for route_instance in [route_group["primary"], *route_group["linked"]]:
                if not hasattr(route_instance, "primary_operator"):
                    route_instance.primary_operator = operator
                    apply_route_colour(route_instance, None)

        route_sections.append({
            'operator': operator,
            'routes': unique_routes,
            'route_count': len(operator_routes),
        })

    vehicle_count = fleet.objects.filter(operator_id__in=operator_ids, in_service=True).count()
    route_count = route_query.count()

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Groups', 'url': '/groups/'},
        {'name': grp.group_name, 'url': f'/group/{grp.group_name}/'},
        {'name': 'Routes', 'url': f'/group/{grp.group_name}/routes/'}
    ]

    return render(request, 'group_routes.html', {
        'group': grp,
        'route_sections': route_sections,
        'breadcrumbs': breadcrumbs,
        'owner': owner,
        'show_hidden': show_hidden,
        'route_count': route_count,
        'vehicle_count': vehicle_count,
        'today': timezone.now().date(),
    })

def organisation_view(request, organisation_name):
    org = get_object_or_404(organisation, organisation_name=organisation_name)
    show_wd = request.GET.get('withdrawn', '').lower() == 'true'
    owner = request.user.is_authenticated and (org.organisation_owner == request.user)

    ops_ids = MBTOperator.objects.filter(organisation=org).values_list('id', flat=True)
    qs = fleet.objects.filter(operator_id__in=ops_ids)

    if not show_wd:
        qs = qs.filter(in_service=True)

    qs = qs.select_related('livery', 'vehicleType', 'operator').only(
        'id', 'fleet_number', 'fleet_number_sort', 'reg', 'prev_reg', 'colour',
        'branding', 'depot', 'name', 'features', 'last_tracked_date',
        'last_trip_datetime', 'last_trip_route_num',
        'livery__name', 'livery__left_css', 'open_top',
        'vehicleType__type_name', 'type_details', 'operator__operator_name',
        'operator__operator_slug', 'operator__operator_code', 'in_service'
    ).order_by('fleet_number_sort')

    show_flags = qs.aggregate(
        show_livery=Max(Case(
            When(Q(livery__isnull=False) | Q(colour__isnull=False), then=1),
            default=0,
            output_field=IntegerField()
        )),
        show_branding=Max(Case(
            When(Q(branding__isnull=False) & Q(livery__isnull=False), then=1),
            default=0,
            output_field=IntegerField()
        )),
        show_prev_reg=Max(Case(
            When(~Q(prev_reg__in=[None, '']), then=1),
            default=0,
            output_field=IntegerField()
        )),
        show_name=Max(Case(
            When(~Q(name__in=[None, '']), then=1),
            default=0,
            output_field=IntegerField()
        )),
        show_depot=Max(Case(
            When(~Q(depot__in=[None, '']), then=1),
            default=0,
            output_field=IntegerField()
        )),
        show_features=Max(Case(
            When(~Q(features__in=[None, '']), then=1),
            default=0,
            output_field=IntegerField()
        )),
    )

    show_livery = bool(show_flags.get('show_livery'))
    show_branding = bool(show_flags.get('show_branding'))
    show_prev_reg = bool(show_flags.get('show_prev_reg'))
    show_name = bool(show_flags.get('show_name'))
    show_depot = bool(show_flags.get('show_depot'))
    show_features = bool(show_flags.get('show_features'))

    paginator = Paginator(qs, 250)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)

    serialized_vehicles = list(page_obj.object_list.values(
        'id', 'fleet_number', 'reg', 'prev_reg', 'colour', 'open_top',
        'branding', 'depot', 'name', 'features', 'type_details', 'operator__operator_name',
        'livery__name', 'livery__left_css', 'vehicleType__type_name', 'operator__operator_slug',
        'operator__operator_code', 'last_tracked_date', 'last_tracked_route',
        'last_trip_datetime', 'last_trip_route_num', 'in_service'
    ))

    vehicle_ids = [v['id'] for v in serialized_vehicles]

    latest_trips = {}
    if vehicle_ids:
        try:
            trips = (
                Trip.objects
                .filter(trip_vehicle_id__in=vehicle_ids, trip_start_at__lte=timezone.now())
                .select_related('trip_route')
                .only('trip_vehicle_id', 'trip_start_at', 'trip_route_num', 'trip_route__route_num')
                .order_by('trip_vehicle_id', '-trip_start_at')
                .distinct('trip_vehicle_id')
            )
            latest_trips = {trip.trip_vehicle_id: trip for trip in trips}
        except NotImplementedError:
            now_ts = timezone.now()
            trip_iter = (
                Trip.objects
                .filter(trip_vehicle_id__in=vehicle_ids, trip_start_at__lte=now_ts)
                .select_related('trip_route')
                .only('trip_vehicle_id', 'trip_start_at', 'trip_route_num', 'trip_route__route_num')
                .order_by('trip_vehicle_id', '-trip_start_at')
                .iterator()
            )
            for trip in trip_iter:
                if trip.trip_vehicle_id not in latest_trips:
                    latest_trips[trip.trip_vehicle_id] = trip
                    if len(latest_trips) == len(vehicle_ids):
                        break

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
            persisted_dt = item.get('last_trip_datetime')
            if persisted_dt:
                item['last_trip_route'] = item.get('last_trip_route_num') or None
                parsed_dt = None
                try:
                    parsed_dt = datetime.fromisoformat(persisted_dt)
                except (ValueError, TypeError):
                    pass
                if parsed_dt:
                    item['last_trip_display'] = format_last_trip_display(parsed_dt)
                else:
                    item['last_trip_route'] = None
                    item['last_trip_display'] = None
            else:
                legacy_dt = item.get('last_tracked_date')
                if legacy_dt:
                    item['last_trip_route'] = item.get('last_tracked_route') or None
                    item['last_trip_display'] = format_last_trip_display(legacy_dt)
                else:
                    item['last_trip_route'] = None
                    item['last_trip_display'] = None

    operators = MBTOperator.objects.filter(organisation=org).values('id', 'operator_slug')

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Organisations', 'url': '/organisations/'},
        {'name': org.organisation_name, 'url': f'/organisation/{org.organisation_name}/'}
    ]

    return render(request, 'group.html', {
        'group':         org,
        'is_org':        True,
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
    order_by_choices = group.OrderBy.choices
    group_instance = get_object_or_404(group, group_name=group_name)

    if request.user != group_instance.group_owner:
        messages.error(request, "You do not have permission to edit this group.")
        return redirect(f'/group/{group_instance.group_name}/')

    if request.method == "POST":
        new_group_name = request.POST.get('group_name', '').strip()
        new_group_description = request.POST.get('group_description', '').strip()
        new_private = request.POST.get('group_private') == 'on'
        new_order_by = request.POST.get('order_by', '').strip()

        if not new_group_name:
            messages.error(request, "Group name cannot be empty.")
            return redirect(f'/group/{group_instance.group_name}/edit/')

        blocked_words = group_name_banned_words(new_group_name)
        if blocked_words:
            messages.error(request, group_name_banned_message(blocked_words))
            return redirect(f'/group/{group_instance.group_name}/edit/')

        reservation = reservedOperatorName.blocking_reservation_for_user(new_group_name, request.user)
        if reservation:
            messages.error(request, reserved_operator_name_message(reservation))
            return redirect(f'/group/{group_instance.group_name}/edit/')

        if new_group_name != group_instance.group_name and group.objects.filter(group_name=new_group_name).exists():
            messages.error(request, "A group with this name already exists.")
            return redirect(f'/group/{group_instance.group_name}/edit/')

        group_instance.group_name = new_group_name
        group_instance.group_description = new_group_description
        group_instance.private = new_private
        group_instance.order_by = new_order_by
        group_instance.save()

        messages.success(request, "Group updated successfully.")
        return redirect(f'/group/{group_instance.group_name}/')

    context = {
        'group': group_instance,
        'order_by_choices': order_by_choices,
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
