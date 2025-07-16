from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .forms import AdForm, LiveryForm, VehicleForm
from .models import CustomModel
from main.models import CustomUser, badge, ad, featureToggle, BannedIps
from fleet.models import liverie, fleet, vehicleType
import requests
from django.template.loader import render_to_string
from django.db.models import Q

def has_permission(user, perm_name):
    if user.is_superuser:
        return True
    return user.mbt_admin_perms.filter(name=perm_name).exists()

def permission_denied(request):
    return render(request, 'now-access.html')

def ban_user(request, user_id):
    if not has_permission(request.user, 'user_ban'):
        return redirect('/admin/permission-denied/')
    
    user = CustomUser.objects.get(id=user_id)
    #user.banned = True
    #user.save()
    return render(request, 'ban.html', {'user': user})

def submit_ban_user(request, user_id):
    if not has_permission(request.user, 'user_ban'):
        return redirect('/admin/permission-denied/')
    
    user = CustomUser.objects.get(id=user_id)
    user.banned = True
    user.save()
    return redirect('/admin/users-management/')

def submit_ip_ban_user(request, user_id):
    if not has_permission(request.user, 'user_ban'):
        return redirect('/admin/permission-denied/')
    
    user = CustomUser.objects.get(id=user_id)
    user.banned = True
    user.save()

    BannedIps.objects.create(
        ip_address=user.last_login_ip,
        reason=request.POST.get('reason', 'No reason provided'),
        related_user=user
    )

    # Implement IP ban logic here
    return redirect('/admin/users-management/')

def custom_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('/admin/')  # Redirect to the admin page
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

@login_required(login_url='/admin/login/')
def fetch_traffic_day_data(request):
    if not has_permission(request.user, 'analytics'):
        return JsonResponse({"error": str("No permission")})
    
    date_param_day = request.GET.get('dateDay', 'today')

    try:
        if date_param_day == 'yesterday':
            response = requests.get("http://184.174.17.73:800/index.php?module=API&method=VisitsSummary.get&idSite=1&period=day&date=yesterday&format=JSON&token_auth=068ac2f37b631d5bb713b246516e88b1")
        else:
            response = requests.get("http://184.174.17.73:800/index.php?module=API&method=VisitsSummary.get&idSite=1&period=day&date=today&format=JSON&token_auth=068ac2f37b631d5bb713b246516e88b1")

        dataDay = response.json()
        return JsonResponse(dataDay)
    except Exception as e:
        return JsonResponse({"error": str(e)})
    
@login_required(login_url='/admin/login/')
def fetch_traffic_week_data(request):
    if not has_permission(request.user, 'analytics'):
        return JsonResponse({"error": str("No permission")})
    
    date_param_week = request.GET.get('dateWeek', 'today')
    
    try:
        if date_param_week == 'last week':
            response = requests.get("http://184.174.17.73:800/index.php?module=API&method=VisitsSummary.get&idSite=1&period=week&date=lastweek&format=JSON&token_auth=068ac2f37b631d5bb713b246516e88b1")
        else:  # Default to today
            response = requests.get("http://184.174.17.73:800/index.php?module=API&method=VisitsSummary.get&idSite=1&period=week&date=today&format=JSON&token_auth=068ac2f37b631d5bb713b246516e88b1")

        dataWeek = response.json()
        return JsonResponse(dataWeek)
    except Exception as e:
        return JsonResponse({"error": str(e)})

@login_required(login_url='/admin/login/')
def fetch_traffic_live_data(request):
    if not has_permission(request.user, 'analytics'):
        return JsonResponse({"error": str("No permission")})
    
    try:
        response = requests.get("http://184.174.17.73:800/index.php?module=API&method=Live.getCounters&idSite=1&lastMinutes=15&format=JSON&token_auth=068ac2f37b631d5bb713b246516e88b1")
        dataLive = response.json()
        # Return only the visits count as a JSON response
        return JsonResponse({'visits': dataLive[0]['visits']})
    except Exception as e:
        return JsonResponse({"error": str(e)})

