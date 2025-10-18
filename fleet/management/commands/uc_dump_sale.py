import random
from django.core.management.base import BaseCommand
from fleet.models import fleet  # Adjust if your model lives elsewhere

class Command(BaseCommand):
    help = "Ensure at least 200 UC fleet vehicles are marked for sale if count drops below 50"

    def handle(self, *args, **kwargs):
        # Step 1: Count UC vehicles currently for sale
        uc_for_sale_count = fleet.objects.filter(operator__operator_code='UC', for_sale=True).count()

        if uc_for_sale_count < 50:
            # Step 2: Get all UC vehicles
            uc_vehicles = list(fleet.objects.filter(operator__operator_code='UC'))

            # Step 3: Shuffle and select 200
            random.shuffle(uc_vehicles)
            selected = uc_vehicles[:200]

            # Step 4: Bulk update
            fleet.objects.filter(id__in=[v.id for v in selected]).update(for_sale=True)

            self.stdout.write(self.style.SUCCESS(f"Updated {len(selected)} UC vehicles to for_sale=True"))
        else:
            self.stdout.write(f"UC fleet has {uc_for_sale_count} vehicles for sale — no update needed.")
