import requests
from django.core.management.base import BaseCommand
from routes.models import stop  # Replace with your app and model if different


class Command(BaseCommand):
    help = "Import bus stops from bustimes.org API"

    def handle(self, *args, **kwargs):
        url = "https://bustimes.org/api/stops/?active=true"
        created_count = 0
        skipped_count = 0

        while url:
            self.stdout.write(f"Fetching: {url}")
            response = requests.get(url)
            data = response.json()

            for item in data.get("results", []):
                name = item.get("long_name")
                location = item.get("location")

                if location and len(location) == 2:
                    longitude, latitude = location
                    obj, created = stop.objects.get_or_create(
                        stop_name=name,
                        latitude=latitude,
                        longitude=longitude
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(f"Added: {name}")
                    else:
                        skipped_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Skipped stop with missing location: {name}"))

            url = data.get("next")

        self.stdout.write(self.style.SUCCESS(
            f"Done! Created {created_count} new stops, skipped {skipped_count}."
        ))
