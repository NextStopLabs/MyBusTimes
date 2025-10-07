# Standard library imports
import datetime
import json
import logging
import os
from datetime import timedelta
from random import randint
import re 

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
from .forms import CustomUserCreationForm, AccountSettingsForm
from fleet.models import MBTOperator, fleetChange, helper
from main.models import CustomUser, UserKeys, badge
from a.models import AffiliateLink

import requests

logger = logging.getLogger(__name__)
User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY

debug = settings.DEBUG

def validate_turnstile(token, remoteip=None):
    if debug:
        return {'success': True}
    else:
        url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'

        data = {
            'secret': settings.CF_SECRET_KEY,
            'response': token
        }

        if remoteip:
            data['remoteip'] = remoteip

        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Turnstile validation error: {e}")
            return {'success': False, 'error-codes': ['internal-error']}

class CustomLoginView(LoginView):
    def form_valid(self, form):
        token = self.request.POST.get('cf-turnstile-response')
        remoteip = (
            self.request.headers.get('CF-Connecting-IP')
            or self.request.headers.get('X-Forwarded-For')
            or self.request.META.get('REMOTE_ADDR')
        )

        validation = validate_turnstile(token, remoteip)

        if not validation.get('success'):
            form.add_error(None, "Captcha validation failed. Please try again.")
            return self.form_invalid(form)

        response = super().form_valid(form)
        user = self.request.user

        # Get IP address
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else self.request.META.get('REMOTE_ADDR')

        # Save login info
        user.last_login_ip = ip
        user.last_login = now()
        user.save(update_fields=["last_login_ip", "last_login"])

        return response
    
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            token = request.POST.get('cf-turnstile-response')
            remoteip = (
                request.headers.get('CF-Connecting-IP')
                or request.headers.get('X-Forwarded-For')
                or request.META.get('REMOTE_ADDR')
            )

            validation = validate_turnstile(token, remoteip)

            if validation['success']:
                if ' ' in form.cleaned_data['username']:
                    form.add_error('username', 'Username cannot contain spaces')
                else:
                    user = form.save()

                    # ✅ check for invite cookie
                    invite_id = request.COOKIES.get("invite_id")
                    if invite_id:
                        try:
                            link = AffiliateLink.objects.get(id=invite_id)
                            link.signups_from_clicks += 1
                            link.save()

                        except AffiliateLink.DoesNotExist:
                            pass

                    # log the new user in
                    user.backend = settings.AUTHENTICATION_BACKENDS[0]
                    login(request, user)

                    response = redirect(f'/u/{user.username}')

                    # ✅ optionally clear the cookie so it’s not reused
                    response.delete_cookie("invite_id")

                    return response
    else:
        form = CustomUserCreationForm()

    return render(request, 'register.html', {'form': form})

def user_profile(request, username):
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
    ]

    profile_user = get_object_or_404(CustomUser, username=username)

    # Operators owned by this user
    operators = MBTOperator.objects.filter(owner=profile_user).order_by('operator_slug')

    # Operators the user helps with
    helper_operator_links = helper.objects.filter(helper=profile_user).order_by('operator__operator_name')
    helper_operators_list = MBTOperator.objects.filter(id__in=helper_operator_links.values('operator')).order_by('operator_name')

    user_edits = fleetChange.objects.filter(user=profile_user).order_by('-create_at')[:10]

    # Check if viewing own profile
    owner = request.user == profile_user

    online = False
    if profile_user.last_active and profile_user.last_active > timezone.now() - timedelta(minutes=5):
        online = True

    context = {
        'breadcrumbs': breadcrumbs,
        'profile_user': profile_user,
        'operators': operators,
        'helper_operators_list': helper_operators_list,
        'owner': owner,
        'online': online,
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

    today = timezone.now()
    current_sub_count = CustomUser.objects.filter(
        ad_free_until__gt=today,
        is_staff=False
    ).count()

    return render(request, 'subscribe.html', {'month_options': range(1, 13), 'current_sub_count': current_sub_count})

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
    YOUR_DOMAIN = 'https://www.mybustimes.cc'
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
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        reg_background = request.POST.get('reg_background') == 'on'
        pfp = request.FILES.get('pfp')
        banner = request.FILES.get('banner')

        # Basic required field check
        if not username or not email:
            messages.error(request, "Username and email are required.")
            return redirect('account_settings')

        # Username validation
        if not re.match(r'^[\w.@+-]+$', username):
            messages.error(request, "Enter a valid username. This value may contain only letters, numbers, and @/./+/-/_ characters.")
            return redirect('account_settings')

        # Update user fields
        user.username = username
        user.email = email
        user.discord_username = request.POST.get('discord_username', '').strip()
        user.reg_background = reg_background

        # Image compression function
        def compress_image(uploaded_file, max_size=1600, quality=80):
            try:
                img = Image.open(uploaded_file)
                img = img.convert('RGB')

                width, height = img.size
                if width > max_size:
                    height = int(height * max_size / width)
                    width = max_size
                    img = img.resize((width, height), Image.Resampling.LANCZOS)

                output_io = BytesIO()
                img.save(output_io, format='WEBP', quality=quality)
                output_io.seek(0)
                return ContentFile(output_io.read(), name=f'{uploaded_file.name.rsplit(".",1)[0]}.webp')
            except Exception as e:
                print("Image compression error:", e)
                return uploaded_file

        if pfp:
            compressed_pfp = compress_image(pfp, max_size=300, quality=80)
            user.pfp.save(compressed_pfp.name, compressed_pfp, save=False)

        if banner:
            compressed_banner = compress_image(banner, max_size=1600, quality=80)
            user.banner.save(compressed_banner.name, compressed_banner, save=False)

        user.save()
        messages.success(request, "Account settings updated successfully.")
        return redirect('user_profile', username=user.username)
    else:
        form = AccountSettingsForm(instance=user)

    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Account Settings', 'url': reverse('account_settings')},
    ]

    context = {
        'form': form,
    }
    return render(request, 'account_settings.html', {'breadcrumbs': breadcrumbs, **context})

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

@csrf_exempt
def give_badge(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    import json
    try:
        data = json.loads(request.body)
        session_key = data.get("session_key")
        give_to_username = data.get("user")
        badge_name = data.get("badge")
        give = data.get("give", True)

        give_to_user = CustomUser.objects.filter(username=give_to_username).first()
        if not give_to_user:
            return JsonResponse({"error": "User not found"}, status=404)

        badge_to_give = badge.objects.filter(badge_name=badge_name).first()
        if not badge_to_give:
            return JsonResponse({"error": "Badge not found"}, status=404)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not session_key:
        return JsonResponse({"error": "Missing session_key"}, status=401)

    # validate session
    try:
        user_key = UserKeys.objects.select_related("user").get(session_key=session_key)
        user = user_key.user

        if not user.is_superuser:
            return JsonResponse({"error": "Permission denied"}, status=403)
    except UserKeys.DoesNotExist:
        return JsonResponse({"error": "Invalid session key"}, status=401)

    if not give:
        give_to_user.badges.remove(badge_to_give)
        give_to_user.save()
        return JsonResponse({"success": "Badge removed successfully"}, status=200)

    give_to_user.badges.add(badge_to_give)
    give_to_user.save()

    return JsonResponse({"success": "Badge given successfully"}, status=200)

@csrf_exempt
def get_all_available_badges(request):
    if request.method != "GET":
        return JsonResponse({"error": "Only GET allowed"}, status=405)

    badges = badge.objects.all().values("badge_name").order_by("badge_name")
    return JsonResponse({"badges": list(badges)}, status=200)