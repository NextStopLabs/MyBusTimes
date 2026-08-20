# Standard library imports
import datetime
import json
import logging
import os
import secrets
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
from django.utils.http import urlencode
from django.utils import timezone
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import logout
from rest_framework.decorators import api_view
from django.core.cache import cache
from django.db.models import Q
from two_factor.views import LoginView as TwoFactorLoginView
from django_otp import devices_for_user

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
from dateutil.relativedelta import relativedelta 

# Local imports
from .forms import CustomUserCreationForm, AccountSettingsForm
from fleet.models import group, MBTOperator, fleetChange, helper, liverie, operatorTransferRequest, reset_unavailable_map_tile_sets_for_user
from main.models import CustomUser, UserKeys, badge, StripeSubscription, ActiveSubscription
from a.models import AffiliateLink, Link
from main.models import featureToggle
from main.discord_roles import (
    clear_discord_booster_cache,
    sync_discord_ad_free_role,
    sync_discord_booster_subscription,
    sync_discord_entitlement_roles,
    sync_discord_pro_role,
    user_has_active_pro,
)
from words.models import bannedWord
from words.utils import banned_words_in_text
from mybustimes.http_client import get as http_get, post as http_post
from requests import RequestException

logger = logging.getLogger(__name__)
User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY

debug = settings.DEBUG

# Helpers for subscription handling
def username_banned_words(username):
    return banned_words_in_text(username, bannedWord.USERNAME_SCOPE)


def username_banned_message(blocked_words):
    words = ', '.join(sorted(set(blocked_words)))
    return f"Username contains a banned word: {words}."


def _price_catalog():
    """Return a map of Stripe price IDs to plan metadata."""
    catalog = {
        settings.STRIPE_BASIC_MONTHLY_PRICE_ID: {"months": 1, "plan": "basic", "mode": "subscription"},
        settings.STRIPE_BASIC_YEARLY_PRICE_ID: {"months": 12, "plan": "basic", "mode": "subscription"},
        settings.STRIPE_BASIC_ONE_OFF_PRICE_ID: {"months": 1, "plan": "basic", "mode": "payment"},
        settings.STRIPE_PRO_MONTHLY_PRICE_ID: {"months": 1, "plan": "pro", "mode": "subscription"},
        settings.STRIPE_PRO_YEARLY_PRICE_ID: {"months": 12, "plan": "pro", "mode": "subscription"},
        settings.STRIPE_PRO_ONE_OFF_PRICE_ID: {"months": 1, "plan": "pro", "mode": "payment"},
        # Legacy IDs for backward compatibility
        settings.STRIPE_MONTHLY_PRICE_ID: {"months": 1, "plan": "basic", "mode": "subscription"},
        settings.STRIPE_YEARLY_PRICE_ID: {"months": 12, "plan": "basic", "mode": "subscription"},
        settings.STRIPE_CUSTOM_PRICE_ID: {"months": 1, "plan": "basic", "mode": "subscription"},
    }
    # Drop None values to avoid key collisions
    return {pid: meta for pid, meta in catalog.items() if pid}


def _extend_ad_free_until(user, months):
    """Calculate new ad free expiry using legacy month-adding logic."""
    if months <= 0:
        return user.ad_free_until
    base = user.ad_free_until if user.ad_free_until and user.ad_free_until > timezone.now() else timezone.now()
    return base + relativedelta(months=months)


def _apply_subscription_benefits(user, months, plan_level):
    """Extend ad-free period and set plan level if provided."""
    new_until = _extend_ad_free_until(user, months)
    update_fields = []

    if new_until and (not user.ad_free_until or new_until > user.ad_free_until):
        user.ad_free_until = new_until
        update_fields.append("ad_free_until")

    if plan_level and plan_level in dict(CustomUser.PLAN_CHOICES):
        if user.sub_plan != plan_level:
            user.sub_plan = plan_level
            update_fields.append("sub_plan")

    if update_fields:
        user.save(update_fields=update_fields)

@login_required
def link_discord_account(request):
    client_id = settings.DISCORD_OAUTH_CLIENT_ID
    if not client_id:
        return render(request, 'link_discord.html', {'error': 'missing_config'})

    state = secrets.token_urlsafe(32)
    request.session["discord_oauth_state"] = state
    request.session["discord_oauth_next"] = request.GET.get("next") or reverse("account_settings")
    redirect_uri = getattr(settings, "DISCORD_OAUTH_REDIRECT_URI", None) or request.build_absolute_uri(reverse("discord_oauth_callback"))

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "identify",
        "state": state,
        "prompt": "consent",
    }
    return redirect(f"https://discord.com/oauth2/authorize?{urlencode(params)}")


