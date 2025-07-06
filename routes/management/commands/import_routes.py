import csv
import json
from datetime import datetime
from django.core.management.base import BaseCommand
from routes.models import route, routeStop, timetableEntry, dayType
from fleet.models import MBTOperator  # Ensure this import matches your actual model location

def safe_date(value):
    try:
        if value in (None, '', 'NULL', '0000-00-00', '0000-01-01'):
            return None
        return value  # Django will parse string date properly
    except Exception:
        return None

class Command(BaseCommand):
    help = 'Import route and timetable data from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to your CSV file')

    def handle(self, *args, **options):
        file_path = options['csv_file']

        try:
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    # Get or create operator
                    try:
                        operator = MBTOperator.objects.get(operator_code=row['Route_Operator'])
                    except MBTOperator.DoesNotExist:
                        self.stderr.write(self.style.ERROR(f"Operator not found for code: {row['Route_Operator']}"))
                        continue

                    value = row.get('RouteBranding', '')
                    if value is None or value.upper() == "NULL":
                        value = ''

                    # Create or update route
                    route_obj, _ = route.objects.update_or_create(
                        id=row['Route_ID'],
                        defaults={
                            'route_num': row['Route_Name'],
                            'route_name': value,
                            'start_date': safe_date(row.get('running-from', '') or None),
                            'inbound_destination': row.get('End_Destination', '') or None,
                            'outbound_destination': row.get('Start_Destination', '') or None,
                        }
                    )
                    route_obj.route_operators.set([operator])
                    route_obj.save()

                    self.stdout.write(self.style.SUCCESS(f"Imported route {route_obj}"))

                    # Parse Stops (if provided)
                    for is_inbound, stop_field in [(False, 'STOP'), (True, 'STOP2')]:
                        stop_data_raw = row.get(stop_field)
                        if stop_data_raw and stop_data_raw.strip():
                            stop_lines = stop_data_raw.strip().split('\n')
                            stop_json = [{"stop": line.strip()} for line in stop_lines if line.strip()]
                            routeStop.objects.update_or_create(
                                route=route_obj,
                                inbound=is_inbound,
                                defaults={"stops": stop_json}
                            )
                            self.stdout.write(self.style.NOTICE(f"Added {'Inbound' if is_inbound else 'Outbound'} stops"))

                    # Timetable logic
                    for timetable_field, is_inbound in [('ServiceJSON', False), ('ServiceJSON2', True)]:
                        service_json = row.get(timetable_field)
                        if service_json and service_json.strip():
                            try:
                                service_data = json.loads(service_json)

                                for stop in service_data.get("stops", []):
                                    stop_name = stop.get("stop_name", "")
                                    timing_point = stop_name.startswith("M - ")
                                    stop_key = stop_name.replace("M - ", "").strip()

                                    for service in stop.get("services", []):
                                        service_name = service.get("service_name", "")
                                        for day_group in service.get("days", []):
                                            day_name = day_group.get("day")
                                            try:
                                                day_obj = dayType.objects.get(name__iexact=day_name)
                                            except dayType.DoesNotExist:
                                                self.stderr.write(self.style.WARNING(f"Missing dayType: {day_name}"))
                                                continue

                                            # Use day + direction as key to group times
                                            key = f"{day_name}-{is_inbound}"
                                            entry, created = timetableEntry.objects.get_or_create(
                                                route=route_obj,
                                                inbound=is_inbound,
                                                circular=False,
                                            )
                                            entry.day_type.add(day_obj)

                                            if not entry.stop_times:
                                                entry.stop_times = {}

                                            if stop_key not in entry.stop_times:
                                                entry.stop_times[stop_key] = {
                                                    "stopname": stop_key,
                                                    "timing_point": timing_point,
                                                    "times": []
                                                }

                                            entry.stop_times[stop_key]["times"] += day_group.get("times", [])
                                            entry.save()

                            except json.JSONDecodeError:
                                self.stderr.write(self.style.ERROR(f"Invalid JSON in {timetable_field} for route {route_obj.route_num}"))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
