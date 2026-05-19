from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.core.validators import validate_ipv46_address
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required

from fleet.views import operator
from .forms import AdForm, LiveryForm, VehicleForm
from .models import CustomModel
from tickets.models import Ticket
from main.models import CustomUser, badge, ad, featureToggle, BannedIps, MBTTeam
from main.models import Device, DeviceBan
from main import moderation
from fleet.models import liverie, fleet, vehicleType, MBTOperator
import requests
from django.template.loader import render_to_string
from django.db.models import Q
from django.shortcuts import get_object_or_404
from apply.models import Application
from messaging.models import Chat, ChatMember
from django.core.mail import send_mail
from django.conf import settings
import subprocess
import logging
from django.apps import apps
from django.utils import timezone
from datetime import timedelta
from main.models import CustomUser as User
from django.contrib import messages
from django.db.models.functions import TruncDate
from django.db.models import Count
from simple_history.utils import get_history_model_for_model
import json
from django.forms.models import model_to_dict
from django.urls import reverse, NoReverseMatch
from simple_history import utils
from simple_history.models import HistoricalRecords
from django.db.models import ManyToManyField, ForeignKey
from django.core.management import call_command
from django.http import FileResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.core.mail import EmailMessage
import zipfile
import tempfile
import os
import threading
import time
from django.core.cache import cache

# Simple in-memory resync task tracker. Keyed by thread_id.
RESYNC_TASKS = {}
RESYNC_LOCK = threading.Lock()
POSTS_PER_PAGE = 100

MAX_HISTORY_ROWS_PER_MODEL = 1000


def clear_feature_toggle_cache(feature_name=None):
    cache.delete('ad_feature_flags')
    cache.delete('feature_toggle_flags')
    if feature_name:
        cache.delete(f'feature_toggle_state:{feature_name}')

def has_permission(user, perm_name):
    if user.is_superuser:
        return True

    if not user.mbt_team:
        return False  # no team, no perms

    team_perms = user.mbt_team.permissions.values_list('name', flat=True)

    return perm_name in team_perms

