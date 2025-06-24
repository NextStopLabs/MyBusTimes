#python imports
import json
import random
import os
import requests

#app imports
from main.models import *
from fleet.models import *
from routes.models import *
from routes.serializers import *
from .forms import ReportForm

#django imports
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.utils.timezone import now

@require_POST
def set_theme(request):
    theme_id = request.POST.get('theme_id')

    try:
        selected_theme = theme.objects.get(pk=theme_id)
    except theme.DoesNotExist:
        return JsonResponse({'error': 'Invalid theme'}, status=400)

    if request.user.is_authenticated:
        # Save theme to user model
        request.user.theme = selected_theme
        request.user.save()
        response = JsonResponse({'message': 'Theme updated for user'})
    else:
        # Set theme cookie for anonymous users
        response = JsonResponse({'message': 'Theme set in cookie'})
        css_filename = selected_theme.css.name  # This might be "themes/MBT_Light.css"
        css_name_only = css_filename.split('/')[-1]  # This will give "MBT_Light.css"

        response.set_cookie('theme', css_name_only, max_age=60*60*24*365)
        response.set_cookie('themeDark', selected_theme.dark_theme, max_age=60*60*24*365)
        response.set_cookie('brandColour', selected_theme.main_colour, max_age=60*60*24*365)
        response.set_cookie('themeID', selected_theme.id, max_age=60*60*24*365)

    return response

