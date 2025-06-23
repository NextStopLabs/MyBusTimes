# urls.py
from django.urls import path
from django.contrib.auth.views import LoginView
from .views import register_view, user_profile
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('register/', register_view, name='register'),
    path('password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('<str:username>/', user_profile, name='user_profile')
]