@require_POST
def gdpr_export_download(request, user_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    user = get_object_or_404(User, pk=user_id)
    zip_path = run_gdpr_export(user)

    return FileResponse(
        open(zip_path, "rb"),
        as_attachment=True,
        filename=f"gdpr_{user.username}.zip",
    )

@require_POST
def gdpr_export_email(request, user_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    user = get_object_or_404(User, pk=user_id)
    zip_path = run_gdpr_export(user)

    body = f"""Hello {user.username},

Please find attached a copy of the personal data we currently hold about your MyBusTimes account.

This information is being provided in response to your FOIR / GDPR request and reflects the data associated with your account at the time this export was generated.

If you believe any of the information is inaccurate, incomplete, or if you have any questions regarding this export, please contact us at:

support@mybustimes.cc

Kind regards,
MyBusTimes Team

MyBusTimes
https://mybustimes.cc
This is an automated message sent from a no-reply address.
"""

    email = EmailMessage(
        subject="Your MyBusTimes FOIR / GDPR Data Export",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )

    email.attach_file(zip_path)
    email.send(fail_silently=False)

    return redirect("update-user", user.id)

def run_gdpr_export(user):
    tmp_dir = tempfile.mkdtemp(prefix="gdpr_")

    call_command(
        "gdpr_scrape",
        email=user.email,
        output_dir=tmp_dir,
        deep=True,
        include_files=True,
    )

    zip_path = os.path.join(tmp_dir, f"gdpr_user_{user.pk}.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(tmp_dir):
            for f in files:
                full_path = os.path.join(root, f)
                if full_path == zip_path:
                    continue
                arcname = os.path.relpath(full_path, tmp_dir)
                zipf.write(full_path, arcname)

    return zip_path

def permission_denied(request):
    return render(request, 'now-access.html')

def get_changes(entry):
    prev = entry.prev_record
    if not prev:
        print(f"[NO PREV] entry={entry}")
        return None
    try:
        diff = entry.diff_against(prev)
    except Exception as e:
        print("diff_against failed:", e)
        return None

    # Filter out IP address fields from changes
    changes = [(c.field, c.old, c.new) for c in diff.changes if 'ip' not in c.field.lower()]
    print(f"[CHANGES] {entry} -> {changes}")
    return changes


def _get_historical_model_choices():
    historical_models = []
    model_lookup = {}

    for model in apps.get_models():
        try:
            get_history_model_for_model(model)
        except Exception:
            continue

        label = f"{model._meta.app_label}.{model._meta.model_name}"
        historical_models.append((label, model._meta.verbose_name.title()))
        model_lookup[label] = model

    historical_models.sort(key=lambda item: item[1])
    return historical_models, model_lookup


def _apply_operator_filter(qs, model, operator):
    model_fields = {field.name: field for field in model._meta.get_fields()}

    fk_field = next(
        (
            name
            for name, field in model_fields.items()
            if isinstance(field, ForeignKey) and field.related_model == MBTOperator
        ),
        None,
    )
    if fk_field:
        return qs.filter(**{f"{fk_field}_id": operator.id})

    m2m_field = next(
        (
            name
            for name, field in model_fields.items()
            if isinstance(field, ManyToManyField) and field.related_model == MBTOperator
        ),
        None,
    )
    if m2m_field:
        live_ids = model.objects.filter(**{f"{m2m_field}__id": operator.id}).values_list("id", flat=True)
        return qs.filter(id__in=live_ids)

    return None


def user_activity_view(request):
    if not has_permission(request.user, 'user_view'):
        return redirect('/admin/permission-denied/')

    query_username = request.GET.get("username", "").strip()
    query_operator = request.GET.get("operator", "").strip()
    selected_model = request.GET.get("model", "").strip()
    selected_scope = request.GET.get("scope", "model").strip().lower() or "model"
    page_size = request.GET.get("page_size", "50").strip()

    try:
        page_size = max(10, min(int(page_size), 100))
    except (TypeError, ValueError):
        page_size = 50

    print("QUERY username:", query_username, "operator:", query_operator, "scope:", selected_scope)

    user = None
    operator = None

    operators = MBTOperator.objects.all().order_by("operator_name")
    historical_models, model_lookup = _get_historical_model_choices()
    selected_model_obj = model_lookup.get(selected_model)
    selected_model_label = selected_model_obj._meta.verbose_name.title() if selected_model_obj else ""

    if query_username:
        try:
            user = User.objects.get(username=query_username)
            print("[USER FOUND]", user)
        except User.DoesNotExist:
            print("[NO USER FOUND]")
            user = None

    if query_operator:
        try:
            operator = MBTOperator.objects.get(id=query_operator)
            print("[OPERATOR FOUND]", operator)
        except MBTOperator.DoesNotExist:
            print("[NO OPERATOR FOUND]")
            operator = None

    broad_scope_selected = selected_scope in {"user", "all"}
    has_filters = bool(selected_model_obj or user or operator or broad_scope_selected)
    page_obj = None
    page_results = []
    query_string = request.GET.copy()
    query_string.pop("page", None)
    query_string = query_string.urlencode()

    if has_filters:
        if selected_model_obj:
            hist_model = get_history_model_for_model(selected_model_obj)
            qs = hist_model.objects.all().select_related("history_user")

            if user:
                qs = qs.filter(history_user_id=user.id)

            if operator:
                filtered_qs = _apply_operator_filter(qs, selected_model_obj, operator)
                if filtered_qs is None:
                    qs = hist_model.objects.none()
                else:
                    qs = filtered_qs

            qs = qs.order_by("-history_date", "-history_id")
            paginator = Paginator(qs, page_size)
            page_obj = paginator.get_page(request.GET.get('page', 1))
            page_results = list(page_obj)

            for entry in page_results:
                entry.model_name = selected_model_obj._meta.verbose_name.title()
                obj_id = getattr(entry, selected_model_obj._meta.pk.attname, None)
                entry.changes = get_changes(entry)
                entry.change_count = len(entry.changes or [])
                entry.history_url = f"/api-admin/{selected_model_obj._meta.app_label}/{selected_model_obj._meta.model_name}/{obj_id}/history/" if obj_id else None
                entry.user_url = f"/api-admin/auth/user/{entry.history_user_id}/change/" if entry.history_user_id else None
                entry.object_label = str(entry)
        else:
            if user:
                selected_scope = "user"

            models_to_scan = []
            for model in apps.get_models():
                try:
                    get_history_model_for_model(model)
                except Exception:
                    continue
                models_to_scan.append(model)

            per_model_limit = 75 if selected_scope == "user" else 40

            print("[STEP] Collecting history entries")
            for model in models_to_scan:
                try:
                    hist_model = get_history_model_for_model(model)
                except Exception:
                    continue

                qs = hist_model.objects.all().select_related("history_user")

                if user:
                    qs = qs.filter(history_user_id=user.id)

                if operator:
                    filtered_qs = _apply_operator_filter(qs, model, operator)
                    if filtered_qs is None:
                        continue
                    qs = filtered_qs

                rows = list(qs.order_by('-history_date', '-history_id')[:per_model_limit])
                if rows:
                    page_results.extend(rows)

            page_results.sort(key=lambda x: x.history_date, reverse=True)
            paginator = Paginator(page_results, page_size)
            page_obj = paginator.get_page(request.GET.get('page', 1))

            for entry in page_obj:
                instance = getattr(entry, "instance", None)

                if instance:
                    entry.model_name = instance._meta.verbose_name.title()
                    obj_id = instance.pk
                    entry.history_url = f"/api-admin/{instance._meta.app_label}/{instance._meta.model_name}/{obj_id}/history/"
                    entry.object_label = str(entry)
                else:
                    entry.model_name = entry._meta.model._meta.verbose_name.title()
                    obj_id = getattr(entry, entry._meta.pk.name, None)
                    entry.history_url = None
                    entry.object_label = str(entry)

                entry.changes = get_changes(entry)
                entry.change_count = len(entry.changes or [])
                entry.user_url = f"/api-admin/auth/user/{entry.history_user_id}/change/" if entry.history_user_id else None

    status_label = "No filters selected"
    if selected_model_obj:
        status_label = f"Showing {selected_model_label} history"
    elif selected_scope == "user" and user:
        status_label = f"Showing activity for {user.username}"
    elif selected_scope == "all":
        status_label = "Showing cross-model activity"

    return render(request, "user_activity.html", {
        "selected_user": user,
        "selected_operator": operator,
        "selected_model": selected_model,
        "selected_model_obj": selected_model_obj,
        "selected_model_label": selected_model_label,
        "selected_scope": selected_scope,
        "page_size": page_size,
        "query_string": query_string,
        "status_label": status_label,
        "has_filters": has_filters,
        "operators": operators,
        "historical_models": historical_models,
        "page_obj": page_obj,
        "page_results": page_results,
    })

@login_required(login_url='/admin/login/')
def live_activity_view(request):
    if not has_permission(request.user, 'admin_dash'):
        return redirect('/admin/permission-denied/')

    cutoff = timezone.now() - timedelta(minutes=15)
    active_users_qs = User.objects.filter(last_active__gte=cutoff, is_active=True).order_by('-last_active')
    active_users = list(active_users_qs[:500])  # limit to avoid huge pages
    # attach masked_last_ip to each user for safe display in template
    for u in active_users:
        last_ip = getattr(u, 'last_ip', None)
        if last_ip:
            try:
                parts = last_ip.split('.')
                if len(parts) == 4:
                    masked = f"{parts[0]}.{parts[1]}.xxx.xxx"
                else:
                    masked = last_ip
            except Exception:
                masked = last_ip
        else:
            masked = None
        setattr(u, 'masked_last_ip', masked)
    active_count = active_users_qs.count()

    recent_signups = User.objects.filter(date_joined__gte=timezone.now() - timedelta(hours=24)).order_by('-date_joined')[:100]

    # Active chats with member counts
    chat_member_counts = (
        Chat.objects
        .annotate(member_count=Count('chatmember'))
        .filter(member_count__gt=0)
        .order_by('-member_count')[:100]
    )

    return render(request, 'live_activity.html', {
        'active_users': active_users,
        'active_count': active_count,
        'recent_signups': recent_signups,
        'active_chats': chat_member_counts,
        'cutoff': cutoff,
    })

@login_required(login_url='/admin/login/')
def live_activity_api(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'permission_denied'}, status=403)

    cutoff = timezone.now() - timedelta(minutes=15)
    # Build base queryset and prefetch related fields to avoid per-user queries
    base_qs = (
        User.objects.filter(last_active__gte=cutoff, is_active=True)
        .select_related('mbt_team')
        .prefetch_related('badges')
        .order_by('-last_active')
    )

    # slice then evaluate once
    users_list = list(base_qs[:500])
    active_count = base_qs.count()

    recent_signups_qs = User.objects.filter(date_joined__gte=timezone.now() - timedelta(hours=24)).order_by('-date_joined')[:100]
    open_tickets_qs = Ticket.objects.filter(status='open').order_by('-created_at')[:100]

    # Batch fetch banned IPs for the set of last_ip values to avoid N queries
    last_ips = {u.last_ip for u in users_list if getattr(u, 'last_ip', None)}
    banned_qs = BannedIps.objects.filter(ip_address__in=last_ips).select_related('related_user') if last_ips else []
    ip_to_bans = {}
    for b in banned_qs:
        ip_to_bans.setdefault(b.ip_address, []).append(b)

    active_users = []
    for u in users_list:
        last_ip = getattr(u, 'last_ip', None)
        bans_for_ip = ip_to_bans.get(last_ip, []) if last_ip else []
        ip_bans_list = [
            {
                'ip_address': b.ip_address,
                'reason': getattr(b, 'reason', None),
                'related_user_id': getattr(b, 'related_user_id', None),
                'banned_at': getattr(b, 'banned_at', None).isoformat() if getattr(b, 'banned_at', None) else None,
            }
            for b in bans_for_ip
        ]

        ip_bans_exist = bool(bans_for_ip)
        ip_bans_for_user = any((getattr(b, 'related_user_id', None) == u.id) for b in bans_for_ip)
        ip_flag = ip_bans_exist and (not getattr(u, 'banned', False) or not ip_bans_for_user)

        # compute masked IP once
        if last_ip:
            try:
                parts = last_ip.split('.')
                masked_ip = f"{parts[0]}.{parts[1]}.xxx.xxx" if len(parts) == 4 else last_ip
            except Exception:
                masked_ip = last_ip
        else:
            masked_ip = None

        # badges are prefetched
        badges = [getattr(b, 'badge_name', None) for b in u.badges.all()] if hasattr(u, 'badges') else []

        active_users.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'last_active': u.last_active.isoformat() if u.last_active else None,
            'last_ip': last_ip,
            'masked_last_ip': masked_ip,
            'is_staff': u.is_staff,
            'is_active': u.is_active,
            'is_superuser': u.is_superuser,
            'banned': getattr(u, 'banned', False),
            'badges': badges,
            'team': (u.mbt_team.name if getattr(u, 'mbt_team', None) else None),
            'ip_flag': ip_flag,
            'ip_bans': ip_bans_list,
        })

    recent_signups = [
        {'id': s.id, 'username': s.username, 'date_joined': s.date_joined.isoformat()}
        for s in recent_signups_qs
    ]

    open_tickets = [
        {
            'id': t.id,
            'title': getattr(t, 'title', f"Ticket #{t.id}"),
            'user': (t.user.username if t.user else t.sender_email) if hasattr(t, 'user') else None,
            'created_at': t.created_at.isoformat() if t.created_at else None,
            'priority': getattr(t, 'priority', None),
        }
        for t in open_tickets_qs
    ]

    return JsonResponse({
        'cutoff': cutoff.isoformat(),
        'active_count': active_count,
        'active_users': active_users,
        'recent_signups': recent_signups,
        'open_tickets': open_tickets,
    })


