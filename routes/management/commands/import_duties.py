import csv
import re
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from routes.models import duty, dutyTrip, dayType
from fleet.models import MBTOperator


class Command(BaseCommand):
    help = "Import old duties and trips from CSV"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str)

    def handle(self, *args, **options):
        file_path = options["csv_file"]
        default_days = dayType.objects.all()  # Adjust this if needed

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                operator_code = row["OperatorCode"].strip()
                routes_raw = row["Routes"].strip()
                duty_number = row["DutyNumber"].strip()

                try:
                    operator = MBTOperator.objects.get(operator_code=operator_code)
                except MBTOperator.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Operator not found: {operator_code}"))
                    continue

                # Create the duty
                duty_obj = duty.objects.create(
                    duty_name=duty_number,
                    duty_operator=operator,
                    board_type='duty',
                )
                duty_obj.duty_day.set(default_days)

                # Parse trips
                entries = re.split(r",\s*(?=\d{1,2}:\d{2})|,\s*B\s*-\s*", routes_raw)

                for entry in entries:
                    entry = entry.strip()
                    if not entry:
                        continue

                    # Check for break
                    if entry.startswith("B -") or re.match(r"^\d{1,2}:\d{2} - \d{1,2}:\d{2}$", entry):
                        # You can skip or handle breaks differently
                        continue

                    match = re.match(r"(?P<time>\d{1,2}:\d{2})\s*-\s*(?P<route>\S+)\s*-\s*(?P<location>.+)", entry)
                    if match:
                        try:
                            time_obj = datetime.strptime(match.group("time"), "%H:%M").time()
                        except ValueError:
                            continue

                        route = match.group("route").strip()
                        location = match.group("location").strip()

                        # We'll use a fake 30-minute duration if no end time is known
                        end_time = (datetime.combine(datetime.today(), time_obj) + timedelta(minutes=30)).time()

                        dutyTrip.objects.create(
                            duty=duty_obj,
                            route=route,
                            start_time=time_obj,
                            end_time=end_time,
                            start_at=location,
                            end_at=None,
                        )
                    else:
                        self.stdout.write(self.style.WARNING(f"Unparsed trip line: {entry}"))

                self.stdout.write(self.style.SUCCESS(f"Imported duty {duty_number}"))

