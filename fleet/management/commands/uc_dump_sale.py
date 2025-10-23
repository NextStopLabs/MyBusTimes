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
        "color": 0xFF0000,  # DeepSkyBlue
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

def send_service_to_discord(count):
    embed = {
        "title": "🚗 Vehicle Service Update",
        "description": f"**Set {count} vehicles in service**",
        "color": 0x0000FF,  # DeepSkyBlue
        "fields": [
            {
                "name": "🕒 Time",
                "value": datetime.now().strftime('%Y-%m-%d %H:%M'),
                "inline": True
            }
        ],
        "footer": {
            "text": "UC Engineer Report Manager"
        },
        "timestamp": datetime.now().isoformat()
    }
    
    data = {
        'channel_id': 1429466839687106671,
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
        # Step 1: Count UC vehicles currently for sale
        uc_for_sale_count = fleet.objects.filter(operator__operator_code='UC', for_sale=True).count()
        uc_not_service_count = fleet.objects.filter(operator__operator_code='UC', in_service=False).count()
        vehicles = fleet.objects.filter(operator__operator_code='UC', in_service=False)
        for vehicle in vehicles: 
            vehicle.in_service = True
            vehicle.save()

        if uc_not_service_count > 0:
            send_service_to_discord(uc_not_service_count)

        if uc_for_sale_count < 50:
            # Step 2: Get all UC vehicles
            uc_vehicles = list(fleet.objects.filter(operator__operator_code='UC'))
            list_amount = 201 - uc_for_sale_count 

            # Step 3: Shuffle and select vehicles for sale
            random.shuffle(uc_vehicles)
            selected = uc_vehicles[:list_amount]

            # Step 4: Bulk update
            fleet.objects.filter(id__in=[v.id for v in selected]).update(for_sale=True)

            # Step 5: Notify via Discord
            if (len(selected) > 0):
                send_to_discord(len(selected))

            self.stdout.write(self.style.SUCCESS(f"Updated {len(selected)} UC vehicles to for_sale=True"))
        else:
            self.stdout.write(f"UC fleet has {uc_for_sale_count} vehicles for sale — no update needed.")