@login_required(login_url='/admin/login/')
def user_search_api(request):
    if not has_permission(request.user, 'user_view'):
        return redirect('/admin/permission-denied/')

    q = request.GET.get('q', '').strip()
    results = []
    if q:
        # allow searching by username, email, or IP address
        qs = User.objects.filter(
            Q(username__icontains=q) | Q(email__icontains=q) | Q(last_ip__icontains=q)
        ).order_by('username')[:200]
        for u in qs:
            masked_ip = None
            last_ip = getattr(u, 'last_ip', None)
            if last_ip:
                # mask IPv4/IPv6 for safe display
                if ':' in last_ip:
                    parts = last_ip.split(':')
                    masked_ip = ':'.join(parts[:2]) + ':…'
                else:
                    parts = last_ip.split('.')
                    if len(parts) == 4:
                        masked_ip = '.'.join(parts[:3]) + '.x'
                    else:
                        masked_ip = last_ip
            results.append({
                'id': u.id,
                'username': u.username,
                'email': getattr(u, 'email', None),
                'last_active': u.last_active.isoformat() if getattr(u, 'last_active', None) else None,
                'last_ip': last_ip,
                'masked_last_ip': masked_ip,
                'is_staff': bool(getattr(u, 'is_staff', False)),
                'banned': bool(getattr(u, 'banned', False)),
                'ip_flag': False,
                'is_active': bool(getattr(u, 'is_active', True)),
            })

    return JsonResponse({'results': results})


from datetime import datetime
from main.models import BannedIps, StripeSubscription 

@login_required(login_url='/admin/login/')
def user_actions_view(request, user_id):
    if not has_permission(request.user, 'user_view'):
        return redirect('/admin/permission-denied/')

    target = get_object_or_404(User, id=user_id)

    # Data for UI
    badges = target.badges.all()
    all_badges = badge.objects.all()
    tickets = Ticket.objects.filter(user=target).order_by('-created_at')
    stripe_sub = None
    try:
        stripe_sub = StripeSubscription.objects.filter(user=target).last()
    except Exception:
        stripe_sub = None
    # Banned IPs related to this user (prepare masked IPs for display)
    raw_banned_ips = BannedIps.objects.filter(related_user=target).order_by('-banned_at')
    banned_ips = []
    for b in raw_banned_ips:
        ip_addr = getattr(b, 'ip_address', None)
        masked = None
        if ip_addr:
            try:
                parts = ip_addr.split('.')
                if len(parts) == 4:
                    masked = f"{parts[0]}.{parts[1]}.xxx.xxx"
                else:
                    masked = ip_addr
            except Exception:
                masked = ip_addr
        banned_ips.append({
            'id': getattr(b, 'id', None),
            'ip_address': masked,  # Only expose masked version
            'masked_ip': masked,
            'reason': getattr(b, 'reason', None),
            'banned_at': getattr(b, 'banned_at', None),
            'related_user_id': getattr(b, 'related_user_id', None),
        })

    # Try to fetch up to 20 recent forum messages from common model names.
    # Account for forum apps that store author as a username string (Post) or a FK (user).
    forum_messages = []
    for candidate in ("Post", "ForumPost", "Comment", "Message", "ThreadMessage"):
        try:
            Model = apps.get_model("forum", candidate)
        except LookupError:
            continue

        # prefer a user FK
        field_names = {f.name for f in Model._meta.get_fields()}
        qs = None
        if 'user' in field_names:
            qs = Model.objects.filter(user=target)
        elif 'author' in field_names:
            # many forum Post models store author as username string
            qs = Model.objects.filter(author=target.username)
        elif 'created_by' in field_names:
            # fallback: sometimes created_by stores username
            qs = Model.objects.filter(created_by=target.username)
        else:
            continue

        try:
            raw_msgs = list(qs.order_by("-created_at")[:20])
        except Exception:
            continue

        # Map model instances -> plain dicts so template won't crash on missing attributes
        def _msg_dict(m):
            # body candidates
            body = getattr(m, "content", None) or getattr(m, "body", None) or getattr(m, "text", None) or ""
            title = getattr(m, "title", None) or getattr(m, "subject", None) or None
            thread = getattr(m, "thread", None)
            thread_title = getattr(thread, "title", None) if thread else None
            # fallback title if still empty
            if not title:
                title = (body[:80] + "…") if body else "Message"

            # Provide both 'title' and 'subject' keys and a 'thread' mapping so templates
            # that reference m.subject or m.thread.title won't crash.
            thread_obj = {"title": thread_title} if thread_title else None

            return {
                "title": title,
                "subject": title,
                "created_at": getattr(m, "created_at", None),
                "thread_title": thread_title,
                "thread": thread_obj,
                "body": body,
                "excerpt": (body[:200] + "…") if body and len(body) > 200 else body,
            }

        forum_messages = [_msg_dict(m) for m in raw_msgs]
        break

    if request.method == "POST":
        action = request.POST.get("action")
        # toggle active/inactive
        if action == "toggle_active":
            target.is_active = not target.is_active
            target.save()
            return redirect(f"/admin/user/{user_id}/actions/")

        # Normal account ban (sets user.banned and banned_date/reason)
        if action == "ban_user":
            # Prevent admins from banning their own account
            if request.user.id == target.id:
                messages.error(request, "You cannot ban your own account.")
                return redirect(f"/admin/user/{user_id}/actions/")
            reason = request.POST.get("ban_reason", "").strip() or None
            until = request.POST.get("ban_until")
            try:
                if until:
                    until_dt = timezone.make_aware(datetime.fromisoformat(until))
                else:
                    until_dt = None
            except Exception:
                until_dt = None
            target.banned = True
            target.banned_reason = reason
            target.banned_date = until_dt
            target.save()
            moderation.invalidate_user_ban_cache(target)
            return redirect(f"/admin/user/{user_id}/actions/")

        # IP ban: add last_ip to BannedIps and set user as banned with far future date
        if action == "ip_ban":
            # Prevent admins from IP-banning their own account
            if request.user.id == target.id:
                messages.error(request, "You cannot IP-ban your own account.")
                return redirect(f"/admin/user/{user_id}/actions/")
            reason = request.POST.get("ban_reason", "").strip() or None
            last_ip = getattr(target, "last_ip", None)
            if last_ip:
                try:
                    BannedIps.objects.update_or_create(
                        ip_address=last_ip,
                        defaults={
                            "reason": reason,
                            "related_user": target,
                        }
                    )
                    moderation.invalidate_ip_ban_cache(last_ip)
                except Exception:
                    # ignore duplicate / validation errors
                    pass
            # mark user banned until 9999-12-31
            far_future = timezone.make_aware(datetime(9999, 12, 31, 0, 0, 0))
            target.banned = True
            target.banned_reason = reason
            target.banned_date = far_future
            target.save()
            moderation.invalidate_user_ban_cache(target)
            return redirect(f"/admin/user/{user_id}/actions/")
        # Device ban: create a DeviceBan record for given fingerprint
        if action == "ban_device":
            if not has_permission(request.user, 'user_ban'):
                return redirect('/admin/permission-denied/')
            fingerprint = request.POST.get('fingerprint')
            reason = request.POST.get('ban_reason', '').strip() or None
            if fingerprint:
                try:
                    DeviceBan.objects.update_or_create(
                        fingerprint=fingerprint,
                        defaults={
                            'reason': reason,
                            'related_user': target,
                            'active': True,
                        }
                    )
                    moderation.invalidate_device_ban_cache(fingerprint)
                except Exception:
                    # ignore unexpected errors
                    pass
            return redirect(f"/admin/user/{user_id}/actions/")
        # Device ban every known device linked to this user
        if action == "ban_user_devices":
            if not has_permission(request.user, 'user_ban'):
                return redirect('/admin/permission-denied/')
            reason = request.POST.get('ban_reason', '').strip() or None
            moderation.create_device_bans_for_user(target, reason=reason)
            return redirect(f"/admin/user/{user_id}/actions/")
        # Unban device: mark DeviceBan.active=False for given fingerprint
        if action == "unban_device":
            if not has_permission(request.user, 'user_ban'):
                return redirect('/admin/permission-denied/')
            fingerprint = request.POST.get('fingerprint')
            if fingerprint:
                try:
                    DeviceBan.objects.filter(fingerprint=fingerprint, active=True).update(active=False)
                    moderation.invalidate_device_ban_cache(fingerprint)
                except Exception:
                    pass
            return redirect(f"/admin/user/{user_id}/actions/")
        # Unban user: clear banned flag and ban metadata
        if action == "unban_user":
            if not has_permission(request.user, 'user_ban'):
                return redirect('/admin/permission-denied/')
            try:
                target.banned = False
                target.banned_reason = None
                target.banned_date = None
                target.save()
                moderation.invalidate_user_ban_cache(target)
            except Exception:
                pass
            return redirect(f"/admin/user/{user_id}/actions/")

        # Unban a single IP ban entry (by ban id)
        if action == "ip_unban":
            if not has_permission(request.user, 'user_ban'):
                return redirect('/admin/permission-denied/')
            ban_id = request.POST.get('ban_id')
            try:
                if ban_id:
                    ip = BannedIps.objects.filter(id=ban_id).values_list('ip_address', flat=True).first()
                    BannedIps.objects.filter(id=ban_id).delete()
                    moderation.invalidate_ip_ban_cache(ip)
            except Exception:
                pass
            return redirect(f"/admin/user/{user_id}/actions/")

        # Unban all IPs related to this user
        if action == "ip_unban_all":
            if not has_permission(request.user, 'user_ban'):
                return redirect('/admin/permission-denied/')
            try:
                ips = list(BannedIps.objects.filter(related_user=target).values_list('ip_address', flat=True))
                BannedIps.objects.filter(related_user=target).delete()
                moderation.invalidate_ip_ban_cache(*ips)
            except Exception:
                pass
            return redirect(f"/admin/user/{user_id}/actions/")
        # Save admin notes
        if action == "save_admin_notes":
            if not has_permission(request.user, 'user_edit'):
                return redirect('/admin/permission-denied/')
            try:
                notes = request.POST.get('admin_notes', '').strip() or None
                target.admin_notes = notes
                target.save()
                messages.success(request, "Admin notes updated.")
            except Exception:
                messages.error(request, "Failed to update admin notes.")
            return redirect(f"/admin/user/{user_id}/actions/")

        # Add badge to user
        if action == "add_badge":
            if not has_permission(request.user, 'user_edit'):
                return redirect('/admin/permission-denied/')
            b_id = request.POST.get('badge_id')
            try:
                if b_id:
                    b = badge.objects.filter(id=b_id).first()
                    if b:
                        target.badges.add(b)
                        messages.success(request, f"Badge '{b.badge_name}' added.")
            except Exception:
                messages.error(request, "Failed to add badge.")
            return redirect(f"/admin/user/{user_id}/actions/")

        # Remove badge from user
        if action == "remove_badge":
            if not has_permission(request.user, 'user_edit'):
                return redirect('/admin/permission-denied/')
            b_id = request.POST.get('badge_id')
            try:
                if b_id:
                    b = badge.objects.filter(id=b_id).first()
                    if b:
                        target.badges.remove(b)
                        messages.success(request, f"Badge '{b.badge_name}' removed.")
            except Exception:
                messages.error(request, "Failed to remove badge.")
            return redirect(f"/admin/user/{user_id}/actions/")
        
    print("badges:", badges)
    print("tickets:", tickets)
    print("stripe_sub:", stripe_sub)
    print("forum_messages:", forum_messages)

    admin_change_url = f"/api-admin/{target._meta.app_label}/{target._meta.model_name}/{target.pk}/change/"
    # Prepare a masked IP for display (avoid template-side method calls)
    last_ip = getattr(target, 'last_ip', None)
    if last_ip:
        try:
            parts = last_ip.split('.')
            if len(parts) == 4:
                masked_last_ip = f"{parts[0]}.{parts[1]}.xxx.xxx"
            else:
                masked_last_ip = last_ip
        except Exception:
            masked_last_ip = last_ip
    else:
        masked_last_ip = None
    # Devices associated with this user
    try:
        devices = Device.objects.filter(usages__user=target).distinct().order_by('-last_seen')
    except Exception:
        devices = Device.objects.filter(last_user=target).order_by('-last_seen')[:50]
    # Attach ban info to each device instance for template
    try:
        devices = list(devices)
        active_bans = {
            b.fingerprint: b
            for b in DeviceBan.objects.filter(
                fingerprint__in=[d.fingerprint for d in devices],
                active=True,
            )
        }
        for d in devices:
            db = active_bans.get(d.fingerprint)
            d.is_banned = bool(db)
            d.ban_reason = db.reason if db else None
    except Exception:
        pass
    return render(request, "user_actions.html", {
        "target": target,
        "admin_change_url": admin_change_url,
        "badges": badges,
        "all_badges": all_badges,
        "tickets": tickets,
        "stripe_sub": stripe_sub,
        "forum_messages": forum_messages,
        "banned_ips": banned_ips,
        "masked_last_ip": masked_last_ip,
        "devices": devices,
    })


