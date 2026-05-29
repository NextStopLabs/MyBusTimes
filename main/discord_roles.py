import logging
import re

import requests
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from main.models import ActiveSubscription

logger = logging.getLogger(__name__)

PRO_PLANS = {"pro", "premium"}
DISCORD_API_BASE = "https://discord.com/api/v10"


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


def sync_discord_pro_role(user, has_pro=None):
    role_id = getattr(settings, "DISCORD_PRO_ROLE_ID", None)
    guild_id = getattr(settings, "DISCORD_GUILD_ID", None)
    bot_token = getattr(settings, "DISCORD_BOT_TOKEN", None)
    discord_id = (getattr(user, "discord_id", "") or "").strip()
    discord_name = (getattr(user, "discord_username", "") or "").strip()

    if not role_id or not guild_id or not bot_token or not (discord_id or discord_name):
        return False

    if has_pro is None:
        has_pro = user_has_active_pro(user)

    member_id = discord_id or _resolve_discord_member_id(guild_id, bot_token, discord_name)
    if not member_id:
        logger.warning("Could not find Discord member for user %s using %r", user.username, discord_name)
        return False

    headers = {"Authorization": f"Bot {bot_token}"}
    url = f"{DISCORD_API_BASE}/guilds/{guild_id}/members/{member_id}/roles/{role_id}"

    try:
        response = (
            requests.put(url, headers=headers, timeout=10)
            if has_pro
            else requests.delete(url, headers=headers, timeout=10)
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        logger.exception("Failed to sync Discord Pro role for user %s", user.username)
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
