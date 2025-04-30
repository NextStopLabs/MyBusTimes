from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from .models import CustomModel
from mybustimes.models import CustomUser, badge
import requests

def has_permission(user, perm_name):
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
    if not has_permission(request.user, 'admin_dash'):
        return redirect('/admin/permission-denied/')
    
    try:
        response = requests.get("http://184.174.17.73:800/index.php?module=API&method=Live.getCounters&idSite=2&lastMinutes=15&format=JSON&token_auth=068ac2f37b631d5bb713b246516e88b1")
        dataLive = response.json()
        # Return only the visits count as a JSON response
        return JsonResponse({'visits': dataLive[0]['visits']})
    except Exception as e:
        return JsonResponse({"error": str(e)})

@login_required(login_url='/admin/login/')
def dashboard_view(request):
    if not has_permission(request.user, 'analytics'):
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
def users_view(request):
    if not has_permission(request.user, 'user managment'):
        return redirect('/admin/permission-denied/')
    
    users = CustomUser.objects.all()  # Get all users from CustomUser
    return render(request, 'users.html', {'users': users})  # Send the data to the template

@login_required(login_url='/admin/login/')
def ads_view(request):
    if not has_permission(request.user, 'ad managment'):
        return redirect('/admin/permission-denied/')
    
    ads = CustomModel.objects.all()
    return render(request, 'ads.html', {'ads': ads})

@login_required(login_url='/admin/login/')
def feature_toggles_view(request):
    if not has_permission(request.user, 'feature_toggle_view'):
        return redirect('/admin/permission-denied/')
    
    feature_toggles = CustomModel.objects.all()
    return render(request, 'feature_toggles.html', {'feature_toggles': feature_toggles})

@login_required(login_url='/admin/login/')
def edit_user(request, user_id):
    if not has_permission(request.user, 'user managment'):
        return redirect('/admin/permission-denied/')
    
    badges = badge.objects.all()
    user = CustomUser.objects.get(id=user_id)
    return render(request, 'edit_user.html', {'user': user, 'badges': badges})

@login_required(login_url='/admin/login/')
def update_user(request, user_id):
    if not has_permission(request.user, 'user managment'):
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
    if not has_permission(request.user, 'user managment'):
        return redirect('/admin/permission-denied/')
    
    user = CustomUser.objects.get(id=user_id)
    user.delete()