def ban_user(request, user_id):
    if not has_permission(request.user, 'user_ban'):
        return redirect('/admin/permission-denied/')
    
    user = CustomUser.objects.get(id=user_id)

    # Prevent banning your own account via this endpoint
    if request.user.id == user.id:
        messages.error(request, "You cannot ban your own account.")
        return redirect('/admin/users-management/')

    if user.banned == True:
        user.banned = False
        user.save()
        moderation.invalidate_user_ban_cache(user)
        return redirect("/admin/users-management/")

    user.banned = True
    user.save()
    moderation.invalidate_user_ban_cache(user)
    return render(request, 'ban.html', {'user': user})


logger = logging.getLogger(__name__)

@login_required(login_url="/admin/login/")
def restart_service(request):
    if not has_permission(request.user, "restart_web"):
        return redirect("/admin/permission-denied/")

    try:
        # Call systemctl via sudo (allowed in /etc/sudoers.d/mybustimes)
        subprocess.run(["/usr/bin/sudo", "/usr/bin/systemctl", "restart", "mybustimes"], check=True)
        messages.success(request, "✅ Service restarted successfully")
    except subprocess.CalledProcessError as e:
        logger.error("Service restart failed: %s", e)
        messages.error(request, "❌ Failed to restart service")
    except FileNotFoundError as e:
        logger.error("systemctl not found: %s", e)
        messages.error(request, "❌ systemctl command not found on server")

    return redirect("/admin/")

def submit_ban_user(request, user_id):
    if not has_permission(request.user, 'user_ban'):
        return redirect('/admin/permission-denied/')
    
    user = CustomUser.objects.get(id=user_id)
    # Prevent banning your own account
    if request.user.id == user.id:
        messages.error(request, "You cannot ban your own account.")
        return redirect('/admin/users-management/')
    user.banned = True
    user.save()
    return redirect('/admin/users-management/')

def submit_ip_ban_user(request, user_id):
    if not has_permission(request.user, 'user_ban'):
        return redirect('/admin/permission-denied/')
    
    user = CustomUser.objects.get(id=user_id)
    # Prevent IP-banning your own account
    if request.user.id == user.id:
        messages.error(request, "You cannot IP-ban your own account.")
        return redirect('/admin/users-management/')
    user.banned = True
    user.save()

    ip = user.last_ip

    # Check if IP is a Docker/local address (172.x.x.x, 10.x.x.x, 192.168.x.x)
    if ip and (ip.startswith('172.') or ip.startswith('10.') or ip.startswith('192.168.')):
        ip = None
        messages.error(request, "IP ban skipped due to local/Docker IP address.")

    try:
        validate_ipv46_address(ip)
    except (ValidationError, TypeError):  # TypeError covers ip=None
        ip = None

    if ip:
        BannedIps.objects.create(
            ip_address=ip,
            reason=request.POST.get('reason', 'No reason provided'),
            related_user=user
        )
    else:
        messages.error(request, "User banned but no valid IP found to ban.")

    return redirect('/admin/users-management/')

