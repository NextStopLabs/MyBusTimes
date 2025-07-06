import csv
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from main.models import CustomUser
from fleet.models import MBTOperator, liverie, vehicleType, fleet
from datetime import datetime

class Command(BaseCommand):
    help = 'Import fleet data from CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)

    def handle(self, *args, **kwargs):
        file_path = kwargs['csv_file']

        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    operator_code = row.get('operator_code', '').strip()
                    loan_code = row.get('LoanCode', '').strip()

                    try:
                        operator = MBTOperator.objects.get(operator_code=operator_code)
                    except MBTOperator.DoesNotExist:
                        self.stderr.write(self.style.WARNING(f"Operator code '{operator_code}' not found. Defaulting to 'LOVS'."))
                        operator = MBTOperator.objects.get(operator_code='LOVS')  # Default fallback

                    loan_operator = None
                    if loan_code:
                        try:
                            loan_operator = MBTOperator.objects.get(operator_code=loan_code)
                        except MBTOperator.DoesNotExist:
                            self.stderr.write(self.style.WARNING(f"Loan operator code '{loan_code}' not found. Skipping loan_operator."))

                    livery_obj = liverie.objects.filter(pk=row['Livery']).first() if row['Livery'].isdigit() else None
                    vehicle_type = vehicleType.objects.filter(pk=row['Type']).first() if row['Type'].isdigit() else None
                    
                    last_tracked_date = parse_datetime(row['LastTrackedTime']) if row['LastTrackedTime'] not in ['NULL', '', None] else None

                    atd = ''

                    if row['Additional_Type_Details'] == 'NULL':
                        atd = ''
                    else:
                        atd = row['Additional_Type_Details'].strip()

                    if row['hex'] == 'NULL':
                        hexColour = ''
                    else:
                        hexColour = row['hex'].strip()

                    fleet_obj, created = fleet.objects.update_or_create(
                        id=row['ID'],
                        defaults={
                            'reg': row['Reg'],
                            'vehicleType': vehicle_type,
                            'livery': livery_obj,
                            'in_service': row['InService'] == '1',
                            'branding': row['Branding'],
                            'fleet_number': row['FleetNumber'],
                            'operator': operator,
                            'features': row['Special_Features'].split(',') if row['Special_Features'] else [],
                            'name': row['Name'] or '',
                            'prev_reg': row['PrevReg'] or '',
                            'for_sale': row['For_Sale'] == '1',
                            'depot': row['Depot'].strip() if row['Depot'] else '',
                            'last_tracked_date': last_tracked_date,
                            'last_tracked_route': row['LastTrackedAs'] or '',
                            'preserved': row['Preserved'] == '1',
                            'notes': row['Notes'] or '',
                            'length': row['Lenth'] or '',
                            'open_top': row['OpenTop'] == '1',
                            'loan_operator': loan_operator,
                            'type_details': atd,
                            'colour': hexColour,
                            'last_modified_by': CustomUser.objects.filter(is_superuser=True).first(), 
                        }
                    )

                    action = "Created" if created else "Updated"
                    self.stdout.write(self.style.SUCCESS(f"{action} fleet entry: {fleet_obj}"))

                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error processing row ID={row.get('ID')}: {e}"))
