from django.urls import path
from a import views

urlpatterns = [
    path('<str:name>', views.affiliate_link, name='affiliate_link'),
]