@login_required(login_url='/admin/login/')
def dashboard_view(request):
    if not has_permission(request.user, 'admin_dash'):
        return redirect('/admin/permission-denied/')
    
    user_count = CustomUser.objects.count()  # Get the user count

    # Get the date parameter from the request, default to 'today'
    date_param = request.GET.get('dateDay', 'today')
    date_param_week = request.GET.get('dateWeek', 'today')

    dataDay = {}
    dataWeek = {}
    dataLive = {}

    return render(request, 'dashboard.html', {'user_count': user_count, "dataDay": dataDay, "dataWeek": dataWeek, "dataLive": dataLive, "date_param": date_param, "date_param_week": date_param_week})

@login_required(login_url='/admin/login/')
def ads_view(request):
    if not has_permission(request.user, 'ad_view'):
        return redirect('/admin/permission-denied/')
    
    feature_toggles = featureToggle.objects.filter(name__in=['mbt_ads', 'google_ads', 'ads'])

    ads = ad.objects.all()
    return render(request, 'ads.html', {'ads': ads, 'feature_toggles': feature_toggles})

@login_required(login_url='/admin/login/')
def edit_ad(request, ad_id):
    if not has_permission(request.user, 'ad_edit'):
        return redirect('/admin/permission-denied/')
    
    ads = ad.objects.get(id=ad_id)

    if request.method == 'POST':
        form = AdForm(request.POST, request.FILES, instance=ads)
        if form.is_valid():
            form.save()
            return redirect('/admin/ads-management/')  # or any success page
    else:
        form = AdForm(instance=ads)

    return render(request, 'edit_ad.html', {'form': form})

@login_required(login_url='/admin/login/')
def delete_ad(request, ad_id):
    if not has_permission(request.user, 'ad_delete'):
        return redirect('/admin/permission-denied/')
    
    ads = ad.objects.get(id=ad_id)
    ads.delete()
    return redirect('/admin/ads-management/')

@login_required(login_url='/admin/login/')
def add_ad(request):
    if not has_permission(request.user, 'ad_add'):
        return redirect('/admin/permission-denied/')
    
    if request.method == 'POST':
        form = AdForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('/admin/ads-management/')
    else:
        form = AdForm()

    return render(request, 'add_ad.html', {'form': form})


@login_required(login_url='/admin/login/')
def users_view(request):
    if not has_permission(request.user, 'user_view'):
        return redirect('/admin/permission-denied/')

    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'join_date')  # default sort
    order = request.GET.get('order', 'desc')  # 'asc' or 'desc'

    users_list = CustomUser.objects.all()

    if search_query:
        users_list = users_list.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    if sort_by in ['username', 'email', 'join_date']:
        if order == 'desc':
            sort_by = '-' + sort_by
        users_list = users_list.order_by(sort_by)

    paginator = Paginator(users_list, 100)
    page_number = request.GET.get("page")
    users = paginator.get_page(page_number)

    sortable_fields = ['username', 'email', 'join_date']

    context = {
        'users': users,
        'search_query': search_query,
        'current_sort': sort_by.lstrip('-'),
        'current_order': order,
        'sortable_fields': sortable_fields,
    }

    return render(request, 'users.html', context)

@login_required(login_url='/admin/login/')
def edit_user(request, user_id):
    if not has_permission(request.user, 'user_edit'):
        return redirect('/admin/permission-denied/')
    
    badges = badge.objects.all()
    user = CustomUser.objects.get(id=user_id)
    return render(request, 'edit_user.html', {'user': user, 'badges': badges})

@login_required(login_url='/admin/login/')
def update_user(request, user_id):
    if not has_permission(request.user, 'user_edit'):
        return redirect('/admin/permission-denied/')
    
    user = CustomUser.objects.get(id=user_id)

    if (request.POST.get('banned') == 'on'):
        user.badges.set([48])
    else:
        user.badges.set(request.POST.getlist('badges'))

    user.username = request.POST.get('username')
    user.email = request.POST.get('email')
    user.banned = request.POST.get('banned') == 'on'
    
    user.save()
    return redirect('/admin/users-management/')

@login_required(login_url='/admin/login/')
def delete_user(request, user_id):
    if not has_permission(request.user, 'user_delete'):
        return redirect('/admin/permission-denied/')
    
    user = CustomUser.objects.get(id=user_id)
    user.delete()

