import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from tracking.models import Trip
from fleet.models import fleet
from routes.models import route
from django.utils.timezone import make_aware

class Command(BaseCommand):
    help = 'Import Trip data from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to your trips CSV file')

    def handle(self, *args, **options):
        file_path = options['csv_file']

        try:
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    # Skip if TripID is missing or empty
                    trip_id = row.get('TripID', '').strip().upper()
                    if not trip_id or trip_id == 'NULL':
                        self.stderr.write(self.style.WARNING("Skipped row with empty TripID"))
                        continue

                    # Skip existing TripID
                    if Trip.objects.filter(trip_id=trip_id).exists():
                        self.stdout.write(self.style.WARNING(f"Skipped existing Trip ID: {trip_id}"))
                        continue

                    # Parse datetime
                    try:
                        start_time = make_aware(datetime.strptime(row['TripDateTime'], "%Y-%m-%d %H:%M:%S"))
                    except ValueError:
                        self.stderr.write(self.style.ERROR(f"Invalid date format: {row['TripDateTime']}"))
                        continue

                    # Get vehicle
                    vehicle_id = row.get('Vehicle_ID', '').strip()
                    if not vehicle_id or vehicle_id.upper() == 'NULL':
                        self.stderr.write(self.style.WARNING("Skipped row with invalid Vehicle_ID"))
                        continue
                    try:
                        vehicle = fleet.objects.get(id=int(vehicle_id))
                    except (fleet.DoesNotExist, ValueError):
                        self.stderr.write(self.style.WARNING(f"Vehicle not found or invalid: {vehicle_id}"))
                        continue

                    # Optional route
                    route_obj = None
                    route_id = row.get('RouteID', '').strip().upper()
                    if route_id and route_id != 'NULL':
                        try:
                            route_obj = route.objects.get(id=int(route_id))
                        except (route.DoesNotExist, ValueError):
                            self.stderr.write(self.style.WARNING(f"Route not found or invalid: {route_id}"))

                    # Create new trip
                    trip = Trip.objects.create(
                        trip_id=trip_id,
                        trip_vehicle=vehicle,
                        trip_route=route_obj,
                        trip_route_num=row.get('RouteNumber', None),
                        trip_start_location=None,
                        trip_end_location=row.get('EndDestination', None),
                        trip_start_at=start_time,
                        trip_end_at=None,
                        trip_ended=False if row.get('Missed') in [None, '', 'NULL'] else True,
                    )

                    self.stdout.write(self.style.SUCCESS(f"Created Trip ID {trip.trip_id}"))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
