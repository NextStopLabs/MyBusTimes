from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .forms import AdForm, LiveryForm
from .models import CustomModel
from main.models import CustomUser, badge, ad, featureToggle
from fleet.models import liverie, fleet
import requests
from django.template.loader import render_to_string

def has_permission(user, perm_name):
    if user.is_superuser:
        return True
    return user.mbt_admin_perms.filter(name=perm_name).exists()

def permission_denied(request):
    return render(request, 'now-access.html')

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
            response = requests.get("http://184.174.17.73:800/index.php?module=API&method=VisitsSummary.get&idSite=2&period=day&date=yesterday&format=JSON&token_auth=068ac2f37b631d5bb713b246516e88b1")
        else:
            response = requests.get("http://184.174.17.73:800/index.php?module=API&method=VisitsSummary.get&idSite=2&period=day&date=today&format=JSON&token_auth=068ac2f37b631d5bb713b246516e88b1")

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
            response = requests.get("http://184.174.17.73:800/index.php?module=API&method=VisitsSummary.get&idSite=2&period=week&date=lastweek&format=JSON&token_auth=068ac2f37b631d5bb713b246516e88b1")
        else:  # Default to today
            response = requests.get("http://184.174.17.73:800/index.php?module=API&method=VisitsSummary.get&idSite=2&period=week&date=today&format=JSON&token_auth=068ac2f37b631d5bb713b246516e88b1")

        dataWeek = response.json()
        return JsonResponse(dataWeek)
    except Exception as e:
        return JsonResponse({"error": str(e)})

@login_required(login_url='/admin/login/')
def fetch_traffic_live_data(request):
    if not has_permission(request.user, 'analytics'):
        return JsonResponse({"error": str("No permission")})
    
    try:
        response = requests.get("http://184.174.17.73:800/index.php?module=API&method=Live.getCounters&idSite=2&lastMinutes=15&format=JSON&token_auth=068ac2f37b631d5bb713b246516e88b1")
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
    
    feature_toggles = featureToggle.objects.filter(name__in=['MBT Ads', 'Google Ads', 'Ads'])

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
    
    users = CustomUser.objects.all()  # Get all users from CustomUser
    return render(request, 'users.html', {'users': users})  # Send the data to the template

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
