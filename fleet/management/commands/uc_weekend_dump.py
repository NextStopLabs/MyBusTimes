import random
from django.core.management.base import BaseCommand
from fleet.models import fleet  # Adjust if your model lives elsewhere
from django.conf import settings
from datetime import datetime
import requests

def send_to_discord(count):
    embed = {
        "title": "🚗 Vehicle Listings Update",
        "description": f"**Listed {count} vehicles for sale**",
        "color": 0x00BFFF,  # DeepSkyBlue
        "fields": [
            {
                "name": "🕒 Time",
                "value": datetime.now().strftime('%Y-%m-%d %H:%M'),
                "inline": True
            }
        ],
        "footer": {
            "text": "UC Sales Report Manager"
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



class Command(BaseCommand):
    help = "Ensure at least 200 UC fleet vehicles are marked for sale if count drops below 50"

    def handle(self, *args, **kwargs):
            # Step 1: Get all UC vehicles
            uc_vehicles = list(fleet.objects.filter(operator__operator_code='UC'))

            # Step 2: Shuffle and select 1000
            random.shuffle(uc_vehicles)
            selected = uc_vehicles[:1000]

            # Step 3: Bulk update
            fleet.objects.filter(id__in=[v.id for v in selected]).update(for_sale=True)

            # Step 5: Notify via Discord
            if (len(selected) > 0):
                send_to_discord(len(selected))

                self.stdout.write(self.style.SUCCESS(f"Updated {len(selected)} UC vehicles to for_sale=True"))
            else:
                self.stdout.write(f"UC fleet has {len(selected)} vehicles for sale — no update needed.")