@login_required
def discord_oauth_callback(request):
    expected_state = request.session.pop("discord_oauth_state", None)
    next_url = request.session.pop("discord_oauth_next", reverse("account_settings"))
    received_state = request.GET.get("state")
    code = request.GET.get("code")

    if not expected_state or received_state != expected_state or not code:
        return render(request, 'link_discord.html', {'error': 'state'})

    client_id = settings.DISCORD_OAUTH_CLIENT_ID
    client_secret = settings.DISCORD_OAUTH_CLIENT_SECRET
    if not client_id or not client_secret:
        return render(request, 'link_discord.html', {'error': 'missing_config'})

    redirect_uri = settings.DISCORD_OAUTH_REDIRECT_URI or request.build_absolute_uri(reverse("discord_oauth_callback"))
    try:
        token_response = http_post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]

        user_response = http_get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        user_response.raise_for_status()
        discord_user = user_response.json()
    except (KeyError, RequestException):
        logger.exception("Discord OAuth link failed")
        return render(request, 'link_discord.html', {'error': 'oauth'})

    discord_id = discord_user.get("id")
    if not discord_id:
        return render(request, 'link_discord.html', {'error': 'oauth'})

    existing = CustomUser.objects.filter(discord_id=discord_id).exclude(id=request.user.id).first()
    if existing:
        return render(request, 'link_discord.html', {'error': 'already_linked'})

    discriminator = discord_user.get("discriminator")
    username = discord_user.get("username") or ""
    request.user.discord_id = discord_id
    request.user.discord_username = (
        f"{username}#{discriminator}"
        if discriminator and discriminator != "0"
        else username
    )
    request.user.discord_global_name = discord_user.get("global_name") or ""
    request.user.discord_avatar = discord_user.get("avatar") or ""
    request.user.save(update_fields=[
        "discord_id",
        "discord_username",
        "discord_global_name",
        "discord_avatar",
    ])
    cache.delete(f"u_sub:{request.user.id}")
    clear_discord_booster_cache(request.user)

    role_syncs = sync_discord_entitlement_roles(request.user)
    counter = Link.objects.filter(pk=16).first()
    if counter:
        counter.clicks += 1
        counter.save(update_fields=["clicks"])

    if any(role_syncs.values()):
        messages.success(request, "Discord account linked successfully and your roles have been synced.")
    else:
        messages.success(request, "Discord account linked successfully.")
    return redirect(next_url)


@login_required
def disconnect_discord_account(request):
    if request.method == "POST":
        sync_discord_booster_subscription(request.user, False)
        sync_discord_pro_role(request.user, False)
        sync_discord_ad_free_role(request.user, False)
        request.user.discord_id = None
        request.user.discord_username = None
        request.user.discord_global_name = None
        request.user.discord_avatar = None
        request.user.save(update_fields=[
            "discord_id",
            "discord_username",
            "discord_global_name",
            "discord_avatar",
        ])
        cache.delete(f"u_sub:{request.user.id}")
        clear_discord_booster_cache(request.user)
        messages.success(request, "Discord account disconnected.")
    return redirect("account_settings")

