import random
from django.core.management.base import BaseCommand
from fleet.models import fleet  # Adjust if your model lives elsewhere
from django.conf import settings
from datetime import datetime
import requests

def send_to_discord(count):
    role_id = ["1348464021313032232", "1406415722015363203", "1425155506024091701"]  # Replace with your actual role ID
    ping_message = "\n".join(f"<@&{role_id}>" for role_id in role_ids) 
    reminder = "Please check for any pending liveries."

    embed = {
        "title": "Livery Pending check",
        "description": f"https://www.mybustimes.cc/admin/livery-management/pending/",
        "color": "#FFA500",  # Use valid hex color (DeepSkyBlue is #00BFFF)
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

    data = {
        'channel_id': 1430515045539774494,
        'content': ping_message,  # This sends the role ping
        'embed': embed
    }

    response = requests.post(
        f"{settings.DISCORD_BOT_API_URL}/send-embed",
        json=data
    )
    response.raise_for_status()

    embed = {
        "title": "Livery Pending check",
        "description": f"https://www.mybustimes.cc/admin/livery-management/pending/",
        "color": "#FFAASS",  # DeepSkyBlue
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
    
    data = {
        'channel_id': 1429276550905204757,
        'embed': embed
    }

    response = requests.post(
        f"{settings.DISCORD_BOT_API_URL}/send-embed",
        json=data
    )
    response.raise_for_status()
