import csv
from django.core.management.base import BaseCommand
from fleet.models import ticket, MBTOperator

class Command(BaseCommand):
    help = 'Import tickets from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        csv_path = options['csv_file']

        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    operator_code = row['Operator_Code']

                    try:
                        operator = MBTOperator.objects.get(operator_code=operator_code)
                    except MBTOperator.DoesNotExist:
                        self.stderr.write(self.style.WARNING(f"Operator code '{operator_code}' not found. Defaulting to 'LOVS'."))
                        operator = MBTOperator.objects.get(operator_code='LOVS')  # Default fallback

                    ticket_obj, created = ticket.objects.update_or_create(
                        id=row['ID'],
                        defaults={
                            'operator': operator,
                            'ticket_name': row['TicketName'],
                            'ticket_price': row['TicketPrice'],
                            'ticket_details': row['Description'],
                            'zone': row['Zone'],
                            'valid_for_days': int(row['ValidForTime']) if row['ValidForTime'] else None,
                            'single_use': row['OneTime'] == '1',
                            'name_on_ticketer': row['TicketerName'] or '',
                            'colour_on_ticketer': row['TicketerColour'] or '',
                            'ticket_category': row['TicketerCat'] or '',
                            'hidden_on_ticketer': row['AvaiableOnBus'] == '0',  # True if NOT available
                        }
                    )

                    action = "Created" if created else "Updated"
                    self.stdout.write(self.style.SUCCESS(f"{action} ticket: {ticket_obj}"))

                except MBTOperator.DoesNotExist:
                    self.stderr.write(self.style.ERROR(f"Operator with code '{row['Operator_Code']}' not found. Skipping ticket ID {row['ID']}"))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error processing ticket ID {row.get('ID')}: {e}"))
