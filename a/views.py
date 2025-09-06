from django.shortcuts import render, redirect
from .models import Link

# Create your views here.
def a(request, name):
    link = Link.objects.filter(name=name).first()
    if link:
        link.clicks += 1
        link.save()
        return redirect(link.url)
    else:
        return render(request, 'error/404.html', status=404)