# Standard library imports
import datetime
import json
import logging
import os
from datetime import timedelta
from random import randint

# Django imports
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import logout

# Third-party imports
import stripe
from dotenv import load_dotenv
from rest_framework import generics, permissions, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

# Local imports
from .forms import CustomUserCreationForm
from fleet.models import MBTOperator, fleetChange, helper
from main.models import CustomUser


logger = logging.getLogger(__name__)
User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY

debug = settings.DEBUG


class CustomLoginView(LoginView):
    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user

        # Get IP address
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else self.request.META.get('REMOTE_ADDR')

        user.last_login_ip = ip
        user.last_login = now()
        user.save(update_fields=["last_login_ip", "last_login"])

        return response
    
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Check for spaces in username
            if ' ' in form.cleaned_data['username']:
                form.add_error('username', 'Username cannot contain spaces')
            else:
                user = form.save()
                user.backend = settings.AUTHENTICATION_BACKENDS[0]  # Set backend
                login(request, user)  # Log in using the set backend
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
    operators = MBTOperator.objects.filter(owner=profile_user).order_by('operator_name')

    # Operators the user helps with
    helper_operator_links = helper.objects.filter(helper=profile_user).order_by('operator__operator_name')
    helper_operators_list = MBTOperator.objects.filter(id__in=helper_operator_links.values('operator'))

    user_edits = fleetChange.objects.filter(user=profile_user).order_by('-create_at')[:10]

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

# Price IDs from .env
if debug == False:
    price_ids = {
        'monthly': os.getenv("PRICE_ID_MONTHLY"),
        'yearly': os.getenv("PRICE_ID_YEARLY"),
        'custom': os.getenv("PRICE_ID_CUSTOM"),
    }
else:
    price_ids = {
        'monthly': os.getenv("PRICE_ID_MONTHLY_TEST"),
        'yearly': os.getenv("PRICE_ID_YEARLY_TEST"),
        'custom': os.getenv("PRICE_ID_CUSTOM_TEST"),
    }

@login_required
def cancel_subscription(request):
    user = request.user
    subscription_id = getattr(user, 'stripe_subscription_id', None)

    if not subscription_id:
        return render(request, 'cancel_subscription.html', {
            'error_message': 'You do not have an active subscription to cancel.'
        })

    if request.method == 'POST':
        try:
            # Cancel subscription at period end (change `at_period_end=False` to cancel immediately)
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
            message = 'Your subscription will be cancelled at the end of the current billing period.'
            return render(request, 'cancel_subscription.html', {'success_message': message})
        except Exception as e:
            return render(request, 'cancel_subscription.html', {
                'error_message': f'Error cancelling subscription: {str(e)}'
            })

    return render(request, 'cancel_subscription.html')

@login_required
def subscribe_ad_free(request):
    if request.method == 'POST':
        plan = request.POST.get('plan')
        user = request.user
        now = timezone.now()

        months = 1
        if plan in ['custom', 'gift']:
            try:
                months = int(request.POST.get('custom_months', 1))
                if months < 1:
                    raise ValueError
            except ValueError:
                return render(request, 'subscribe.html', {
                    'error_message': 'Invalid number of months',
                    'month_options': range(1, 13),
                })

        gift_username = None
        if plan == 'gift':
            gift_username = request.POST.get('gift_username', '').strip()
            if not gift_username:
                return render(request, 'subscribe.html', {
                    'error_message': 'Gift username is required',
                    'gift_username_error': True,
                    'month_options': range(1, 13),
                })

            if not User.objects.filter(username=gift_username).exists():
                return render(request, 'subscribe.html', {
                    'error_message': 'User not found. Please check the username.',
                    'gift_username_error': True,
                    'gift_username_value': gift_username,
                    'month_options': range(1, 13),
                })

        try:
            line_items = [{
                'price': price_ids['custom'] if plan in ['custom', 'gift'] else price_ids[plan],
                'quantity': months if plan in ['custom', 'gift'] else 1,
            }]

            metadata = {
                'user_id': str(user.id),
                'plan': plan,
                'months': str(months),
            }
            if gift_username:
                metadata['gift_username'] = gift_username

            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment' if plan in ['custom', 'gift'] else 'subscription',
                success_url=request.build_absolute_uri(
                    reverse('payment_success')
                ) + f'?plan={plan}&months={months}&gift_username={gift_username}',
                cancel_url=request.build_absolute_uri(reverse('payment_cancel')),
                customer_email=user.email,
                client_reference_id=str(user.id),
                metadata=metadata,
            )
            return redirect(session.url, code=303)

        except Exception as e:
            logger.error(f"Stripe session error: {e}")
            return render(request, 'subscribe.html', {
                'error_message': f'Error creating Stripe session: {str(e)}',
                'month_options': range(1, 13),
            })

    return render(request, 'subscribe.html', {'month_options': range(1, 13)})

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.error(f"Stripe webhook error: {e}")
        return HttpResponse(status=400)

    if event['type'] in ['checkout.session.completed', 'checkout.session.async_payment_succeeded']:
        session = event['data']['object']
        metadata = session.get('metadata', {})
        user_id = metadata.get('user_id')
        gift_username = metadata.get('gift_username')
        months = int(metadata.get('months', 1))
        now = timezone.now()

        try:
            target_user = (User.objects.get(username=gift_username)
                           if gift_username else
                           User.objects.get(id=user_id))
            if target_user.ad_free_until and target_user.ad_free_until > now:
                target_user.ad_free_until += timedelta(days=30 * months)
            else:
                target_user.ad_free_until = now + timedelta(days=30 * months)
            target_user.save()
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                metadata = session.get('metadata', {})
                user_id = metadata.get('user_id')

                # Save subscription ID if this is a subscription mode
                subscription_id = session.get('subscription')

                try:
                    user = User.objects.get(id=user_id)
                    if subscription_id:
                        user.stripe_subscription_id = subscription_id
                        user.save()
                except User.DoesNotExist:
                    logger.error(f"User not found for webhook: user_id={user_id}")

        except User.DoesNotExist:
            logger.error(f"Stripe webhook failed: user not found for user_id={user_id} or gift_username={gift_username}")

    return HttpResponse(status=200)