def custom_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('/admin/')  # Redirect to the admin page
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def get_user_joins_per_day(period="all"):
    today = timezone.now().date()
    start_date = None

    if period == "this_week":
        start_date = today - timedelta(days=today.weekday())  # Monday
    elif period == "last_week":
        start_date = today - timedelta(days=today.weekday() + 7)
        end_date = start_date + timedelta(days=6)
    elif period == "this_month":
        start_date = today.replace(day=1)
    elif period == "last_month":
        first_day_this_month = today.replace(day=1)
        start_date = (first_day_this_month - timedelta(days=1)).replace(day=1)
        end_date = first_day_this_month - timedelta(days=1)
    elif period == "this_year":
        start_date = today.replace(month=1, day=1)
    elif period == "last_year":
        start_date = today.replace(year=today.year - 1, month=1, day=1)
        end_date = today.replace(year=today.year - 1, month=12, day=31)

    qs = User.objects.annotate(day=TruncDate("date_joined"))

    if start_date:
        if "end_date" in locals():
            qs = qs.filter(date_joined__date__gte=start_date, date_joined__date__lte=end_date)
        else:
            qs = qs.filter(date_joined__date__gte=start_date)

    data = (
        qs.values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    return [{"day": entry["day"].isoformat(), "count": entry["count"]} for entry in data]

@login_required(login_url='/admin/login/')
def dashboard_view(request):
    if not has_permission(request.user, 'admin_dash'):
        return redirect('/admin/permission-denied/')

    # Read filter from query param (?period=this_week)
    period = request.GET.get('period', 'this_week')
    user_joins_per_day = get_user_joins_per_day(period)

    user_count = CustomUser.objects.count()
    cutoff = timezone.now() - timedelta(minutes=15)
    active_user_count = User.objects.filter(last_active__gte=cutoff, is_active=True).count()

    return render(request, 'dashboard.html', {
        'user_count': user_count,
        'active_user_count': active_user_count,
        'user_joins_per_day': json.dumps(user_joins_per_day),
        'current_period': period,
    })
@login_required(login_url='/admin/login/')
def ads_view(request):
    if not has_permission(request.user, 'ad_view'):
        return redirect('/admin/permission-denied/')
    
    feature_toggles = featureToggle.objects.filter(name__in=['mbt_ads', 'google_ads', 'ads'])

    ads = ad.objects.all()
    return render(request, 'ads.html', {'ads': ads, 'feature_toggles': feature_toggles})

@login_required
def admin_site_links(request):
    if not has_permission(request.user, 'admin_dash'):
        return redirect('/admin/permission-denied/')
    
    return render(request, 'admin_site_links.html')


@login_required(login_url='/admin/login/')
def forum_management_view(request):
    if not has_permission(request.user, 'forum_manage'):
        return redirect('/admin/permission-denied/')

    # List forums and threads with discord mappings
    from forum.models import Forum, Thread

    forums = Forum.objects.all().order_by('order', 'name')
    threads = Thread.objects.select_related('forum').order_by('-created_at')[:500]

    return render(request, 'forum_management.html', {
        'forums': forums,
        'threads': threads,
    })


@login_required(login_url='/admin/login/')
def forum_mod_threads(request):
    if not has_permission(request.user, 'forum_manage'):
        return redirect('/admin/permission-denied/')

    from forum.models import Thread

    search = request.GET.get('search', '').strip()
    page = int(request.GET.get('page', 1))

    qs = Thread.objects.select_related('forum').order_by('-created_at')
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(created_by__icontains=search) | Q(discord_channel_id__icontains=search))

    paginator = Paginator(qs, 50)
    threads = paginator.get_page(page)

    return render(request, 'forum_mod_threads.html', {
        'threads': threads,
        'search': search,
    })


@login_required(login_url='/admin/login/')
def forum_mod_thread_detail(request, thread_id):
    if not has_permission(request.user, 'forum_manage'):
        return redirect('/admin/permission-denied/')

    from forum.models import Thread, Post

    thread = get_object_or_404(Thread, pk=thread_id)

    # search posts by author
    author = request.GET.get('author', '').strip()
    if author:
        posts_qs = thread.posts.filter(author__icontains=author).order_by('created_at')
    else:
        posts_qs = thread.posts.order_by('created_at')

    paginator = Paginator(posts_qs, 200)
    page = request.GET.get('page')
    posts = paginator.get_page(page)

    return render(request, 'forum_mod_thread.html', {
        'thread': thread,
        'posts': posts,
        'author_search': author,
    })


@login_required
@require_POST
def mod_delete_thread(request, thread_id):
    if not has_permission(request.user, 'forum_manage'):
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)

    from forum.models import Thread
    th = get_object_or_404(Thread, pk=thread_id)
    th.delete()
    messages.success(request, 'Thread deleted')
    return redirect('/admin/forum/moderation/')


@login_required
@require_POST
def mod_recreate_thread(request, thread_id):
    if not has_permission(request.user, 'forum_manage'):
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)

    from forum.models import Thread, Post
    try:
        th = Thread.objects.get(pk=thread_id)
    except Thread.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Thread not found'}, status=404)
    # Read optional pages parameter to limit how many pages to sync after recreate
    pages = None
    try:
        pages = int(request.POST.get('pages') or request.GET.get('pages') or 0)
        if pages <= 0:
            pages = None
    except Exception:
        pages = None

    # Call the discord bot to create a new thread/channel
    try:
        payload = {
            'title': th.title,
            'content': th.posts.order_by('created_at').first().content if th.posts.exists() else ''
        }
        if not settings.DISABLE_JESS:
            resp = requests.post(f"{settings.DISCORD_BOT_API_URL}/create-thread", json=payload, timeout=30)
            resp.raise_for_status()
            new_channel = resp.json().get('thread_id') or resp.json().get('channel_id')
            if new_channel:
                th.discord_channel_id = str(new_channel)
                th.save(update_fields=['discord_channel_id'])
                messages.success(request, 'Recreated thread on Discord')

                # start resync in background for the newly created channel (same behavior as resync)
                t = threading.Thread(target=_resync_thread_background, args=(th.id, 1, pages), daemon=True)
                t.start()
            else:
                messages.error(request, 'Discord API returned no channel id')
        else:
            messages.error(request, 'Discord API is disabled (DISABLE_JESS=True).')
    except Exception as e:
        messages.error(request, f'Failed to recreate thread: {e}')

    return redirect(f'/admin/forum/moderation/thread/{th.id}/')


def _recreate_page_background(task_id, thread_ids, pages_limit=None, sleep_seconds=1):
    from forum.models import Thread
    total = len(thread_ids)
    with RESYNC_LOCK:
        RESYNC_TASKS[task_id] = {'status': 'running', 'total': total, 'processed': 0}

    for tid in thread_ids:
        # check for stop
        with RESYNC_LOCK:
            task = RESYNC_TASKS.get(task_id)
        if not task or task.get('status') == 'stopped':
            break

        try:
            th = Thread.objects.get(pk=tid)
        except Thread.DoesNotExist:
            with RESYNC_LOCK:
                RESYNC_TASKS[task_id]['processed'] += 1
            continue

        try:
            payload = {
                'title': th.title,
                'content': th.posts.order_by('created_at').first().content if th.posts.exists() else ''
            }
            if not settings.DISABLE_JESS:
                resp = requests.post(f"{settings.DISCORD_BOT_API_URL}/create-thread", json=payload, timeout=30)
                resp.raise_for_status()
                new_channel = resp.json().get('thread_id') or resp.json().get('channel_id')
                if new_channel:
                    th.discord_channel_id = str(new_channel)
                    th.save(update_fields=['discord_channel_id'])
                    # start per-thread resync for this thread
                    t = threading.Thread(target=_resync_thread_background, args=(th.id, sleep_seconds, pages_limit), daemon=True)
                    t.start()
        except Exception:
            pass

        # mark processed for page-level task
        with RESYNC_LOCK:
            if task_id in RESYNC_TASKS:
                RESYNC_TASKS[task_id]['processed'] += 1

        time.sleep(sleep_seconds)

    # mark done
    with RESYNC_LOCK:
        if task_id in RESYNC_TASKS:
            RESYNC_TASKS[task_id]['status'] = 'done'