from datetime import datetime
def send_to_discord_embed(channel_id, title, message, colour=0x00BFFF):
    embed = {
        "title": title,
        "description": message,
        "color": colour,
        "fields": [
            {
                "name": "Time",
                "value": datetime.now().strftime('%Y-%m-%d %H:%M'),
                "inline": True
            }
        ],
        "footer": {
            "text": "MBT Logging System"
        },
        "timestamp": datetime.now().isoformat()
    }

    data = {
        'channel_id': channel_id,
        'embed': embed
    }
    if not settings.DISABLE_JESS:
        try:
            response = http_post(
                f"{settings.DISCORD_BOT_API_URL}/send-embed",
                json=data,
                timeout=5,
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.exception("Failed to send embed to Discord: %s", e)
            return False


def validate_turnstile(token, remoteip=None):
    if settings.SKIP_CAPTCHA == True:
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
            response = http_post(url, data=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            print(f"Turnstile validation error: {e}")
            return {'success': False, 'error-codes': ['internal-error']}

class CustomLoginView(TwoFactorLoginView):

    def post(self, *args, **kwargs):
        if self.steps.current == 'auth':
            token = self.request.POST.get('cf-turnstile-response')
            remoteip = (
                self.request.headers.get('CF-Connecting-IP')
                or self.request.headers.get('X-Forwarded-For')
                or self.request.META.get('REMOTE_ADDR')
            )
            validation = validate_turnstile(token, remoteip)
            if not validation.get('success'):
                form = self.get_form()
                form.cleaned_data = getattr(form, 'cleaned_data', {})
                form.add_error(None, "Captcha validation failed. Please try again.")
                return self.render(form)

        if self.steps.current != self.steps.first and not self.get_user():
            self.show_timeout_error = True
            self.storage.reset()
            return self.render_goto_step(self.FIRST_STEP)

        return super().post(*args, **kwargs)

    def done(self, form_list, **kwargs):
        response = super().done(form_list, **kwargs)
        user = self.request.user
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else self.request.META.get('REMOTE_ADDR')
        user.last_login_ip = ip
        user.last_login = now()
        user.save(update_fields=["last_login_ip", "last_login"])
        return response
    
def register_view(request):
    register_enabled = cache.get('feature_toggle_state:register')
    if register_enabled is None:
        register_enabled = featureToggle.objects.filter(name="register").values('enabled').first()
        cache.set('feature_toggle_state:register', register_enabled, 60)
    if not register_enabled or not register_enabled['enabled']:
        return render(request, 'feature_disabled.html', {'feature_name': "register"}, status=200)

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

            # email and username validation
            if form.cleaned_data['email'] and CustomUser.objects.filter(email=form.cleaned_data['email']).exists():
                form.add_error('email', 'Email address is already in use.')

            if form.cleaned_data['username'] and CustomUser.objects.filter(username=form.cleaned_data['username']).exists():
                form.add_error('username', 'Username is already taken.')

            if ' ' in form.cleaned_data.get('username', ''):
                form.add_error('username', 'Username cannot contain spaces')

            blocked_words = username_banned_words(form.cleaned_data.get('username', ''))
            if blocked_words:
                form.add_error('username', username_banned_message(blocked_words))

            # 🔥 NEW IMPORTANT CHECK — DO NOT SAVE IF ERRORS WERE ADDED
            if form.errors:
                return render(request, 'register.html', {'form': form})

            # Continue only if validation success
            if validation['success']:
                # Rate limit signups by IP: max 5 signups per 10 minutes
                remoteip = (
                    request.headers.get('CF-Connecting-IP')
                    or request.headers.get('X-Forwarded-For')
                    or request.META.get('REMOTE_ADDR')
                )
                ip = remoteip.split(',')[0].strip() if remoteip else request.META.get('REMOTE_ADDR')

                LIMIT = 5
                WINDOW = 10 * 60  # seconds
                cache_key = f"signup:{ip}"

                current = cache.get(cache_key)
                if current is None:
                    cache.set(cache_key, 1, WINDOW)
                else:
                    if current >= LIMIT:
                        form.add_error(None, 'Too many signups from your IP address. Please try again later.')
                        return render(request, 'register.html', {'form': form})
                    cache.set(cache_key, current + 1, WINDOW)

                user = form.save(commit=False)
                user.last_ip = ip
                user.last_login_ip = ip
                user.save()

                # invite cookie support
                invite_id = request.COOKIES.get("invite_id")
                if invite_id:
                    try:
                        link = AffiliateLink.objects.get(id=invite_id)
                        link.signups_from_clicks += 1
                        link.save()
                    except AffiliateLink.DoesNotExist:
                        pass

                # login new user
                user.backend = settings.AUTHENTICATION_BACKENDS[0]
                login(request, user)

                response = redirect(f'/u/{user.username}')
                response.delete_cookie("invite_id")
                return response

    else:
        form = CustomUserCreationForm()

    return render(request, 'register.html', {'form': form})

def user_profile(request, username):
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
    ]

    profile_user = get_object_or_404(
        CustomUser.objects
        .select_related('mbt_team')
        .prefetch_related('badges', 'banned_from'),
        username=username,
    )

    # Operators owned by this user
    operators = (
        MBTOperator.objects
        .filter(owner=profile_user)
        .only('id', 'operator_name', 'operator_slug', 'operator_code')
        .order_by('operator_slug')
    )

    groups = (
        group.objects
        .filter(group_owner=profile_user)
        .only('id', 'group_name')
        .order_by('group_name')
    )

    # Operators the user helps with
    helper_operators_list = (
        MBTOperator.objects
        .filter(helper_operator__helper=profile_user)
        .only('id', 'operator_name', 'operator_slug', 'operator_code')
        .order_by('operator_name')
        .distinct()
    )

    user_edits = (
        fleetChange.objects
        .filter(user=profile_user)
        .select_related('vehicle', 'vehicle__operator', 'user')
        .only(
            'id', 'create_at', 'message', 'disapproved_reason',
            'vehicle__id', 'vehicle__fleet_number', 'vehicle__reg',
            'vehicle__operator__operator_slug',
            'user__id', 'user__username'
        )
        .order_by('-create_at')[:10]
    )

    # Check if viewing own profile
    owner = request.user == profile_user
    if owner:
        pending_transfers = (
            operatorTransferRequest.objects
            .filter(to_user=profile_user, status=operatorTransferRequest.PENDING)
            .select_related('operator', 'from_user')
            .order_by('-created_at')
        )
    else:
        pending_transfers = operatorTransferRequest.objects.none()

    now = timezone.now()

    online = False
    if profile_user.last_active and profile_user.last_active > timezone.now() - timedelta(minutes=5):
        online = True

    sub_status = {}

    # Filter to only currently active subscriptions
    user_active_subs = list(
        ActiveSubscription.objects.filter(
            user=profile_user,
            end_date__gt=now
        ).order_by('-end_date')
    )

    sub_count = len(user_active_subs)
    
    if sub_count > 1:
        counter = 0
        for sub in user_active_subs:
            counter += 1
            sub_status[f"sub_{counter}"] = {
                'plan': sub.plan,
                'until': sub.end_date.strftime("%Y-%m-%d"),
                'is_trial': sub.is_trial
            }
    elif sub_count == 1:
        sub = user_active_subs[0]
        sub_status["sub_1"] = {
            'plan': sub.plan,
            'until': sub.end_date.strftime("%Y-%m-%d"),
            'is_trial': sub.is_trial
        }
    else:
        sub_status["sub_1"] = {'plan': 'free', 'until': 'N/A', 'is_trial': False}

    context = {
        'sub_status': sub_status,
        'breadcrumbs': breadcrumbs,
        'profile_user': profile_user,
        'operators': operators,
        'groups': groups, 
        'helper_operators_list': helper_operators_list,
        'owner': owner,
        'online': online,
        'user_edits': user_edits,
        'pending_transfers': pending_transfers,
        'now': now,
    }

    return render(request, 'profile.html', context)

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
        except stripe.error.StripeError:
            logger.exception("Stripe error while cancelling subscription for user %s", user.id)
            return render(request, 'cancel_subscription.html', {
                'error_message': 'There was a problem contacting our payment provider. Please try again or contact support if the issue persists.'
            })
        except Exception:
            logger.exception("Unexpected error cancelling subscription for user %s", user.id)
            return render(request, 'cancel_subscription.html', {
                'error_message': 'An unexpected error occurred. Please try again or contact support.'
            })

    return render(request, 'cancel_subscription.html')

def calculate_sub_class(user):
    now = timezone.now()
    print(f"[calculate_sub_class] ── START for user: {user.username} | now: {now}")

    # Find the latest non-expired subscription record for this user
    all_subs = ActiveSubscription.objects.filter(user=user)
    print(f"[calculate_sub_class] Total ActiveSubscription rows for user: {all_subs.count()}")
    for s in all_subs:
        print(f"  → id={s.id} | plan={s.plan} | end_date={s.end_date} | stripe_id={s.stripe_subscription_id} | is_trial={s.is_trial}")

    sub_record = (
        all_subs
        .filter(Q(end_date__isnull=True) | Q(end_date__gt=now))
        .order_by("-end_date", "-id")
        .first()
    )
    print(f"[calculate_sub_class] Selected record after filter: {sub_record}")

    if not sub_record:
        print("[calculate_sub_class] No valid sub_record found → checking staff fallback")
        if user.is_staff:
            print("[calculate_sub_class] Staff user → returning basic_monthly")
            return "basic_monthly"
        print("[calculate_sub_class] Returning free (no record)")
        return "free"

    if not sub_record.stripe_subscription_id:
        print(f"[calculate_sub_class] sub_record id={sub_record.id} has no stripe_subscription_id")
        print(f"[calculate_sub_class] Stored plan on record: {sub_record.plan!r}")
        # No Stripe ID — use the stored plan directly if available
        if sub_record.plan:
            plan = sub_record.plan
            print(f"[calculate_sub_class] Returning stored plan: {plan!r}")
            return plan
        if user.is_staff:
            print("[calculate_sub_class] Staff user → returning basic_monthly")
            return "basic_monthly"
        print("[calculate_sub_class] Returning free (no stripe_id, no plan)")
        return "free"

    print(f"[calculate_sub_class] Retrieving Stripe subscription: {sub_record.stripe_subscription_id}")
    try:
        stripe_sub = stripe.Subscription.retrieve(sub_record.stripe_subscription_id)
        print(f"[calculate_sub_class] Stripe status: {stripe_sub.get('status')}")
    except Exception as exc:
        print(f"[calculate_sub_class] Stripe retrieve failed: {exc}")
        if user.is_staff:
            return "basic_monthly"
        return "free"

    items = stripe_sub.get("items", {}).get("data", []) if stripe_sub else []
    print(f"[calculate_sub_class] Stripe items count: {len(items)}")
    if not items:
        print("[calculate_sub_class] No items on Stripe subscription")
        if user.is_staff:
            return "basic_monthly"
        return "free"

    price_id = items[0].get("price", {}).get("id")
    print(f"[calculate_sub_class] Price ID from Stripe: {price_id!r}")
    price_map = _price_catalog()
    print(f"[calculate_sub_class] Price catalog keys: {list(price_map.keys())}")

    if price_id and price_id in price_map:
        plan = price_map[price_id]["plan"]
        interval_months = price_map[price_id].get("months", 1)
        print(f"[calculate_sub_class] Matched catalog → plan={plan!r}, months={interval_months}")
        if interval_months >= 12:
            return f"{plan}_yearly"
        if interval_months >= 1:
            return f"{plan}_monthly"
        return plan

    print(f"[calculate_sub_class] Price ID {price_id!r} not in catalog")
    if sub_record.plan:
        print(f"[calculate_sub_class] Falling back to stored plan: {sub_record.plan!r}")
        return sub_record.plan

    if user.is_staff:
        print("[calculate_sub_class] Staff user → returning basic_monthly")
        return "basic_monthly"

    print("[calculate_sub_class] Returning free (end of function)")
    return "free"

@login_required
def subscribe_ad_free(request):
    today = timezone.now()
    current_sub_count = CustomUser.objects.filter(
        ad_free_until__gt=today,
        is_staff=False
    ).count()

    had_pro_trial = request.user.had_pro_trial

    current_sub = calculate_sub_class(request.user)

    return render(request, 'subscribe.html', {'had_pro_trial': had_pro_trial, 'current_sub': current_sub, 'month_options': range(1, 13), 'current_sub_count': current_sub_count})

@login_required
def payment_success(request):
    return render(request, 'payment_success.html')

@login_required
def payment_cancel(request):
    return render(request, 'payment_cancel.html')

import datetime

class stripe_webhook(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def log(self, *args):
        print("[StripeWebhook DEBUG]", *args)

    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

        print("🔔 Received webhook POST")
        print("Payload (truncated):", payload[:300])

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except Exception as e:
            error_msg = f"Webhook verification failed: {str(e)}"
            print(f"❌ {error_msg}")
            return Response(status=400)

        event_type = event.get("type")
        data_obj = event.get("data", {}).get("object", {})

        print("📌 Event type:", event_type)

        try:
            if event_type == "checkout.session.completed":
                return self.handle_checkout_session_completed(data_obj)
            elif event_type == "invoice.payment_succeeded":
                return self.handle_invoice_payment_succeeded(data_obj)
            elif event_type == "customer.subscription.deleted":
                return self.handle_customer_subscription_deleted(data_obj)
            else:
                print("⚠ Unhandled event type:", event_type)
                return Response(status=200)

        except Exception as e:
            error_msg = f"Handler exception for {event_type}: {str(e)}"
            print(f"❗ {error_msg}")

            # Get full traceback for logging
            import traceback
            tb_str = traceback.format_exc()
            traceback.print_exc()

            return Response(status=500)

    def handle_checkout_session_completed(self, session):
        print("👉 Handling checkout.session.completed")
        print("Session metadata:", session.get("metadata"))

        user_id = session.get("client_reference_id")
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")

        if not user_id:
            print("❌ Missing client_reference_id in session")
            return Response(status=400)

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            print("❌ User not found:", user_id)
            return Response(status=404)

        # Ensure StripeSubscription record exists/updated
        if subscription_id:
            sub_defaults = {
                "user": user,
                "customer_id": customer_id,
                "product_name": "Ad free",
                "start_date": timezone.now().date(),
            }
            
            # Handle potential duplicates
            try:
                sub_obj, created = StripeSubscription.objects.update_or_create(
                    subscription_id=subscription_id,
                    defaults=sub_defaults,
                )
                if created:
                    print("✔ Created StripeSubscription record")
                else:
                    print("✔ Updated StripeSubscription record")
            except StripeSubscription.MultipleObjectsReturned:
                # Fix duplicates by keeping the most recent one
                print("⚠ Found duplicate StripeSubscription records, cleaning up...")
                duplicates = StripeSubscription.objects.filter(subscription_id=subscription_id).order_by('-id')
                keep = duplicates.first()
                delete_ids = list(duplicates.exclude(id=keep.id).values_list('id', flat=True))
                
                StripeSubscription.objects.filter(id__in=delete_ids).delete()
                print(f"✔ Deleted {len(delete_ids)} duplicate records, kept ID {keep.id}")
                
                # Update the kept record
                for key, value in sub_defaults.items():
                    setattr(keep, key, value)
                keep.save()
                sub_obj = keep

        # Save subscription ID
        if subscription_id:
            user.stripe_subscription_id = subscription_id
            print("✔ Stored stripe_subscription_id:", subscription_id)

        # If checkout session metadata has plan info, use it
        session_meta = session.get("metadata") or {}
        plan_level = session_meta.get("plan_level")
        months = session_meta.get("months")

        if plan_level:
            user.sub_plan = plan_level
            print("✔ Set plan from session metadata:", plan_level)

        if months:
            try:
                dur = int(months)
                user.ad_free_until = timezone.now() + datetime.timedelta(days=30*dur)
                print("✔ Set ad_free_until from session metadata:", user.ad_free_until)
            except Exception as e:
                print("⚠ Could not parse months metadata:", str(e))

        user.save(update_fields=["sub_plan", "ad_free_until", "stripe_subscription_id"])

        # Create ActiveSubscription record (works for both subscriptions and one-off payments)
        effective_plan = plan_level or "basic"
        if subscription_id:
            # For recurring subscriptions, use get_or_create with subscription_id
            ActiveSubscription.objects.get_or_create(
                stripe_subscription_id=subscription_id,
                defaults={
                    "user": user,
                    "start_date": timezone.now(),
                    "end_date": user.ad_free_until + timedelta(days=7), # grace period
                    "plan": effective_plan,
                    "is_trial": False,
                }
            )
            print("✔ Created ActiveSubscription record for subscription")
        elif plan_level and user.ad_free_until:
            # For one-off payments, create without subscription_id
            ActiveSubscription.objects.create(
                user=user,
                stripe_subscription_id=None,
                start_date=timezone.now(),
                end_date=user.ad_free_until + timedelta(days=7), # grace period
                plan=effective_plan,
                is_trial=False,
            )
            print("✔ Created ActiveSubscription record for one-off payment")

        print("✔ Completed checkout.session.completed")
        sync_discord_entitlement_roles(user)
        return Response(status=200)

    def handle_invoice_payment_succeeded(self, invoice):
        print("👉 Handling invoice.payment_succeeded")
        print("Invoice top-level metadata:", invoice.get("metadata"))

        print(" ")
        print("==============================")
        print("Full invoice payload:", invoice)
        print("==============================")
        print(" ")

        customer_id = invoice.get("customer")
        subscription_id = invoice.get("subscription")

        # If Stripe didn't set the top-level `subscription` field, try to
        # extract it from known nested locations
        if not subscription_id:
            try:
                # parent.subscription_details.subscription
                subscription_id = invoice.get("parent", {}).get("subscription_details", {}).get("subscription")
                if not subscription_id:
                    # lines -> first item -> parent -> subscription_item_details -> subscription
                    first_line_parent = invoice.get("lines", {}).get("data", [])[0].get("parent", {})
                    subscription_id = first_line_parent.get("subscription") or first_line_parent.get("subscription_item_details", {}).get("subscription") or first_line_parent.get("subscription_item", None)
                if subscription_id:
                    print("ℹ Extracted subscription_id from nested invoice data:", subscription_id)
            except Exception:
                pass

        customer_email = invoice.get("customer_email") or invoice.get("billing_reason")
        print("Invoice customer_id:", customer_id, "subscription_id:", subscription_id, "customer_email:", customer_email)

        # Find user
        user = None
        sub_obj = None
        if subscription_id:
            sub_obj = StripeSubscription.objects.filter(subscription_id=subscription_id).first()
            if sub_obj:
                user = sub_obj.user
                print("✔ Found user via subscription_id:", user.username)

        # Fallback: user might have the subscription id stored directly on CustomUser
        if not user and subscription_id:
            try:
                user_fallback = CustomUser.objects.filter(stripe_subscription_id=subscription_id).first()
                if user_fallback:
                    user = user_fallback
                    print("✔ Found user via CustomUser.stripe_subscription_id:", user.username)
            except Exception:
                pass

        if not user and customer_id:
            sub_obj = StripeSubscription.objects.filter(customer_id=customer_id).order_by("-id").first()
            if sub_obj:
                user = sub_obj.user
                print("✔ Found user via customer_id:", user.username)

        # Another fallback: try to match by customer email
        if not user and customer_email:
            try:
                user_email_match = CustomUser.objects.filter(email__iexact=customer_email).first()
                if user_email_match:
                    user = user_email_match
                    print("✔ Found user via invoice customer_email:", user.username)
            except Exception:
                pass

        if not user:
            error_msg = f"No linked user found for invoice {invoice.get('id')}"
            print(f"❌ {error_msg}")
            return Response(status=404)

        # Get first invoice line
        lines = invoice.get("lines", {}).get("data", [])
        if not lines:
            print("❌ No invoice lines found")
            return Response(status=400)

        first_line = lines[0]
        line_meta = first_line.get("metadata") or {}
        print("Line item metadata:", line_meta)

        # Extract billing period end
        period = first_line.get("period", {})
        period_end_ts = period.get("end")
        if not period_end_ts:
            print("❌ Missing period end on invoice line")
            return Response(status=400)

        ad_free_until = datetime.datetime.fromtimestamp(period_end_ts, tz=datetime.timezone.utc)
        print("✔ Calculated ad_free_until:", ad_free_until)
        if not user.ad_free_until or ad_free_until > user.ad_free_until:
            user.ad_free_until = ad_free_until

        # Extract plan from multiple possible sources
        plan_level = None
        
        # 1. Try line item metadata
        plan_level = line_meta.get("plan_level")
        if plan_level:
            print("✔ Found plan_level in line metadata:", plan_level)
        
        # 2. Try to extract from description (e.g., "MyBusTimes Basic Monthly")
        if not plan_level:
            description = first_line.get("description", "")
            print(f"  Parsing description: {description}")
            
            # Extract plan from description like "MyBusTimes Basic Monthly"
            if "Basic" in description:
                plan_level = "basic"
                print("✔ Extracted plan from description: basic")
            elif "Premium" in description or "Pro" in description:
                plan_level = "premium"
                print("✔ Extracted plan from description: premium")
        
        # 3. Try to get from Stripe product metadata
        if not plan_level:
            try:
                product_id = first_line.get("pricing", {}).get("price_details", {}).get("product")
                if product_id:
                    print(f"  Fetching product metadata for: {product_id}")
                    product = stripe.Product.retrieve(product_id)
                    plan_level = product.get("metadata", {}).get("plan_level")
                    if plan_level:
                        print("✔ Found plan_level in product metadata:", plan_level)
            except Exception as e:
                print(f"⚠ Could not fetch product metadata: {str(e)}")
        
        # 4. Set the plan level on the user
        if plan_level:
            user.sub_plan = plan_level
            print("✔ Set user.sub_plan to:", plan_level)
        else:
            # No plan found in any metadata - default to 'basic' for paid subscriptions
            user.sub_plan = "basic"
            print("⚠ No plan_level found in metadata, defaulting to 'basic'")

        user.save(update_fields=["ad_free_until", "sub_plan"])
        print("✔ User updated:", user.username, user.sub_plan, user.ad_free_until)

        # Determine start_date for the StripeSubscription record
        try:
            period_start_ts = first_line.get("period", {}).get("start") or invoice.get("period_start")
            if period_start_ts:
                start_date_date = datetime.datetime.fromtimestamp(period_start_ts, tz=datetime.timezone.utc).date()
            else:
                start_date_date = timezone.now().date()
        except Exception:
            start_date_date = timezone.now().date()

        # Determine effective subscription id
        effective_subscription_id = subscription_id
        if not effective_subscription_id and sub_obj and getattr(sub_obj, 'subscription_id', None):
            effective_subscription_id = sub_obj.subscription_id
            print("ℹ Using subscription_id from StripeSubscription record:", effective_subscription_id)

        # **FIX: Handle duplicate StripeSubscription records**
        if effective_subscription_id:
            try:
                StripeSubscription.objects.update_or_create(
                    subscription_id=effective_subscription_id,
                    defaults={
                        "start_date": start_date_date,
                        "end_date": ad_free_until.date(),
                        "user": user,
                        "customer_id": customer_id,
                    },
                )
                print("✔ Updated StripeSubscription end_date (by subscription_id)")
            except StripeSubscription.MultipleObjectsReturned:
                # Clean up duplicates
                print("⚠ Found duplicate StripeSubscription records, cleaning up...")
                duplicates = StripeSubscription.objects.filter(
                    subscription_id=effective_subscription_id
                ).order_by('-id')
                
                keep = duplicates.first()
                delete_ids = list(duplicates.exclude(id=keep.id).values_list('id', flat=True))

                StripeSubscription.objects.filter(id__in=delete_ids).delete()
                print(f"✔ Deleted {len(delete_ids)} duplicate records, kept ID {keep.id}")
                
                # Update the kept record
                keep.start_date = start_date_date
                keep.end_date = ad_free_until.date()
                keep.user = user
                keep.customer_id = customer_id
                keep.save()
                print("✔ Updated StripeSubscription end_date (after cleanup)")
                
        elif customer_id:
            # No subscription id available; update/create by customer_id
            StripeSubscription.objects.update_or_create(
                customer_id=customer_id,
                defaults={
                    "start_date": start_date_date,
                    "end_date": ad_free_until.date(),
                    "user": user,
                },
            )
            print("✔ Updated StripeSubscription end_date (by customer_id)")

        # Create or update ActiveSubscription for this payment period
        # Use the plan_level we extracted, fallback to user.sub_plan, default to "basic"
        effective_plan = plan_level or "basic"
        print(f"  Using effective_plan for ActiveSubscription: {effective_plan}")
        
        active_defaults = {
            "start_date": timezone.now(),
            "end_date": ad_free_until + timedelta(days=7),  # grace period
            "plan": effective_plan,
            "is_trial": False,
        }

        if effective_subscription_id:
            ActiveSubscription.objects.update_or_create(
                stripe_subscription_id=effective_subscription_id,
                defaults={"user": user, **active_defaults},
            )
            print("✔ Updated/created ActiveSubscription record for invoice payment")
        else:
            # Subscriptionless invoice (one-off payment)
            ActiveSubscription.objects.create(
                user=user,
                stripe_subscription_id="Renewed for invoice " + invoice.get("id"),
                **active_defaults,
            )
            print("✔ Created ActiveSubscription record (no subscription id) for invoice payment")

        sync_discord_entitlement_roles(user)
        return Response(status=200)

    def handle_customer_subscription_deleted(self, subscription):
        subscription_id = subscription.get("id")
        customer_id = subscription.get("customer")

        user = None
        if subscription_id:
            sub_obj = StripeSubscription.objects.filter(subscription_id=subscription_id).first()
            if sub_obj:
                user = sub_obj.user

        if not user and subscription_id:
            user = CustomUser.objects.filter(stripe_subscription_id=subscription_id).first()

        if not user and customer_id:
            sub_obj = StripeSubscription.objects.filter(customer_id=customer_id).order_by("-id").first()
            if sub_obj:
                user = sub_obj.user

        if not user:
            print(f"❌ No linked user found for subscription {subscription_id or customer_id}")
            return Response(status=404)

        if subscription_id:
            ActiveSubscription.objects.filter(stripe_subscription_id=subscription_id).update(end_date=timezone.now())
            if user.stripe_subscription_id == subscription_id:
                user.stripe_subscription_id = None
                user.sub_plan = "free"
                user.ad_free_until = None

        if not user_has_active_pro(user):
            user.sub_plan = "free"
            user.ad_free_until = None
            user.save(update_fields=["sub_plan", "ad_free_until", "stripe_subscription_id"])
            reset_unavailable_map_tile_sets_for_user(user)
            sync_discord_entitlement_roles(user)
        elif subscription_id:
            user.save(update_fields=["stripe_subscription_id"])
            sync_discord_entitlement_roles(user)

        return Response(status=200)

@api_view(["POST"])
def create_checkout_session(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY

    if request.data.get("product_type", "").endswith("_free_trial"):
        days = int(request.data.get("months", 7))
        product_type = request.data.get("product_type").replace("_free_trial", "")

        user = request.user
        current_ad_free = max(user.ad_free_until, timezone.now()) if user.ad_free_until else timezone.now()
        new_ad_free_until = current_ad_free + datetime.timedelta(days=days)

        user.sub_plan = product_type
        user.had_pro_trial = True
        user.ad_free_until = new_ad_free_until

        user.save(update_fields=["sub_plan", "had_pro_trial", "ad_free_until"])

        # Create ActiveSubscription record for the free trial
        ActiveSubscription.objects.create(
            user=user,
            stripe_subscription_id=None,
            start_date=timezone.now(),
            end_date=new_ad_free_until + timedelta(days=7), # grace period
            plan=product_type,
            is_trial=True
        )
        print("✔ Created ActiveSubscription for free trial")

        sync_discord_entitlement_roles(user)
        return redirect('/u/subscribe/success/')
    
    else:

        try:
            user_id = request.user.id
            product_type = request.data.get("product_type")
            try:
                months = int(request.data.get("months", 1))
            except (TypeError, ValueError):
                return Response({"error": "Invalid months value"}, status=status.HTTP_400_BAD_REQUEST)

            price_map = _price_catalog()
            price_id = None
            plan_level = None
            mode = "subscription"
            quantity = 1

            # Map product_type to price IDs (new and legacy)
            if product_type == "basic_monthly":
                price_id = settings.STRIPE_BASIC_MONTHLY_PRICE_ID
            elif product_type == "pro_monthly":
                price_id = settings.STRIPE_PRO_MONTHLY_PRICE_ID
                plan_level = "pro"
            elif product_type == "basic_yearly":
                price_id = settings.STRIPE_BASIC_YEARLY_PRICE_ID
                months = 12
            elif product_type == "pro_yearly":
                price_id = settings.STRIPE_PRO_YEARLY_PRICE_ID
                months = 12
                plan_level = "pro"
            elif product_type == "basic_one_off":
                price_id = settings.STRIPE_BASIC_ONE_OFF_PRICE_ID
                mode = "payment"
            elif product_type == "pro_one_off":
                price_id = settings.STRIPE_PRO_ONE_OFF_PRICE_ID
                mode = "payment"
                plan_level = "pro"
            elif product_type == "monthly":  # legacy
                price_id = settings.STRIPE_MONTHLY_PRICE_ID
            elif product_type == "yearly":  # legacy
                price_id = settings.STRIPE_YEARLY_PRICE_ID
                months = 12
            elif product_type == "custom":  # legacy custom quantity
                price_id = settings.STRIPE_CUSTOM_PRICE_ID
                quantity = months

            if price_id and price_id in price_map:
                plan_level = plan_level or price_map[price_id]["plan"]
                mode = price_map[price_id]["mode"]
            
            if not price_id:
                return Response({"error": "Invalid product type"}, status=status.HTTP_400_BAD_REQUEST)

            print("[checkout_session] user", user_id, "product_type", product_type, "price_id", price_id, "months", months, "plan", plan_level, "mode", mode, "quantity", quantity)

            # URLs required by Stripe
            success_url = request.build_absolute_uri('/u/subscribe/success/')
            cancel_url = request.build_absolute_uri('/u/subscribe/cancel/')

            session_params = {
                "success_url": success_url,
                "cancel_url": cancel_url,
                "line_items": [{"price": price_id, "quantity": quantity}],
                "mode": mode,
                "client_reference_id": str(user_id),
                "allow_promotion_codes": True,
                "payment_method_types": ["card"],
                "metadata": {
                    "user_id": str(user_id),
                    "product_type": product_type,
                    "months": str(months),
                    "plan_level": plan_level or "basic",
                },
            }

            # Persist plan and months on the subscription itself so invoice events can read them
            if mode == "subscription":
                session_params["subscription_data"] = {
                    "metadata": {
                        "months": str(months),
                        "plan_level": plan_level or "basic",
                    }
                }

            checkout_session = stripe.checkout.Session.create(**session_params)

            return redirect(checkout_session.url)

        except Exception as e:
            logger.exception("Unable to create stripe checkout session")
            return Response(
                {"error": f"Unable to create checkout session: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image

@login_required
def account_settings(request):
    user = request.user
    public_badges = badge.objects.filter(self_asign=True).order_by("badge_name")

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        reg_background = request.POST.get('reg_background') == 'on'
        fleet_icons = request.POST.get('fleet_icons') == 'on'
        pfp = request.FILES.get('pfp')
        banner = request.FILES.get('banner')
        selected_badge_ids = request.POST.getlist('badges')

        # Basic required field check
        if not username or not email:
            messages.error(request, "Username and email are required.")
            return redirect('account_settings')

        # Username validation
        if not re.match(r'^[\w.@+-]+$', username):
            messages.error(request, "Enter a valid username. This value may contain only letters, numbers, and @/./+/-/_ characters.")
            return redirect('account_settings')

        blocked_words = username_banned_words(username)
        if blocked_words:
            messages.error(request, username_banned_message(blocked_words))
            return redirect('account_settings')

        # Update user fields
        user.username = username
        user.email = email
        user.reg_background = reg_background
        user.fleet_icons = fleet_icons

        # Image compression function
        def compress_image(uploaded_file, max_size=1600, quality=80):
            try:
                with Image.open(uploaded_file) as img:
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
        private_badges = list(user.badges.exclude(self_asign=True))
        selected_public_badges = list(public_badges.filter(id__in=selected_badge_ids))
        user.badges.set(private_badges + selected_public_badges)
        sync_discord_entitlement_roles(user)
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
        'public_badges': public_badges,
        'selected_public_badge_ids': list(user.badges.filter(self_asign=True).values_list('id', flat=True)),
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

@login_required
def user_liveries(request, username):
    user = get_object_or_404(CustomUser, username=username)

    liveries = liverie.objects.filter(added_by=user).order_by('-pk')

    mbt_perms = []
    if request.user.is_authenticated and request.user.mbt_team:
        mbt_perms = list(request.user.mbt_team.permissions.values_list('name', flat=True))


    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Account Settings', 'url': reverse('account_settings')},
        {'name': 'My Liveries', 'url': reverse('user_liveries', kwargs={'username': user.username})},
    ]

    context = {
        'mbt_perms': mbt_perms,
        'username': username,
        'liveries': liveries,
        'breadcrumbs': breadcrumbs,
    }

    return render(request, 'user_liveries.html', context)

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

@login_required
def admin_reverify(request):
    if request.method == 'POST':
        token = request.POST.get('otp_token', '').strip()

        verified = False
        for device in devices_for_user(request.user):
            try:
                if device.verify_token(token):
                    verified = True
                    break
            except Exception:
                continue

        if verified:
            request.session['otp_admin_verified_at'] = timezone.now().timestamp()
            next_url = request.session.pop('otp_admin_next', '/admin/')
            return redirect(next_url)

        return render(request, 'two_factor/reverify.html', {'error': 'Invalid code. Please try again.'})

    return render(request, 'two_factor/reverify.html')
