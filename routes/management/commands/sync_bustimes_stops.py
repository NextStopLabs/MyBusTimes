from django.core.management.base import BaseCommand
from routes.models import stop
from gameData.models import game
import requests

class Command(BaseCommand):
    help = 'Syncs stops from Bustimes API with pagination'

    def handle(self, *args, **kwargs):
        base_url = 'https://bustimes.org/api/stops/?limit=99999999'  # Replace with the actual API endpoint
        next_url = base_url  # Start with the base URL
        total_count = 0  # To keep track of the total number of stops synced

        try:
            while next_url:
                # Make the request to the current URL
                response = requests.get(next_url)
                response.raise_for_status()
                stops_data = response.json()

                # Check if 'results' is in the response data
                if 'results' not in stops_data:
                    self.stderr.write(self.style.ERROR('No results found in the API response'))
                    return

                stops = stops_data['results']  # Extract the list of stops

                print(f"Found {len(stops)} stops in this batch.")

                # Define or get a default game instance
                default_game, _ = game.objects.get_or_create(game_name='BustimesAPI')

                count = 0
                for s in stops:
                    # Only process if 'location' is available
                    location = s.get('location', [])
                    if location:
                        stop_name = s.get('long_name', 'Unknown stop')
                        latitude = location[0] if len(location) > 0 else None
                        longitude = location[1] if len(location) > 1 else None

                        stop.objects.create(
                            stop_name=stop_name,
                            latitude=latitude,
                            longitude=longitude,
                            game=default_game,
                            source='bustimes'
                        )
                        count += 1

                total_count += count
                print(f"Successfully synced {count} stops in this batch.")

                # Set the URL for the next page
                next_url = stops_data.get('next', None)  # This will be None if there are no more pages

            self.stdout.write(self.style.SUCCESS(f'Successfully synced a total of {total_count} stops from Bustimes'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error syncing stops: {e}'))
