import random
import logging
from django.conf import settings
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


def _post(channel_id, payload):
    if settings.DISABLE_JESS:
        return
    try:
        requests.post(
            f"{settings.DISCORD_BOT_API_URL}/send-embed",
            json=payload,
            timeout=8,
        )
    except Exception:
        logger.exception("Failed to send livery pending Discord embed (channel %s)", channel_id)


def send_to_discord(count):
    # Role IDs to ping
    role_ids = ["1348464021313032232", "1406415722015363203", "1425155506024091701"]
    ping_lines = "\n".join(f"<@&{rid}>" for rid in role_ids)
    reminder = "Please check for any pending liveries."
    ping_message = f"{ping_lines}\n\n{reminder}"

    # Embed definition
    embed = {
        "title": "Livery Pending check",
        "description": "https://www.mybustimes.cc/admin/livery-management/pending/",
        "color": "#00BFFF",  # DeepSkyBlue
        "fields": [
            {
                "name": "🕒 Time",
                "value": datetime.now().strftime('%Y-%m-%d %H:%M'),
                "inline": True
            }
        ],
        "footer": {
            "text": "MBT Livery Manager"
        },
        "timestamp": datetime.now().isoformat()
    }

    # Send to first channel with role pings
    _post(1430515045539774494, {
        'channel_id': 1430515045539774494,
        'content': ping_message,
        'embed': embed
    })

    # Send to second channel without pings
    _post(1429276550905204757, {
        'channel_id': 1429276550905204757,
        'embed': embed
    })

