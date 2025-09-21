from django.shortcuts import render, redirect
from .models import Link, AffiliateLink
from main.models import CustomUser as User

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
        value=link.id,                    # store the ID, not the whole object
        max_age=60 * 60 * 24 * 30,        # 30 days
        httponly=True,                    # protect from JS
        secure=True                       # only over HTTPS
    )
    return response