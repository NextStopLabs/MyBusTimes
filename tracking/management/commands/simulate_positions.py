from django.core.management.base import BaseCommand
from django.utils import timezone
from tracking.models import Trip
from fleet.models import fleet

from tracking.utils import (
    get_route_coordinates,
    get_progress,
    interpolate,
    calculate_heading,
    calculate_timetable_position,
    clear_sim_cache,
)


class Command(BaseCommand):
    help = "Simulate vehicle positions for all active trips (timetable-aware)"

    def handle(self, *args, **kwargs):
        now = timezone.now()
        clear_sim_cache()

        # -----------------------------------------------------------------
        # 1. Get active trips (start <= now <= end, not missed)
        # -----------------------------------------------------------------
        active_trips = (
            Trip.objects.filter(
                trip_start_at__lte=now,
                trip_end_at__gte=now,
                trip_missed=False,
            )
            .select_related("trip_vehicle", "trip_vehicle__operator", "trip_route")
        )

        if not active_trips.exists():
            self.stdout.write("No active trips found.")
            return

        # -----------------------------------------------------------------
        # 2. Clear sim data for vehicles whose trips ended > 15 min ago
        # -----------------------------------------------------------------
        fleet.objects.filter(
            current_trip__trip_end_at__lt=now - timezone.timedelta(minutes=15)
        ).update(
            sim_lat=None,
            sim_lon=None,
            sim_heading=None,
            sim_delay=None,
            current_trip=None,
            updated_at=None,
        )

        self.stdout.write("Cleared old trip positions.")

        # -----------------------------------------------------------------
        # 3. Process each active trip
        # -----------------------------------------------------------------
        timetable_hits = 0
        fallback_hits = 0
        skipped = 0

        for trip in active_trips:
            vehicle = trip.trip_vehicle
            if not vehicle or not trip.trip_route:
                skipped += 1
                continue

            lat = None
            lng = None
            heading = 0.0
            delay = 0.0

            # --- 3a. Try timetable-aware positioning first ---
            tt_result = calculate_timetable_position(trip)

            if tt_result is not None:
                lat = tt_result["lat"]
                lng = tt_result["lng"]
                heading = tt_result["heading"]
                delay = round(tt_result["delay"], 1)
                timetable_hits += 1
            else:
                # --- 3b. Fallback: simple time-based interpolation ---
                coords = get_route_coordinates(trip.trip_route_id, trip)
                if not coords:
                    skipped += 1
                    continue

                progress = get_progress(trip)

                if progress >= 1.0:
                    lat, lng = coords[-1]
                    heading = vehicle.sim_heading or 0.0
                else:
                    lat, lng, seg_index = interpolate(coords, progress)
                    if lat is None or lng is None:
                        skipped += 1
                        continue
                    # Heading: use next point along the route
                    next_idx = min(seg_index + 1, len(coords) - 1) if seg_index is not None else 0
                    heading = calculate_heading(lat, lng, coords[next_idx][0], coords[next_idx][1])

                delay = 0.0
                fallback_hits += 1

            # --- Write back to vehicle ---
            vehicle.sim_lat = lat
            vehicle.sim_lon = lng
            vehicle.sim_heading = heading
            vehicle.sim_delay = delay
            vehicle.current_trip = trip
            vehicle.updated_at = now

            vehicle.save(
                update_fields=[
                    "sim_lat",
                    "sim_lon",
                    "sim_heading",
                    "sim_delay",
                    "current_trip",
                    "updated_at",
                ]
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Simulation complete. "
                f"Timetable-based: {timetable_hits}, "
                f"Fallback (time-based): {fallback_hits}, "
                f"Skipped: {skipped}, "
                f"Total active trips: {active_trips.count()}"
            )
        )
