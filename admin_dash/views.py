from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.core.validators import validate_ipv46_address
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from .forms import AdForm, LiveryForm, VehicleForm
from .models import CustomModel
from main.models import CustomUser, badge, ad, featureToggle, BannedIps, MBTTeam
from fleet.models import liverie, fleet, vehicleType
import requests
from django.template.loader import render_to_string
from django.db.models import Q
from django.shortcuts import get_object_or_404
from apply.models import Application
from messaging.models import Chat, ChatMember
from django.core.mail import send_mail
from django.conf import settings
import subprocess
import logging
from django.utils import timezone
from datetime import timedelta
from main.models import CustomUser as User
from django.contrib import messages
from django.db.models.functions import TruncDate
from django.db.models import Count
import json

def has_permission(user, perm_name):
    if user.is_superuser:
        return True

    if not user.mbt_team:
        return False  # no team, no perms

    team_perms = user.mbt_team.permissions.values_list('name', flat=True)

    return perm_name in team_perms

def permission_denied(request):
    return render(request, 'now-access.html')

def ban_user(request, user_id):
    if not has_permission(request.user, 'user_ban'):
        return redirect('/admin/permission-denied/')
    
    user = CustomUser.objects.get(id=user_id)

    if user.banned == True:
        user.banned = False
        user.save()
        return redirect("/admin/users-management/")

    user.banned = True
    user.save()
    return render(request, 'ban.html', {'user': user})


logger = logging.getLogger(__name__)

@login_required(login_url="/admin/login/")
def restart_service(request):
    if not has_permission(request.user, "restart_web"):
        return redirect("/admin/permission-denied/")

    try:
        # Call systemctl via sudo (allowed in /etc/sudoers.d/mybustimes)
        subprocess.run(["/usr/bin/sudo", "/usr/bin/systemctl", "restart", "mybustimes"], check=True)
        messages.success(request, "✅ Service restarted successfully")
    except subprocess.CalledProcessError as e:
        logger.error("Service restart failed: %s", e)
        messages.error(request, "❌ Failed to restart service")
    except FileNotFoundError as e:
        logger.error("systemctl not found: %s", e)
        messages.error(request, "❌ systemctl command not found on server")

    return redirect("/admin/")

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

    ip = user.last_login_ip
    try:
        validate_ipv46_address(ip)
    except (ValidationError, TypeError):  # TypeError covers ip=None
        ip = None

    if ip:
        BannedIps.objects.create(
            ip_address=ip,
            reason=request.POST.get('reason', 'No reason provided'),
            related_user=user
        )
    else:
        messages.error(request, "User banned but no valid IP found to ban.")

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

