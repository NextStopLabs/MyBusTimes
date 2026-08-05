import logging

from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.signals import request_finished
from django.db import close_old_connections, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser
from .flagging import enqueue_signup_flagging

logger = logging.getLogger(__name__)

@receiver(user_logged_in)
def send_login_notification(sender, request, user, **kwargs):
    cache_key = f"login_email_{user.pk}"
    if cache.get(cache_key):
        return  
    cache.set(cache_key, True, timeout=1800)  #

    if not user.email:
        return

    ip = (
        request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        or request.META.get("REMOTE_ADDR", "Unknown")
    )
    user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")

    send_mail(
        subject="New login to your MyBusTimes account",
        message=f"""Hi {user.username},

A new login was detected on your account.

IP Address: {ip}
Browser: {user_agent}

If this wasn't you, please change your password immediately.

— The MyBusTimes Team
""",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,  # Don't break login if email fails
    )


@receiver(post_save, sender=CustomUser)
def monitor_new_user_signup(sender, instance, created, **kwargs):
    if not created:
        return

    transaction.on_commit(lambda: enqueue_signup_flagging(instance.pk))


@receiver(request_finished)
def cleanup_db_connections_on_request_finish(**kwargs):
    """
    Force-close stale database connections at the end of every HTTP request.

    In ASGI mode Django's default close_old_connections only runs in the
    event-loop thread.  Sync views executed in thread-pool threads can leak
    connections because those threads are invisible to the async handler.
    This signal gives the OS thread that serviced the request one more chance
    to release its connection before returning to the pool.
    """
    try:
        close_old_connections()
    except Exception:
        pass