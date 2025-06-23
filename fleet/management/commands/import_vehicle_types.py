from django.core.management.base import BaseCommand
from fleet.models import vehicleType
from mybustimes.models import CustomUser  # Adjust this import based on your user model location
import csv

class Command(BaseCommand):
    help = 'Import vehicle types from a CSV file'

    def handle(self, *args, **kwargs):
        try:
            user = CustomUser.objects.get(id=1)
        except CustomUser.DoesNotExist:
            self.stdout.write(self.style.ERROR('User with ID 1 does not exist.'))
            return

        with open('vehicle_types.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                vehicleType.objects.update_or_create(
                    id=row['ID'],
                    defaults={
                        'type_name': row['TypeName'] or "black",
                        'double_decker': bool(int(row['DoubleDecker'])),
                        'active': bool(int(row['Live'])),
                        'added_by': user,
                        'aproved_by': user,
                    }
                )

        self.stdout.write(self.style.SUCCESS('Successfully imported vehicle types.'))