def get_user_joins_per_day(period="all"):
    today = timezone.now().date()
    start_date = None

    if period == "this_week":
        start_date = today - timedelta(days=today.weekday())  # Monday
    elif period == "last_week":
        start_date = today - timedelta(days=today.weekday() + 7)
        end_date = start_date + timedelta(days=6)
    elif period == "this_month":
        start_date = today.replace(day=1)
    elif period == "last_month":
        first_day_this_month = today.replace(day=1)
        start_date = (first_day_this_month - timedelta(days=1)).replace(day=1)
        end_date = first_day_this_month - timedelta(days=1)
    elif period == "this_year":
        start_date = today.replace(month=1, day=1)
    elif period == "last_year":
        start_date = today.replace(year=today.year - 1, month=1, day=1)
        end_date = today.replace(year=today.year - 1, month=12, day=31)

    qs = User.objects.annotate(day=TruncDate("date_joined"))

    if start_date:
        if "end_date" in locals():
            qs = qs.filter(date_joined__date__gte=start_date, date_joined__date__lte=end_date)
        else:
            qs = qs.filter(date_joined__date__gte=start_date)

    data = (
        qs.values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    return [{"day": entry["day"].isoformat(), "count": entry["count"]} for entry in data]

@login_required(login_url='/admin/login/')
def dashboard_view(request):
    if not has_permission(request.user, 'admin_dash'):
        return redirect('/admin/permission-denied/')

    # Read filter from query param (?period=this_week)
    period = request.GET.get("period", "all")
    user_joins_per_day = get_user_joins_per_day(period)

    user_count = CustomUser.objects.count()
    cutoff = timezone.now() - timedelta(minutes=15)
    active_user_count = User.objects.filter(last_active__gte=cutoff, is_active=True).count()

    return render(request, 'dashboard.html', {
        'user_count': user_count,
        'active_user_count': active_user_count,
        'user_joins_per_day': json.dumps(user_joins_per_day),
        'current_period': period,
    })
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

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


@login_required(login_url='/admin/login/')
def livery_management(request):
    if not has_permission(request.user, 'livery_view'):
        return redirect('/admin/permission-denied/')


    search_query = request.GET.get('q', '')
    liveries_list = liverie.objects.filter(name__icontains=search_query, declined=False).order_by('name')

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
    vehicles_list = vehicleType.objects.filter(type_name__icontains=search_query, hidden=False).order_by('type_name')

    paginator = Paginator(vehicles_list, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # If AJAX, return partial HTML
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('partials/vehicle_table.html', {'page_obj': page_obj})
        return JsonResponse({'html': html})

    return render(request, 'vehicles-manage.html', {'page_obj': page_obj, 'search_query': search_query, 'approver': False})

@login_required(login_url='/admin/login/')
def vehicle_approver(request):
    if not has_permission(request.user, 'vehicle_view'):
        return redirect('/admin/permission-denied/')


    search_query = request.GET.get('q', '')
    vehicles_list = vehicleType.objects.filter(type_name__icontains=search_query, hidden=False, active=False).order_by('type_name')

    paginator = Paginator(vehicles_list, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # If AJAX, return partial HTML
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('partials/vehicle_table.html', {'page_obj': page_obj})
        return JsonResponse({'html': html})

    return render(request, 'vehicles-manage.html', {'page_obj': page_obj, 'search_query': search_query, 'approver': True})


@login_required(login_url='/admin/login/')
def livery_approver(request):
    if not has_permission(request.user, 'livery_view'):
        return redirect('/admin/permission-denied/')


    search_query = request.GET.get('q', '')
    liveries_list = liverie.objects.filter(name__icontains=search_query, published=False, declined=False).order_by('name')

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
    force = request.GET.get('force', 'false').lower() == 'true'

    if not has_permission(request.user, 'livery_publish'):
        return redirect('/admin/permission-denied/')
    
    page_number = request.GET.get('page')
    livery = liverie.objects.get(id=livery_id)
    checkDuplicate = liverie.objects.filter(name=livery.name).exclude(id=livery_id).exists()
    if not checkDuplicate or force == True:
        livery.published = True
        livery.aproved_by = request.user
        livery.save()
        return redirect('/admin/livery-management/pending/?page=' + str(page_number))

    return render(request, 'dupe_livery_check.html', {'livery': livery, 'other_liveries': liverie.objects.filter(name=livery.name).exclude(id=livery_id)})

@login_required(login_url='/admin/login/')
def publish_vehicle(request, vehicle_id):
    if not has_permission(request.user, 'vehicle_publish'):
        return redirect('/admin/permission-denied/')

    page_number = request.GET.get('page')

    vehicle = vehicleType.objects.get(id=vehicle_id)
    vehicle.active = True
    vehicle.save()

    return redirect('/admin/vehicle-management/pending/?page=' + str(page_number))

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
    
    # Use get_object_or_404 for better error handling
    livery = get_object_or_404(liverie, id=livery_id)

    page_number = request.GET.get('page', '1')

    # Check if any vehicle is using this livery
    if fleet.objects.filter(livery=livery).exists():
        other_liveries = liverie.objects.filter(name=livery.name).exclude(id=livery_id)
        return render(request, 'dupe_livery.html', {'livery': livery, 'other_liveries': other_liveries})

    livery.declined = True
    livery.save()
    return redirect(f'/admin/livery-management/pending/?page={page_number}')

@login_required(login_url='/admin/login/')
def delete_vehicle(request, vehicle_id):
    if not has_permission(request.user, 'vehicle_delete'):
        return redirect('/admin/permission-denied/')

    vehicle = vehicleType.objects.get(id=vehicle_id)
    page_number = request.GET.get('page')

    # Check if any vehicle in MyBusTimes.fleet is using this vehicle
    if fleet.objects.filter(vehicleType=vehicle).exists():
        other_vehicles = vehicleType.objects.filter(type_name=vehicle.type_name).exclude(id=vehicle_id)

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

    old_livery.declined = True
    old_livery.save()
    return redirect('/admin/livery-management/?page=' + str(page_number))

@login_required(login_url='/admin/login/')
def replace_vehicle(request):
    if not has_permission(request.user, 'vehicle_replace'):
        return redirect('/admin/permission-denied/')

    old_vehicle = vehicleType.objects.get(id=request.GET.get('old'))
    new_vehicle = vehicleType.objects.get(id=request.GET.get('new'))

    fleet.objects.filter(vehicleType=old_vehicle).update(vehicleType=new_vehicle)

    page_number = request.GET.get('page')

    old_vehicle.delete()
    return redirect('/admin/vehicle-management/?page=' + str(page_number))

@login_required(login_url='/admin/login/')
def applications_management(request):
    if not has_permission(request.user, 'applications_view'):
        return redirect('/admin/permission-denied/')

    page_number = request.GET.get('page', 1)
    applications_qs = Application.objects.all().order_by('-created_at')

    paginator = Paginator(applications_qs, 10)  # Show 10 applications per page
    try:
        applications = paginator.page(page_number)
    except PageNotAnInteger:
        applications = paginator.page(1)
    except EmptyPage:
        applications = paginator.page(paginator.num_pages)

    return render(request, 'applications_management.html', {
        'applications': applications
    })

@login_required(login_url='/admin/login/')
def application_detail(request, application_id):
    if not has_permission(request.user, 'applications_view'):
        return redirect('/admin/permission-denied/')

    application = get_object_or_404(Application, pk=application_id)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "continue":
            # Create a new group chat
            chat = Chat.objects.create(
                chat_type="group_private",
                name=f"Group chat for application #{application.id}",
                description=f"Group chat for application #{application.id}",
                created_by=request.user
            )

            # Add applicant
            ChatMember.objects.create(chat=chat, user=application.applicant, is_admin=False)

            # Add all users with mbt_admin permission
            admins = CustomUser.objects.filter(username=request.user.username).distinct()
            for admin_user in admins:
                ChatMember.objects.create(chat=chat, user=admin_user, is_admin=True)



            # Link the chat to the application
            application.chat = chat
            application.status = "accepted"
            application.save()

            # Send email to applicant
            chat_link = f"https://mybustimes.cc/chat/{chat.id}/"
            subject = "Your Application Has Been Accepted"
            message = (
                f"Hello {application.applicant.get_full_name() or application.applicant.username},\n\n"
                f"Your application has been accepted. We've created a group chat so we can continue the process.\n"
                f"You can join the chat here: {chat_link}\n\n"
                "Thank you,\nThe MyBusTimes Team"
            )

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [application.applicant.email],
                fail_silently=False,
            )

            return redirect("chat_detail", chat_id=chat.id)

        elif action == "decline":
            application.status = "declined"
            application.save()
            return redirect("applications_management")

    return render(request, "application_detail.html", {
        "application": application,
        "answers": application.question_answers or {}
    })

@login_required(login_url='/admin/login/')
def flip_livery(request):    
    return render(request, 'flip.html')