@login_required
@require_POST
def mod_recreate_page_api(request):
    if not has_permission(request.user, 'forum_manage'):
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)

    from forum.models import Thread

    page = int(request.POST.get('page') or request.GET.get('page') or 1)
    search = (request.POST.get('search') or request.GET.get('search') or '').strip()

    qs = Thread.objects.select_related('forum').order_by('-created_at')
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(created_by__icontains=search) | Q(discord_channel_id__icontains=search))

    paginator = Paginator(qs, 50)
    threads_page = paginator.get_page(page)
    thread_ids = [t.id for t in threads_page.object_list]

    # optional pages param for per-thread resync
    pages_limit = None
    try:
        pages_limit = int(request.POST.get('pages') or request.GET.get('pages') or 0)
        if pages_limit <= 0:
            pages_limit = None
    except Exception:
        pages_limit = None

    # create a unique task id
    task_id = f"page-{int(time.time()*1000)}"

    # start background worker
    t = threading.Thread(target=_recreate_page_background, args=(task_id, thread_ids, pages_limit), daemon=True)
    t.start()

    return JsonResponse({'status': 'started', 'task_id': task_id})


@login_required
def recreate_page_status(request, task_id):
    if not has_permission(request.user, 'forum_manage'):
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)

    with RESYNC_LOCK:
        task = RESYNC_TASKS.get(task_id)
    if not task:
        return JsonResponse({'status': 'not_found'})
    return JsonResponse({'status': 'ok', 'task': task})


@login_required
@require_POST
def mod_recreate_page(request):
    if not has_permission(request.user, 'forum_manage'):
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)

    from forum.models import Thread

    # read page and search from the form
    page = int(request.POST.get('page') or request.GET.get('page') or 1)
    search = (request.POST.get('search') or request.GET.get('search') or '').strip()

    qs = Thread.objects.select_related('forum').order_by('-created_at')
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(created_by__icontains=search) | Q(discord_channel_id__icontains=search))

    paginator = Paginator(qs, 50)
    threads_page = paginator.get_page(page)

    # optional pages param to pass to the resync worker for each recreated thread
    pages_limit = None
    try:
        pages_limit = int(request.POST.get('pages') or request.GET.get('pages') or 0)
        if pages_limit <= 0:
            pages_limit = None
    except Exception:
        pages_limit = None

    created = 0
    for th in threads_page.object_list:
        try:
            payload = {
                'title': th.title,
                'content': th.posts.order_by('created_at').first().content if th.posts.exists() else ''
            }
            if not settings.DISABLE_JESS:
                resp = requests.post(f"{settings.DISCORD_BOT_API_URL}/create-thread", json=payload, timeout=30)
                resp.raise_for_status()
                new_channel = resp.json().get('thread_id') or resp.json().get('channel_id')
                if new_channel:
                    th.discord_channel_id = str(new_channel)
                    th.save(update_fields=['discord_channel_id'])
                    # start resync in background for the newly created channel
                    t = threading.Thread(target=_resync_thread_background, args=(th.id, 1, pages_limit), daemon=True)
                    t.start()
                    created += 1
        except Exception:
            # ignore per-thread failures and continue
            continue

    messages.success(request, f'Recreated {created} threads on this page (attempted {len(threads_page.object_list)}).')
    return redirect(f'/admin/forum/moderation/?page={page}&search={search}')


@login_required
@require_POST
def mod_delete_post(request, post_id):
    if not has_permission(request.user, 'forum_manage'):
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)

    from forum.models import Post
    post = get_object_or_404(Post, pk=post_id)
    thread_id = post.thread_id
    post.delete()
    messages.success(request, 'Post deleted')
    return redirect(f'/admin/forum/moderation/thread/{thread_id}/')


def _resync_thread_background(thread_id, sleep_seconds=1, pages=None):
    from forum.models import Thread, Post
    from django.conf import settings
    try:
        th = Thread.objects.get(pk=thread_id)
    except Thread.DoesNotExist:
        return
    if not th.discord_channel_id:
        with RESYNC_LOCK:
            RESYNC_TASKS.pop(thread_id, None)
        return

    # Determine posts to process. If pages specified, take newest `pages` pages worth
    if pages:
        try:
            pages = int(pages)
        except Exception:
            pages = None

    if pages and pages > 0:
        # get newest posts first, up to pages * POSTS_PER_PAGE
        subset = list(th.posts.order_by('-created_at').all()[: pages * POSTS_PER_PAGE])
        # we want to send in chronological order within that subset
        posts = list(reversed(subset))
    else:
        posts = list(th.posts.order_by('created_at').all())

    total = len(posts)
    with RESYNC_LOCK:
        RESYNC_TASKS[thread_id] = {
            'status': 'running',
            'total': total,
            'processed': 0,
        }
    for post in posts:
        # check for control signals
        with RESYNC_LOCK:
            task = RESYNC_TASKS.get(thread_id)
        if not task:
            # stopped externally
            break

        # pause handling
        while True:
            with RESYNC_LOCK:
                task = RESYNC_TASKS.get(thread_id)
                if not task:
                    break
                status = task.get('status')
            if not task or status == 'stopped':
                break
            if status == 'paused':
                time.sleep(1)
                continue
            break

        with RESYNC_LOCK:
            task = RESYNC_TASKS.get(thread_id)
            if not task or task.get('status') == 'stopped':
                break

        try:
            data = {
                'channel_id': str(th.discord_channel_id),
                'send_by': post.author,
                'message': post.content,
            }

            files = None
            if getattr(post, 'image', None):
                try:
                    img_path = post.image.path
                    if os.path.exists(img_path):
                        files = {'image': (os.path.basename(img_path), open(img_path, 'rb'))}
                except Exception:
                    files = None

            # Send via Discord bot API
            try:
                if not settings.DISABLE_JESS:
                    requests.post(f"{settings.DISCORD_BOT_API_URL}/send-message", data=data, files=files, timeout=30)
            except Exception:
                pass

            # avoid rate limits and be gentle
            time.sleep(sleep_seconds)

            # mark processed
            with RESYNC_LOCK:
                if thread_id in RESYNC_TASKS:
                    RESYNC_TASKS[thread_id]['processed'] += 1
        finally:
            try:
                if files and isinstance(files.get('image')[1], object):
                    files.get('image')[1].close()
            except Exception:
                pass


@login_required
@require_POST
def resync_thread(request, thread_id):
    if not has_permission(request.user, 'forum_manage'):
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    # Read optional pages parameter from POST (AJAX) to limit how many pages to sync
    pages = None
    try:
        pages = int(request.POST.get('pages') or request.GET.get('pages') or 0)
        if pages <= 0:
            pages = None
    except Exception:
        pages = None

    # Start background thread to slowly resend posts
    t = threading.Thread(target=_resync_thread_background, args=(thread_id, 1, pages), daemon=True)
    t.start()

    messages.success(request, 'Resync started in background. This may take some time.')
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'started', 'thread_id': thread_id})

    return redirect('/admin/forum-management/')


@login_required
def resync_status(request, thread_id):
    if not has_permission(request.user, 'forum_manage'):
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)

    with RESYNC_LOCK:
        task = RESYNC_TASKS.get(thread_id)
    if not task:
        return JsonResponse({'status': 'not_found'})

    return JsonResponse({'status': 'ok', 'task': task})


@login_required
@require_POST
def resync_pause(request, thread_id):
    if not has_permission(request.user, 'forum_manage'):
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    with RESYNC_LOCK:
        task = RESYNC_TASKS.get(thread_id)
        if task:
            task['status'] = 'paused'
            return JsonResponse({'status': 'paused'})
    return JsonResponse({'status': 'not_found'})


@login_required
@require_POST
def resync_resume(request, thread_id):
    if not has_permission(request.user, 'forum_manage'):
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    with RESYNC_LOCK:
        task = RESYNC_TASKS.get(thread_id)
        if task:
            task['status'] = 'running'
            return JsonResponse({'status': 'running'})
    return JsonResponse({'status': 'not_found'})