@login_required(login_url='/admin/login/')
def feature_toggles_view(request):
    if not has_permission(request.user, 'feature_toggle_view'):
        return redirect('/admin/permission-denied/')
    
    feature_toggles = featureToggle.objects.all()
    return render(request, 'feature_toggles.html', {'feature_toggles': feature_toggles})

@login_required(login_url='/admin/login/')
def enable_feature(request, feature_id):
    if not has_permission(request.user, 'feature_toggle_enable'):
        return redirect('/admin/permission-denied/')

    feature = featureToggle.objects.get(id=feature_id)
    feature.enabled = True
    feature.coming_soon = False
    feature.maintenance = False
    feature.save()
    return redirect('/admin/feature-toggles-management/')

@login_required(login_url='/admin/login/')
def maintenance_feature(request, feature_id):
    if not has_permission(request.user, 'feature_toggle_maintenance'):
        return redirect('/admin/permission-denied/')
    
    feature = featureToggle.objects.get(id=feature_id)
    feature.maintenance = True
    feature.coming_soon = False
    feature.enabled = False
    feature.save()
    return redirect('/admin/feature-toggles-management/')

@login_required(login_url='/admin/login/')
def disable_feature(request, feature_id):
    if not has_permission(request.user, 'feature_toggle_disable'):
        return redirect('/admin/permission-denied/')
    
    feature = featureToggle.objects.get(id=feature_id)
    feature.enabled = False
    feature.coming_soon = False
    feature.maintenance = False
    feature.save()
    return redirect('/admin/feature-toggles-management/')

@login_required(login_url='/admin/login/')
def enable_ad_feature(request, feature_id):
    if not has_permission(request.user, 'feature_toggle_enable'):
        return redirect('/admin/permission-denied/')

    feature = featureToggle.objects.get(id=feature_id)
    feature.enabled = True
    feature.coming_soon = False
    feature.maintenance = False
    feature.save()
    return redirect('/admin/ads-management/')

@login_required(login_url='/admin/login/')
def disable_ad_feature(request, feature_id):
    if not has_permission(request.user, 'feature_toggle_disable'):
        return redirect('/admin/permission-denied/')
    
    feature = featureToggle.objects.get(id=feature_id)
    feature.enabled = False
    feature.coming_soon = False
    feature.maintenance = False
    feature.save()
    return redirect('/admin/ads-management/')

from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