def index(request):
    # Load mod.json messages as before
    mod_path = os.path.join(settings.MEDIA_ROOT, 'JSON', 'mod.json')
    with open(mod_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    messages = data.get('messages', [])
    message = random.choice(messages) if messages else "Welcome!"

    # Get all regions from DB, order by country and then name
    regions = region.objects.all().order_by('region_country', 'region_name')

    breadcrumbs = [{'name': 'Home', 'url': '/'}]

    context = {
        'breadcrumbs': breadcrumbs,
        'message': message,
        'regions': regions,
    }
    return render(request, 'index.html', context)

def region_view(request, region_code):
    try:
        region_instance = region.objects.get(region_code=region_code)
        operators = MBTOperator.objects.filter(region=region_instance).order_by('operator_name')
    except region.DoesNotExist:
        return render(request, '404.html', status=404)

    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': region_instance.region_name, 'url': f'/region/{region_code}/'}]

    context = {
        'breadcrumbs': breadcrumbs,
        'region': region_instance,
        'operators': operators,
    }
    return render(request, 'region.html', context)

def search(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return render(request, 'search.html', {'results': [], 'query': query})

    # Search for operators and vehicles
    operators = MBTOperator.objects.filter(
        Q(operator_name__icontains=query) | Q(operator_code__icontains=query)
    ).order_by('operator_name')

    vehicles = fleet.objects.filter(
        Q(reg__icontains=query) | Q(fleet_number__icontains=query)
    ).order_by('fleet_number')
    
    routes_qs = route.objects.filter(
        Q(route_name__icontains=query) | Q(route_num__icontains=query)
    ).order_by('route_num')

    users = CustomUser.objects.filter(
        Q(username__icontains=query)
    ).order_by('username')

    # Serialize the queryset
    full_routes = routesSerializer(routes_qs, many=True).data

    breadcrumbs = [{'name': 'Home', 'url': '/'}]

    print(f"Search query: {query}")
    print(f"Found {operators.count()} operators and {vehicles.count()} vehicles and {routes_qs.count()} routes and {users.count()} users for query '{query}'")

    context = {
        'breadcrumbs': breadcrumbs,
        'query': query,
        'operators': operators,
        'vehicles': vehicles,
        'routes': full_routes,
        'users': users,
    }
    return render(request, 'search.html', context)

def rules(request):
    breadcrumbs = [{'name': 'Home', 'url': '/'}]

    context = {
        'breadcrumbs': breadcrumbs,
    }
    return render(request, 'rules.html', context)

DISCORD_BOT_TOKEN = settings.DISCORD_BOT_TOKEN
DISCORD_CHANNEL_ID = settings.DISCORD_REPORTS_CHANNEL

def send_report_to_discord(report):
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    content = f"**New {report.report_type} Report**\n"
    content += f"Reporter: {report.reporter.username}\n"
    content += f"Details: {report.details}\n"
    content += f"Context: {report.context or 'None'}\n"
    content += f"Time: {report.created_at.strftime('%Y-%m-%d %H:%M')}"

    payload = {
        "content": content
    }

    url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages"
    requests.post(url, headers=headers, json=payload)

def report_view(request):
    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': 'Report', 'url': '/report'}]

    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.save()
            send_report_to_discord(report)
            return redirect('report_thank_you')  # Optional redirect
    else:
        form = ReportForm()

    return render(request, 'report.html', {
        'breadcrumbs': breadcrumbs,
        'form': form
    })

def report_thank_you_view(request):
    return render(request, 'report_thank_you.html')

def data(request):
    breadcrumbs = [{'name': 'Home', 'url': '/'}]

    context = {
        'breadcrumbs': breadcrumbs,
    }
    return render(request, 'data.html', context)

@login_required
def create_livery(request):
    if request.method == "POST":
        name = request.POST.get('livery-name', '').strip()
        colour = request.POST.get('livery-colour', '').strip()
        left_css = request.POST.get('livery-css-left', '').strip()
        right_css = request.POST.get('livery-css-right', '').strip()
        text_colour = request.POST.get('text-colour', '').strip()
        stroke_colour = request.POST.get('text-stroke-colour', '').strip()

        new_livery = liverie.objects.create(
            name=name,
            colour=colour,
            left_css=left_css,
            right_css=right_css,
            text_colour=text_colour,
            stroke_colour=stroke_colour,
            updated_at=now(),
            published=False,
            added_by=request.user
        )

        return redirect(f'/create/livery/progress/{new_livery.id}/')

    breadcrumbs = [{'name': 'Home', 'url': '/'}]
    liveries = liverie.objects.all()
    context = {
        'breadcrumbs': breadcrumbs,
        'liveryData': liveries,
    }
    return render(request, 'create_livery.html', context)

def create_livery_progress(request, livery_id):
    try:
        livery_instance = liverie.objects.get(pk=livery_id)
    except liverie.DoesNotExist:
        return render(request, '404.html', status=404)

    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': 'Create Livery', 'url': '/create/livery/'}, {'name': 'Progress', 'url': f'/create/livery/progress/{livery_id}/'}]

    context = {
        'breadcrumbs': breadcrumbs,
        'livery': livery_instance,
    }
    return render(request, 'create_livery_progress.html', context)

@csrf_exempt  # You may want to handle CSRF properly later
def valhalla_proxy(request, type):
    if request.method == "POST":
        try:
            response = requests.post(
                f"https://valhalla.mybustimes.cc/{type}",
                data=request.body,
                headers={"Content-Type": "application/json"}
            )
            return JsonResponse(response.json(), safe=False, status=response.status_code)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return HttpResponseBadRequest("Only POST allowed")

def for_sale(request):
    for_sale_vehicles = fleet.objects.filter(for_sale=True).order_by('fleet_number')
    
    # Group vehicles by operator
    operators_with_vehicles = {}
    for vehicle in for_sale_vehicles:
        if vehicle.operator not in operators_with_vehicles:
            operators_with_vehicles[vehicle.operator] = []
        operators_with_vehicles[vehicle.operator].append(vehicle)

    breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': 'For Sale', 'url': '/for-sale/'}]
    context = {
        'breadcrumbs': breadcrumbs,
        'for_sale_vehicles': for_sale_vehicles,
        'operators_with_vehicles': operators_with_vehicles,
    }

    return render(request, 'for_sale.html', context)