@login_required
@require_POST
def resync_stop(request, thread_id):
    if not has_permission(request.user, 'forum_manage'):
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    with RESYNC_LOCK:
        if thread_id in RESYNC_TASKS:
            RESYNC_TASKS[thread_id]['status'] = 'stopped'
            # remove task entry after marking stopped
            RESYNC_TASKS.pop(thread_id, None)
            return JsonResponse({'status': 'stopped'})
    return JsonResponse({'status': 'not_found'})


@login_required(login_url='/admin/login/')
def edit_ad(request, ad_id):
    if not has_permission(request.user, 'ad_edit'):
        return redirect('/admin/permission-denied/')
    
    ads = ad.objects.get(id=ad_id)

    if request.method == 'POST':
        form = AdForm(request.POST, request.FILES, instance=ads)
        if form.is_valid():
            form.save()
            return redirect('/admin/ads-management/')  # or any success page
    else:
        form = AdForm(instance=ads)

    return render(request, 'edit_ad.html', {'form': form})

@login_required(login_url='/admin/login/')
def delete_ad(request, ad_id):
    if not has_permission(request.user, 'ad_delete'):
        return redirect('/admin/permission-denied/')
    
    ads = ad.objects.get(id=ad_id)
    ads.delete()
    return redirect('/admin/ads-management/')

@login_required(login_url='/admin/login/')
def add_ad(request):
    if not has_permission(request.user, 'ad_add'):
        return redirect('/admin/permission-denied/')
    
    if request.method == 'POST':
        form = AdForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('/admin/ads-management/')
    else:
        form = AdForm()

    return render(request, 'add_ad.html', {'form': form})


@login_required(login_url='/admin/login/')
def users_view(request):
    if not has_permission(request.user, 'user_view'):
        return redirect('/admin/permission-denied/')

    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'join_date')  # default sort
    order = request.GET.get('order', 'desc')  # 'asc' or 'desc'

    users_list = CustomUser.objects.all()

    if search_query:
        users_list = users_list.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    if sort_by in ['username', 'email', 'join_date']:
        if order == 'desc':
            sort_by = '-' + sort_by
        users_list = users_list.order_by(sort_by)

    paginator = Paginator(users_list, 100)
    page_number = request.GET.get("page")
    users = paginator.get_page(page_number)

    sortable_fields = ['username', 'email', 'join_date']

    context = {
        'users': users,
        'search_query': search_query,
        'current_sort': sort_by.lstrip('-'),
        'current_order': order,
        'sortable_fields': sortable_fields,
    }

    return render(request, 'users.html', context)

@login_required(login_url='/admin/login/')
def edit_user(request, user_id):
    if not has_permission(request.user, 'user_edit'):
        return redirect('/admin/permission-denied/')
    
    badges = badge.objects.all()
    user = CustomUser.objects.get(id=user_id)
    return render(request, 'edit_user.html', {'user': user, 'badges': badges})

@login_required(login_url='/admin/login/')
def update_user(request, user_id):
    if not has_permission(request.user, 'user_edit'):
        return redirect('/admin/permission-denied/')
    
    user = CustomUser.objects.get(id=user_id)

    if (request.POST.get('banned') == 'on'):
        user.badges.set([48])
    else:
        user.badges.set(request.POST.getlist('badges'))

    if request.method == "POST":
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.banned = request.POST.get('banned') == 'on'
        
        user.save()
    return redirect('/admin/users-management/')

@login_required(login_url='/admin/login/')
def delete_user(request, user_id):
    if not has_permission(request.user, 'user_delete'):
        return redirect('/admin/permission-denied/')
    
    user = CustomUser.objects.get(id=user_id)
    user.delete()

@login_required(login_url='/admin/login/')
def feature_toggles_view(request):
    if not has_permission(request.user, 'feature_toggle_view'):
        return redirect('/admin/permission-denied/')
    
    feature_toggles = featureToggle.objects.all()
    return render(request, 'feature_toggles.html', {'feature_toggles': feature_toggles})

@login_required(login_url='/admin/login/')
def enable_feature(request, feature_id):
    if not has_permission(request.user, 'feature_toggle_enable'):
        return redirect('/admin/permission-denied/')

    feature = featureToggle.objects.get(id=feature_id)
    feature.enabled = True
    feature.coming_soon = False
    feature.maintenance = False
    feature.save()
    clear_feature_toggle_cache(feature.name)
    return redirect('/admin/feature-toggles-management/')

@login_required(login_url='/admin/login/')
def maintenance_feature(request, feature_id):
    if not has_permission(request.user, 'feature_toggle_maintenance'):
        return redirect('/admin/permission-denied/')
    
    feature = featureToggle.objects.get(id=feature_id)
    feature.maintenance = True
    feature.coming_soon = False
    feature.enabled = False
    feature.save()
    clear_feature_toggle_cache(feature.name)
    return redirect('/admin/feature-toggles-management/')

@login_required(login_url='/admin/login/')
def disable_feature(request, feature_id):
    if not has_permission(request.user, 'feature_toggle_disable'):
        return redirect('/admin/permission-denied/')
    
    feature = featureToggle.objects.get(id=feature_id)
    feature.enabled = False
    feature.coming_soon = False
    feature.maintenance = False
    feature.save()
    clear_feature_toggle_cache(feature.name)
    return redirect('/admin/feature-toggles-management/')

@login_required(login_url='/admin/login/')
def enable_ad_feature(request, feature_id):
    if not has_permission(request.user, 'feature_toggle_enable'):
        return redirect('/admin/permission-denied/')

    feature = featureToggle.objects.get(id=feature_id)
    feature.enabled = True
    feature.coming_soon = False
    feature.maintenance = False
    feature.save()
    clear_feature_toggle_cache(feature.name)
    return redirect('/admin/ads-management/')

@login_required(login_url='/admin/login/')
def disable_ad_feature(request, feature_id):
    if not has_permission(request.user, 'feature_toggle_disable'):
        return redirect('/admin/permission-denied/')
    
    feature = featureToggle.objects.get(id=feature_id)
    feature.enabled = False
    feature.coming_soon = False
    feature.maintenance = False
    feature.save()
    clear_feature_toggle_cache(feature.name)
    return redirect('/admin/ads-management/')

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


