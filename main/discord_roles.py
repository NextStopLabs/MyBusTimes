import logging
import re

import requests
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from main.models import ActiveSubscription

logger = logging.getLogger(__name__)

PRO_PLANS = {"pro", "premium"}
DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_BOOSTER_CACHE_TIMEOUT = 300


def user_has_active_pro(user):
    now = timezone.now()
    return (
        ActiveSubscription.objects.filter(user=user)
        .filter(Q(end_date__isnull=True) | Q(end_date__gt=now))
        .filter(plan__in=PRO_PLANS)
        .exists()
        or (
            getattr(user, "sub_plan", "free") in PRO_PLANS
            and user.ad_free_until is not None
            and user.ad_free_until > now
        )
    )


def user_has_ad_free(user, is_discord_booster=None):
    now = timezone.now()
    has_paid_ad_free = (
        ActiveSubscription.objects.filter(user=user)
        .filter(Q(end_date__isnull=True) | Q(end_date__gt=now))
        .exists()
        or (
            getattr(user, "sub_plan", "free") != "free"
            and user.ad_free_until is not None
            and user.ad_free_until > now
        )
    )

    if has_paid_ad_free:
        return True

    if is_discord_booster is None:
        is_discord_booster = user_is_discord_booster(user)

    return is_discord_booster


def discord_booster_cache_key(user_id):
    return f"discord_booster:{user_id}"


def clear_discord_booster_cache(user):
    if getattr(user, "id", None):
        cache.delete(discord_booster_cache_key(user.id))


def user_is_discord_booster(user, use_cache=True):
    if not getattr(settings, "DISCORD_BOOSTER_AD_FREE_ENABLED", True):
        return False

    discord_id = (getattr(user, "discord_id", "") or "").strip()
    if not discord_id:
        return False

    cache_key = discord_booster_cache_key(user.id)
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    guild_id = getattr(settings, "DISCORD_GUILD_ID", None)
    bot_token = getattr(settings, "DISCORD_BOT_TOKEN", None)
    if not guild_id or not bot_token:
        return False

    headers = {"Authorization": f"Bot {bot_token}"}
    try:
        response = requests.get(
            f"{DISCORD_API_BASE}/guilds/{guild_id}/members/{discord_id}",
            headers=headers,
            timeout=10,
        )
        if response.status_code == 404:
            is_booster = False
        else:
            response.raise_for_status()
            is_booster = bool(response.json().get("premium_since"))
    except requests.RequestException:
        logger.exception("Failed to check Discord boost status for user %s", user.username)
        is_booster = False

    cache.set(cache_key, is_booster, DISCORD_BOOSTER_CACHE_TIMEOUT)
    return is_booster


def sync_discord_ad_free_role(user, has_ad_free=None):
    if has_ad_free is None:
        has_ad_free = user_has_ad_free(user)
    return _sync_discord_role(user, getattr(settings, "DISCORD_AD_FREE_ROLE_ID", None), has_ad_free, "Ad Free")


def sync_discord_pro_role(user, has_pro=None):
    if has_pro is None:
        has_pro = user_has_active_pro(user)
    return _sync_discord_role(user, getattr(settings, "DISCORD_PRO_ROLE_ID", None), has_pro, "Pro")


def sync_discord_entitlement_roles(user, is_discord_booster=None):
    return {
        "ad_free": sync_discord_ad_free_role(user, user_has_ad_free(user, is_discord_booster=is_discord_booster)),
        "pro": sync_discord_pro_role(user, user_has_active_pro(user)),
    }


def _sync_discord_role(user, role_id, should_have_role, role_name):
    guild_id = getattr(settings, "DISCORD_GUILD_ID", None)
    bot_token = getattr(settings, "DISCORD_BOT_TOKEN", None)
    discord_id = (getattr(user, "discord_id", "") or "").strip()
    discord_name = (getattr(user, "discord_username", "") or "").strip()

    if not role_id or not guild_id or not bot_token or not (discord_id or discord_name):
        return False

    member_id = discord_id or _resolve_discord_member_id(guild_id, bot_token, discord_name)
    if not member_id:
        logger.warning("Could not find Discord member for %s role sync for user %s using %r", role_name, user.username, discord_name)
        return False

    headers = {"Authorization": f"Bot {bot_token}"}
    url = f"{DISCORD_API_BASE}/guilds/{guild_id}/members/{member_id}/roles/{role_id}"

    try:
        response = (
            requests.put(url, headers=headers, timeout=10)
            if should_have_role
            else requests.delete(url, headers=headers, timeout=10)
        )
        if response.status_code == 404:
            logger.warning(
                "Discord member %s is not in guild %s; cannot sync %s role for user %s",
                member_id,
                guild_id,
                role_name,
                user.username,
            )
            return False
        response.raise_for_status()
        return True
    except requests.RequestException:
        response_text = getattr(locals().get("response", None), "text", "")
        logger.exception("Failed to sync Discord %s role for user %s: %s", role_name, user.username, response_text)
        return False


def ensure_discord_guild_member(discord_id, access_token):
    guild_id = getattr(settings, "DISCORD_GUILD_ID", None)
    bot_token = getattr(settings, "DISCORD_BOT_TOKEN", None)

    if not guild_id or not bot_token or not discord_id or not access_token:
        return False

    try:
        response = requests.put(
            f"{DISCORD_API_BASE}/guilds/{guild_id}/members/{discord_id}",
            headers={
                "Authorization": f"Bot {bot_token}",
                "Content-Type": "application/json",
            },
            json={"access_token": access_token},
            timeout=10,
        )
        if response.status_code in {201, 204}:
            return True
        response.raise_for_status()
        return True
    except requests.RequestException:
        response_text = getattr(locals().get("response", None), "text", "")
        logger.exception("Failed to add Discord user %s to guild %s: %s", discord_id, guild_id, response_text)
        return False


def _resolve_discord_member_id(guild_id, bot_token, discord_name):
    direct_id = _extract_discord_user_id(discord_name)
    if direct_id:
        return direct_id

    query = _normalise_discord_search_query(discord_name)
    if not query:
        return None

    headers = {"Authorization": f"Bot {bot_token}"}
    try:
        response = requests.get(
            f"{DISCORD_API_BASE}/guilds/{guild_id}/members/search",
            headers=headers,
            params={"query": query, "limit": 10},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Failed to search Discord member %r", discord_name)
        return None

    members = response.json()
    if not members:
        return None

    lowered_name = discord_name.lower()
    lowered_query = query.lower()
    for member in members:
        user = member.get("user", {})
        candidates = {
            str(user.get("id", "")),
            str(user.get("username", "")),
            str(user.get("global_name", "")),
            str(member.get("nick", "")),
        }
        if lowered_name in {candidate.lower() for candidate in candidates if candidate}:
            return user.get("id")

    for member in members:
        user = member.get("user", {})
        candidates = [
            str(user.get("username", "")),
            str(user.get("global_name", "")),
            str(member.get("nick", "")),
        ]
        if any(lowered_query in candidate.lower() for candidate in candidates if candidate):
            return user.get("id")

    return members[0].get("user", {}).get("id")


def _extract_discord_user_id(value):
    mention_match = re.fullmatch(r"<@!?(\d{15,25})>", value)
    if mention_match:
        return mention_match.group(1)

    if re.fullmatch(r"\d{15,25}", value):
        return value

    return None


def _normalise_discord_search_query(value):
    if "#" in value:
        value = value.split("#", 1)[0]
    return value.strip().lstrip("@")
