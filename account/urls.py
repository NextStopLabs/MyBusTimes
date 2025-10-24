# urls.py
from django.urls import path
from django.contrib.auth.views import LoginView
from .views import *
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('login/', CustomLoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('register/', register_view, name='register'),
    path('subscribe/', subscribe_ad_free, name='subscribe'),
    path('subscribe/success/', payment_success, name='payment_success'),
    path('subscribe/cancel/', payment_cancel, name='payment_cancel'),
    path('subscribe/cancel-ad-free/', cancel_subscription, name='cancel_ad_free'),
    path('stripe/webhook/', stripe_webhook, name='stripe_webhook'),
    path('subscribe/create-checkout-session/', create_checkout_session, name='create_checkout_session'),
    path('settings/', account_settings, name='account_settings'),
    path('delete-account/', delete_account, name='delete_account'),
    path('TicketerCode/', ticketer_code, name='ticketer_code'),

    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='password_reset_form.html',
        email_template_name='password_reset_email.html',
        subject_template_name='password_reset_subject.txt',
        success_url='/password-reset/done/'
    ), name='password_reset'),

    path('<str:username>/liveries/', user_liveries, name='user_liveries'),
    path('<str:username>/', user_profile, name='user_profile'),
]