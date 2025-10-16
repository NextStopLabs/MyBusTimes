import json
from django.core.management.base import BaseCommand
from routes.models import timetableEntry

class Command(BaseCommand):
    help = "Migrate existing stop_times JSON to new _idx_ID format"

    def handle(self, *args, **options):
        entries = timetableEntry.objects.all()
        for entry in entries:
            if not entry.stop_times:
                continue

            try:
                old_stop_times = json.loads(entry.stop_times)
            except json.JSONDecodeError:
                self.stdout.write(self.style.WARNING(f"Skipping entry {entry.id} - invalid JSON"))
                continue

            new_stop_times = {}
            for idx, (stop_name, stop_data) in enumerate(old_stop_times.items()):
                key = f"{stop_name}_idx_{idx}"
                new_stop_times[key] = {
                    "stopname": stop_data.get("stopname", stop_name),
                    "timing_point": stop_data.get("timing_point", False),
                    "times": stop_data.get("times", [])
                }

            entry.stop_times = json.dumps(new_stop_times)
            entry.save()
            self.stdout.write(self.style.SUCCESS(f"Migrated timetableEntry {entry.id}"))

        self.stdout.write(self.style.SUCCESS("All entries migrated successfully."))