@login_required(login_url='/admin/login/')
def livery_management(request):
    if not has_permission(request.user, 'livery_view'):
        return redirect('/admin/permission-denied/')


    search_query = request.GET.get('q', '')
    liveries_list = liverie.objects.filter(name__icontains=search_query, declined=False).order_by('name')

    paginator = Paginator(liveries_list, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # If AJAX, return partial HTML
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('partials/livery_table.html', {'page_obj': page_obj})
        return JsonResponse({'html': html})

    return render(request, 'livery.html', {'page_obj': page_obj, 'search_query': search_query, 'approver': False})

@login_required(login_url='/admin/login/')
def vehicle_management(request):
    if not has_permission(request.user, 'vehicle_view'):
        return redirect('/admin/permission-denied/')


    search_query = request.GET.get('q', '')
    vehicles_list = vehicleType.objects.filter(type_name__icontains=search_query, hidden=False).order_by('type_name')

    paginator = Paginator(vehicles_list, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # If AJAX, return partial HTML
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('partials/vehicle_table.html', {'page_obj': page_obj})
        return JsonResponse({'html': html})

    return render(request, 'vehicles-manage.html', {'page_obj': page_obj, 'search_query': search_query, 'approver': False})

@login_required(login_url='/admin/login/')
def vehicle_approver(request):
    if not has_permission(request.user, 'vehicle_view'):
        return redirect('/admin/permission-denied/')


    search_query = request.GET.get('q', '')
    vehicles_list = vehicleType.objects.filter(type_name__icontains=search_query, hidden=False, active=False).order_by('type_name')

    paginator = Paginator(vehicles_list, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # If AJAX, return partial HTML
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('partials/vehicle_table.html', {'page_obj': page_obj})
        return JsonResponse({'html': html})

    return render(request, 'vehicles-manage.html', {'page_obj': page_obj, 'search_query': search_query, 'approver': True})


@login_required(login_url='/admin/login/')
def livery_approver(request):
    if not has_permission(request.user, 'livery_view'):
        return redirect('/admin/permission-denied/')


    search_query = request.GET.get('q', '')
    liveries_list = liverie.objects.filter(name__icontains=search_query, published=False, declined=False).order_by('name')

    paginator = Paginator(liveries_list, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # If AJAX, return partial HTML
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('partials/livery_table.html', {'page_obj': page_obj})
        return JsonResponse({'html': html})

    return render(request, 'livery.html', {'page_obj': page_obj, 'search_query': search_query, 'approver': True})


@login_required(login_url='/admin/login/')
def publish_livery(request, livery_id):
    force = request.GET.get('force', 'false').lower() == 'true'

    if not has_permission(request.user, 'livery_publish'):
        return redirect('/admin/permission-denied/')
    
    page_number = request.GET.get('page')
    livery = liverie.objects.get(id=livery_id)
    checkDuplicate = liverie.objects.filter(name=livery.name).exclude(id=livery_id).exclude(declined=True).exists()
    if not checkDuplicate or force == True:
        livery.published = True
        livery.aproved_by = request.user
        livery.save()
        return redirect('/admin/livery-management/pending/?page=' + str(page_number))

    return render(request, 'dupe_livery_check.html', {'livery': livery, 'other_liveries': liverie.objects.filter(name=livery.name).exclude(id=livery_id).exclude(declined=True)})

@login_required(login_url='/admin/login/')
def publish_vehicle(request, vehicle_id):
    if not has_permission(request.user, 'vehicle_publish'):
        return redirect('/admin/permission-denied/')

    page_number = request.GET.get('page')

    vehicle = vehicleType.objects.get(id=vehicle_id)
    vehicle.active = True
    vehicle.save()

    return redirect('/admin/vehicle-management/pending/?page=' + str(page_number))

@login_required(login_url='/admin/login/')
def edit_livery(request, livery_id):
    if not has_permission(request.user, 'livery_edit'):
        return redirect('/admin/permission-denied/')
    
    page_number = request.GET.get('page')

    if request.method == 'POST':
        livery = liverie.objects.get(id=livery_id)
        form = LiveryForm(request.POST, instance=livery)
        if form.is_valid():
            form.save()
            return redirect('/admin/livery-management/?page=' + str(page_number))
    else:
        livery = liverie.objects.get(id=livery_id)
        form = LiveryForm(instance=livery)
    
    return render(request, 'edit_livery.html', {'form': form})

@login_required(login_url='/admin/login/')
def edit_vehicle(request, vehicle_id):
    if not has_permission(request.user, 'vehicle_edit'):
        return redirect('/admin/permission-denied/')
    
    page_number = request.GET.get('page')

    if request.method == 'POST':
        vehicle = vehicleType.objects.get(id=vehicle_id)
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            return redirect('/admin/vehicle-management/?page=' + str(page_number))
    else:
        vehicle = vehicleType.objects.get(id=vehicle_id)
        form = VehicleForm(instance=vehicle)

    return render(request, 'edit_vehicle.html', {'form': form})

@login_required(login_url='/admin/login/')
def delete_livery(request, livery_id):
    if not has_permission(request.user, 'livery_delete'):
        return redirect('/admin/permission-denied/')
    
    # Use get_object_or_404 for better error handling
    livery = get_object_or_404(liverie, id=livery_id)

    page_number = request.GET.get('page', '1')

    # Check if any vehicle is using this livery
    if fleet.objects.filter(livery=livery).exists():
        other_liveries = liverie.objects.filter(name=livery.name).exclude(id=livery_id)
        return render(request, 'dupe_livery.html', {'livery': livery, 'other_liveries': other_liveries})

    livery.declined = True
    livery.save()
    return redirect(f'/admin/livery-management/pending/?page={page_number}')

@login_required(login_url='/admin/login/')
def delete_vehicle(request, vehicle_id):
    if not has_permission(request.user, 'vehicle_delete'):
        return redirect('/admin/permission-denied/')

    vehicle = vehicleType.objects.get(id=vehicle_id)
    page_number = request.GET.get('page')

    # Check if any vehicle in MyBusTimes.fleet is using this vehicle
    if fleet.objects.filter(vehicleType=vehicle).exists():
        other_vehicles = vehicleType.objects.filter(type_name=vehicle.type_name).exclude(id=vehicle_id)

        return render(request, 'dupe_vehicle.html', {'vehicle': vehicle, 'other_vehicles': other_vehicles})

    vehicle.delete()
    return redirect('/admin/vehicle-management/?page=' + str(page_number))

@login_required(login_url='/admin/login/')
def replace_livery(request):
    if not has_permission(request.user, 'livery_replace'):
        return redirect('/admin/permission-denied/')
    
    old_livery = liverie.objects.get(id=request.GET.get('old'))
    new_livery = liverie.objects.get(id=request.GET.get('new'))

    fleet.objects.filter(livery=old_livery).update(livery=new_livery)

    page_number = request.GET.get('page')

    old_livery.declined = True
    old_livery.save()
    return redirect('/admin/livery-management/?page=' + str(page_number))

@login_required(login_url='/admin/login/')
def replace_vehicle(request):
    if not has_permission(request.user, 'vehicle_replace'):
        return redirect('/admin/permission-denied/')

    old_vehicle = vehicleType.objects.get(id=request.GET.get('old'))
    new_vehicle = vehicleType.objects.get(id=request.GET.get('new'))

    fleet.objects.filter(vehicleType=old_vehicle).update(vehicleType=new_vehicle)

    page_number = request.GET.get('page')

    old_vehicle.delete()
    return redirect('/admin/vehicle-management/?page=' + str(page_number))

@login_required(login_url='/admin/login/')
def applications_management(request):
    if not has_permission(request.user, 'applications_view'):
        return redirect('/admin/permission-denied/')

    page_number = request.GET.get('page', 1)
    applications_qs = Application.objects.all().order_by('-created_at')

    paginator = Paginator(applications_qs, 10)  # Show 10 applications per page
    try:
        applications = paginator.page(page_number)
    except PageNotAnInteger:
        applications = paginator.page(1)
    except EmptyPage:
        applications = paginator.page(paginator.num_pages)

    return render(request, 'applications_management.html', {
        'applications': applications
    })

@login_required(login_url='/admin/login/')
def application_detail(request, application_id):
    if not has_permission(request.user, 'applications_view'):
        return redirect('/admin/permission-denied/')

    application = get_object_or_404(Application, pk=application_id)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "continue":
            # Create a new group chat
            chat = Chat.objects.create(
                chat_type="group_private",
                name=f"Group chat for application #{application.id}",
                description=f"Group chat for application #{application.id}",
                created_by=request.user
            )

            # Add applicant
            ChatMember.objects.create(chat=chat, user=application.applicant, is_admin=False)

            # Add all users with mbt_admin permission
            admins = CustomUser.objects.filter(username=request.user.username).distinct()
            for admin_user in admins:
                ChatMember.objects.create(chat=chat, user=admin_user, is_admin=True)



            # Link the chat to the application
            application.chat = chat
            application.status = "accepted"
            application.save()

            # Send email to applicant
            chat_link = f"https://mybustimes.cc/chat/{chat.id}/"
            subject = "Your Application Has Been Accepted"
            message = (
                f"Hello {application.applicant.get_full_name() or application.applicant.username},\n\n"
                f"Your application has been accepted. We've created a group chat so we can continue the process.\n"
                f"You can join the chat here: {chat_link}\n\n"
                "Thank you,\nThe MyBusTimes Team"
            )

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [application.applicant.email],
                fail_silently=False,
            )

            return redirect("chat_detail", chat_id=chat.id)

        elif action == "decline":
            application.status = "declined"
            application.save()
            return redirect("applications_management")

    return render(request, "application_detail.html", {
        "application": application,
        "answers": application.question_answers or {}
    })

@login_required(login_url='/admin/login/')
def flip_livery(request):    
    return render(request, 'flip.html')
