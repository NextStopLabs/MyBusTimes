from django.urls import path
from a import views

urlpatterns = [
    path('your_link/', views.your_link, name='your_link'),
    path('<str:name>', views.affiliate_link, name='affiliate_link'),
]