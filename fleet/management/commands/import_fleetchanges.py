import csv
import json
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from fleet.models import fleet, fleetChange, vehicleType, MBTOperator
from main.models import CustomUser


class Command(BaseCommand):
    help = 'Import fleet change history from CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)
        parser.add_argument('--user-id', type=int, help='ID of the user making the import')

    def handle(self, *args, **kwargs):
        csv_file_path = kwargs['csv_file']
        
        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                fleet_number = row['FleetNumber_New'].strip()
                reg = row['Reg_New'].strip()
                vehicle_id_raw = row.get("Vehicl_ID", "").strip()
                vehicle_id = int(vehicle_id_raw) if vehicle_id_raw.isdigit() else None

                user_id = row['User'].strip()

                print(user_id)

                user = None
                if user_id and user_id != 'NULL':
                    try:
                        user = CustomUser.objects.get(username=user_id)
                    except CustomUser.DoesNotExist:
                       user = CustomUser.objects.get(id=4416)
                else:
                    user = CustomUser.objects.get(id=4416)

                vehicle = None
                if vehicle_id:
                    vehicle = fleet.objects.filter(id=vehicle_id).first()


                vehicle = None

                if vehicle_id:
                    vehicle = fleet.objects.filter(id=vehicle_id).first()

                if not vehicle:
                    vehicle = fleet.objects.filter(fleet_number=fleet_number, reg__iexact=reg).first()

                if not vehicle:
                    self.stdout.write(self.style.WARNING(f"Vehicle not found for row: {row}"))
                    continue

                changes = []

                def add_change(field, old, new):
                    old_val = str(old).strip() if old else ''
                    new_val = str(new).strip() if new else ''
                    if old_val != new_val:
                        changes.append({"item": field, "from": old_val, "to": new_val})

                # Add fields from CSV
                add_change("fleet_number", row['FleetNumber_Old'], row['FleetNumber_New'])
                add_change("reg", row['Reg_Old'], row['Reg_New'])
                add_change("branding", row['Branding_Old'], row['Branding_New'])
                add_change("in_service", row['InService_Old'], row['InService_New'])
                add_change("for_sale", row['For_Sale_Old'], row['For_Sale_New'])
                add_change("preserved", row['Preserved_Old'], row['Preserved_New'])
                add_change("prev_reg", row['PrevReg_Old'], row['PrevReg_New'])
                add_change("name", row['Name_Old'], row['Name_New'])
                add_change("type_details", row['Additional_Type_Details_Old'], row['Additional_Type_Details_New'])
                add_change("depot", row['Depot_Old'], row['Depot_New'])

                # Vehicle type from ID
                if row['Type_Old'] != row['Type_New']:
                    try:
                        old_type = vehicleType.objects.get(id=row['Type_Old']).type_name
                    except vehicleType.DoesNotExist:
                        old_type = f"Unknown (ID {row['Type_Old']})"

                    try:
                        new_type = vehicleType.objects.get(id=row['Type_New']).type_name
                    except vehicleType.DoesNotExist:
                        new_type = f"Unknown (ID {row['Type_New']})"

                    add_change("vehicle_type", old_type, new_type)

                # Operator code changes
                if row['OperatorCode_Old'] != row['OperatorCode_New']:
                    add_change("operator", row['OperatorCode_Old'], row['OperatorCode_New'])

                # Hex changes
                add_change("hex", row['Old_hex'], row['New_hex'])

                # If changes found, log it
                if changes:
                    fc = fleetChange.objects.create(
                        vehicle=vehicle,
                        operator=vehicle.operator,
                        user=user,
                        approved_by=user,
                        approved_at=now(),
                        changes=json.dumps(changes),
                        message=row.get("Summary", "")
                    )
                    self.stdout.write(self.style.SUCCESS(f"Change logged for vehicle {vehicle.fleet_number} (ID {vehicle.id})"))

        self.stdout.write(self.style.SUCCESS("CSV import completed"))
