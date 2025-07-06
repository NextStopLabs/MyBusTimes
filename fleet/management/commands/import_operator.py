import csv
from django.core.management.base import BaseCommand
from main.models import CustomUser, region
from fleet.models import MBTOperator, group, organisation

class Command(BaseCommand):
    help = "Import operators from CSV"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=',', quotechar='"')
            reader.fieldnames = [h.strip() for h in reader.fieldnames]

            max_len = 50

            for row in reader:
                id = row['ID']
                operator_code = row['Operator_Code']
                operator_name = row['Operator_Name'][:max_len]
                owner_username = row['Owner']
                private = bool(int(row['Private'])) if row['Private'] and row['Private'].isdigit() else False
                public = bool(int(row['Public'])) if row['Public'] and row['Public'].isdigit() else False
                group_name = row.get('Group')
                organisation_name = row.get('organisation')
                region_names = row.get('Region', '')  # comma separated string
                
                print(f"Importing operator {operator_name} ({operator_code})")

                # Find or create owner user
                try:
                    owner = CustomUser.objects.get(username=owner_username)
                except CustomUser.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Owner user '{owner_username}' not found moved to default user 'Admin'"))
                    owner = CustomUser.objects.get(username='Admin')

                # Create or update operator
                operator, created = MBTOperator.objects.update_or_create(
                    operator_code=operator_code,
                    defaults={
                        'operator_name': operator_name,
                        'private': private,
                        'public': public,
                        'owner': owner,
                        'operator_details': {
                        }
                    }
                )

                # Handle many-to-many regions
                if region_names:
                    region_list = [r.strip() for r in region_names.split(',') if r.strip()]
                    regions_qs = region.objects.filter(region_name__in=region_list)
                    operator.region.set(regions_qs)
                else:
                    operator.region.clear()

                operator.save()

                self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} operator {operator_name} ({operator_code})"))