@login_required(login_url='/admin/login/')
def livery_management(request):
    if not has_permission(request.user, 'livery_view'):
        return redirect('/admin/permission-denied/')


    search_query = request.GET.get('q', '')
    liveries_list = liverie.objects.filter(name__icontains=search_query).order_by('name')

    paginator = Paginator(liveries_list, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # If AJAX, return partial HTML
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('partials/livery_table.html', {'page_obj': page_obj})
        return JsonResponse({'html': html})

    return render(request, 'livery.html', {'page_obj': page_obj, 'search_query': search_query, 'approver': False})

@login_required(login_url='/admin/login/')
def vehicle_management(request):
    if not has_permission(request.user, 'vehicle_view'):
        return redirect('/admin/permission-denied/')


    search_query = request.GET.get('q', '')
    vehicles_list = vehicleType.objects.filter(type_name__icontains=search_query).order_by('type_name')

    paginator = Paginator(vehicles_list, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # If AJAX, return partial HTML
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('partials/vehicle_table.html', {'page_obj': page_obj})
        return JsonResponse({'html': html})

    return render(request, 'vehicles-manage.html', {'page_obj': page_obj, 'search_query': search_query, 'approver': False})

@login_required(login_url='/admin/login/')
def livery_approver(request):
    if not has_permission(request.user, 'livery_view'):
        return redirect('/admin/permission-denied/')


    search_query = request.GET.get('q', '')
    liveries_list = liverie.objects.filter(name__icontains=search_query, published=False).order_by('name')

    paginator = Paginator(liveries_list, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # If AJAX, return partial HTML
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('partials/livery_table.html', {'page_obj': page_obj})
        return JsonResponse({'html': html})

    return render(request, 'livery.html', {'page_obj': page_obj, 'search_query': search_query, 'approver': True})


@login_required(login_url='/admin/login/')
def publish_livery(request, livery_id):
    if not has_permission(request.user, 'livery_publish'):
        return redirect('/admin/permission-denied/')
    
    page_number = request.GET.get('page')

    livery = liverie.objects.get(id=livery_id)
    livery.published = True
    livery.save()

    return redirect('/admin/livery-management/?page=' + str(page_number))

@login_required(login_url='/admin/login/')
def publish_vehicle(request, vehicle_id):
    if not has_permission(request.user, 'vehicle_publish'):
        return redirect('/admin/permission-denied/')
    
    page_number = request.GET.get('page')

    vehicle = vehicleType.objects.get(id=vehicle_id)
    vehicle.active = True
    vehicle.save()

    return redirect('/admin/vehicle-management/?page=' + str(page_number))

@login_required(login_url='/admin/login/')
def edit_livery(request, livery_id):
    if not has_permission(request.user, 'livery_edit'):
        return redirect('/admin/permission-denied/')
    
    page_number = request.GET.get('page')

    if request.method == 'POST':
        livery = liverie.objects.get(id=livery_id)
        form = LiveryForm(request.POST, instance=livery)
        if form.is_valid():
            form.save()
            return redirect('/admin/livery-management/?page=' + str(page_number))
    else:
        livery = liverie.objects.get(id=livery_id)
        form = LiveryForm(instance=livery)
    
    return render(request, 'edit_livery.html', {'form': form})

@login_required(login_url='/admin/login/')
def edit_vehicle(request, vehicle_id):
    if not has_permission(request.user, 'vehicle_edit'):
        return redirect('/admin/permission-denied/')
    
    page_number = request.GET.get('page')

    if request.method == 'POST':
        vehicle = vehicleType.objects.get(id=vehicle_id)
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            return redirect('/admin/vehicle-management/?page=' + str(page_number))
    else:
        vehicle = vehicleType.objects.get(id=vehicle_id)
        form = VehicleForm(instance=vehicle)

    return render(request, 'edit_vehicle.html', {'form': form})

@login_required(login_url='/admin/login/')
def delete_livery(request, livery_id):
    if not has_permission(request.user, 'livery_delete'):
        return redirect('/admin/permission-denied/')
    
    livery = liverie.objects.get(id=livery_id)
    page_number = request.GET.get('page')
    
    # Check if any vehicle in MyBusTimes.fleet is using this livery
    if fleet.objects.filter(livery=livery).exists():
        other_liveries = liverie.objects.filter(name=livery.name).exclude(id=livery_id)

        return render(request, 'dupe_livery.html', {'livery': livery, 'other_liveries': other_liveries})
    
    livery.delete()
    return redirect('/admin/livery-management/?page=' + str(page_number))

@login_required(login_url='/admin/login/')
def delete_vehicle(request, vehicle_id):
    if not has_permission(request.user, 'vehicle_delete'):
        return redirect('/admin/permission-denied/')

    vehicle = vehicleType.objects.get(id=vehicle_id)
    page_number = request.GET.get('page')

    # Check if any vehicle in MyBusTimes.fleet is using this vehicle
    if fleet.objects.filter(vehicleType=vehicle).exists():
        other_vehicles = vehicleType.objects.filter(name=vehicle.name).exclude(id=vehicle_id)

        return render(request, 'dupe_vehicle.html', {'vehicle': vehicle, 'other_vehicles': other_vehicles})

    vehicle.delete()
    return redirect('/admin/vehicle-management/?page=' + str(page_number))

@login_required(login_url='/admin/login/')
def replace_livery(request):
    if not has_permission(request.user, 'livery_replace'):
        return redirect('/admin/permission-denied/')
    
    old_livery = liverie.objects.get(id=request.GET.get('old'))
    new_livery = liverie.objects.get(id=request.GET.get('new'))

    fleet.objects.filter(livery=old_livery).update(livery=new_livery)

    page_number = request.GET.get('page')

    old_livery.delete()
    return redirect('/admin/livery-management/?page=' + str(page_number))

@login_required(login_url='/admin/login/')
def flip_livery(request):    
    return render(request, 'flip.html')
