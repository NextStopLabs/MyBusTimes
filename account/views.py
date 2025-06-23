# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from .forms import CustomUserCreationForm
from main.models import CustomUser
from fleet.models import MBTOperator, helper, fleetChange

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Optional: log in after registration
            return redirect(f'/u/{user.username}')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

def user_profile(request, username):
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
    ]

    profile_user = get_object_or_404(CustomUser, username=username)

    # Operators owned by this user
    operators = MBTOperator.objects.filter(owner=profile_user)

    # Operators the user helps with
    helper_operator_links = helper.objects.filter(helper=profile_user)
    helper_operators_list = MBTOperator.objects.filter(id__in=helper_operator_links.values('operator'))

    user_edits = fleetChange.objects.filter(user=profile_user).order_by('-create_at')

    # Check if viewing own profile
    owner = request.user == profile_user

    context = {
        'breadcrumbs': breadcrumbs,
        'profile_user': profile_user,
        'operators': operators,
        'helper_operators_list': helper_operators_list,
        'owner': owner,
        'user_edits': user_edits,
    }

    return render(request, 'profile.html', context)
