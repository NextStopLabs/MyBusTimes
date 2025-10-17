from django.shortcuts import render, redirect
from .models import Link, AffiliateLink
from main.models import CustomUser as User
from django.db.models import Sum

# Create your views here.
def a(request, name):
    link = Link.objects.filter(name=name).first()
    if link:
        link.clicks += 1
        link.save()
        return redirect(link.url)
    else:
        return render(request, 'error/404.html', status=404)
    
def affiliate_link(request, name):
    link = AffiliateLink.objects.filter(tag=name).first()

    if not link:
        tag_base = name.split('-')[0]
        user = User.objects.filter(username=tag_base).first()
        if not user:
            return render(request, 'error/404.html', status=404)
        link = AffiliateLink.objects.create(tag=name, user=user)

    link.clicks += 1
    link.save()

    response = redirect("/u/register/")

    response.set_cookie(
        key="invite_id",
        value=link.id,
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        secure=True
    )
    return response

def your_link(request):
    if not request.user.is_authenticated:
        return redirect('/u/login/?next=/invite/your-link/')
    
    user = request.user
    user_link = "/invite/" + user.username
    
    current_invites = AffiliateLink.objects.filter(user=user).aggregate(
        total_clicks=Sum("clicks")
    )["total_clicks"] or 0

    signups = AffiliateLink.objects.filter(user=user).aggregate(
        total_signups=Sum("signups_from_clicks")
    )["total_signups"] or 0

    context = {
        'user_link': user_link,
        'current_invites': current_invites,
        'signups': signups,
    }

    return render(request, 'your_link.html', context)