@login_required
def payment_success(request):
    return render(request, 'payment_success.html')

@login_required
def payment_cancel(request):
    return render(request, 'payment_cancel.html')

def create_checkout_session(request):
    YOUR_DOMAIN = 'https://mbtv2-test-dont-fucking-share-this-link.mybustimes.cc'
    plan = request.POST.get('plan', 'monthly')
    months = int(request.POST.get('custom_months', 1))  # for custom/gift quantity
    gift_username = request.POST.get("gift_username", "").strip()

    # Select username based on plan
    username = gift_username if plan == 'gift' else request.POST.get("username_form", "").strip()

    # Check if user exists in CustomUsers model
    if plan == 'gift':
        queryset = CustomUser.objects.all()
        user_exists = queryset.filter(username=username).exists()
        if not user_exists:
            # Redirect to an error page or back with a message
            #return render(request, 'subscribe.html', {'gift_username_error': True})
            return render(request, 'subscribe.html', {
                    'error_message': 'User not found. Please check the username and try again.',
                    'gift_username_error': True,
                    'gift_username_value': gift_username,
                    'month_options': range(1, 13),
                })

    else:
        # For other plans, you may want to verify user in the default User model or skip
        queryset = CustomUser.objects.all()
        user_exists = queryset.filter(username=username).exists()
        if not user_exists:
            return redirect("/account/login/?next=/account/subscribe/")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_ids['custom'] if plan in ['custom', 'gift'] else price_ids[plan],
                'quantity': months if plan in ['custom', 'gift'] else 1,
            }],
            mode='payment' if plan in ['custom', 'gift'] else 'subscription',
            success_url=YOUR_DOMAIN + f'/account/subscribe/success/?plan={plan}&months={months}&gift_username={gift_username}',
            cancel_url=YOUR_DOMAIN + '/account/subscribe/',
            customer_email=request.user.email if request.user.is_authenticated else None,
            metadata={
                'user_id': str(request.user.id),
                'plan': plan,
                'months': str(months),
                'gift_username': gift_username,
            },
        )

        return redirect(session.url, code=303)

    except Exception as e:
        return render(request, 'error.html', {'message': str(e)})
    
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image

@login_required
def account_settings(request):
    user = request.user

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        reg_background = request.POST.get('reg_background') == 'on'  # Convert checkbox to boolean
        pfp = request.FILES.get('pfp')
        banner = request.FILES.get('banner')

        if not username or not email:
            messages.error(request, "Username and email are required.")
            return redirect('account_settings')

        user.username = username
        user.email = email
        user.discord_username = request.POST.get('discord_username', '').strip()  # Get Discord username
        user.reg_background = reg_background  # Update reg_background setting
        
        def compress_image(uploaded_file, max_size=1600, quality=80):
            try:
                img = Image.open(uploaded_file)
                img = img.convert('RGB')  # Ensure no alpha channel issues

                # Resize maintaining aspect ratio
                width, height = img.size
                if width > max_size:
                    height = int(height * max_size / width)
                    width = max_size
                    img = img.resize((width, height), Image.Resampling.LANCZOS) 

                # Save to BytesIO in WebP format
                output_io = BytesIO()
                img.save(output_io, format='WEBP', quality=quality)
                output_io.seek(0)

                # Create a ContentFile for Django model
                return ContentFile(output_io.read(), name=f'{uploaded_file.name.rsplit(".",1)[0]}.webp')
            except Exception as e:
                print("Image compression error:", e)
                return uploaded_file  # fallback: return original

        if pfp:
            compressed_pfp = compress_image(pfp, max_size=300, quality=80)
            user.pfp.save(compressed_pfp.name, compressed_pfp, save=False)

        if banner:
            compressed_banner = compress_image(banner, max_size=1600, quality=80)
            user.banner.save(compressed_banner.name, compressed_banner, save=False)

        user.save()
        messages.success(request, "Account settings updated successfully.")
        return redirect('user_profile', username=user.username)
    
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Account Settings', 'url': reverse('account_settings')},
    ]

    return render(request, 'account_settings.html', {'user': user, 'breadcrumbs': breadcrumbs})

@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        logout(request)  # Ends the session before deleting
        user.delete()    # Deletes the user from the DB
        return redirect('/')
    
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Account Settings', 'url': reverse('account_settings')},
    ]

    return render(request, 'delete_account.html', {'user': request.user, 'breadcrumbs': breadcrumbs})

@login_required
def ticketer_code(request):
    user = request.user

    if request.method == 'POST':
        random_code = request.POST.get('ticketer_code', '').strip()

        user.ticketer_code = random_code
        user.save()

        return render(request, 'ticketer_code.html', {'user': user})

    if user.ticketer_code is None:
        random_code = randint(100000, 999999)  # Generate a random 6-digit code

        user.ticketer_code = random_code
        user.save()

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Account Settings', 'url': reverse('account_settings')},
    ]

    return render(request, 'ticketer_code.html', {'user': user, 'breadcrumbs': breadcrumbs})