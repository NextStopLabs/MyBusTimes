import math
from datetime import datetime, timezone as dt_timezone

from django.core.management.base import BaseCommand
from django.utils import timezone

from tracking.models import ActiveTrip
from fleet.models import fleet as Fleet


# track_route/track_timing JSON can be large; keep writes batched so we
# never send one giant multi-row UPDATE (same lesson as the precompute
# command's bulk_create).
BULK_UPDATE_BATCH_SIZE = 200

FLEET_UPDATE_FIELDS = ("sim_lat", "sim_lon", "sim_heading", "current_trip_id", "updated_at")


class Command(BaseCommand):
    help = "Update vehicle sim position (lat/lon/heading) and current_trip from ActiveTrip data"

    def handle(self, *args, **options):
        now = timezone.now()

        active_trips = list(
            ActiveTrip.objects.only(
                "trip_id", "vehicle_id", "start_datetime", "end_datetime", "track_route"
            )
        )

        active_vehicle_ids = {at.vehicle_id for at in active_trips}

        # Pull every fleet row we might need to touch in one query: any
        # vehicle currently on an active trip, plus any vehicle that still
        # thinks it's on a trip but no longer has an ActiveTrip row (needs
        # clearing).
        stale_vehicle_ids = set(
            Fleet.objects.filter(current_trip__isnull=False)
            .exclude(id__in=active_vehicle_ids)
            .values_list("id", flat=True)
        )

        relevant_ids = active_vehicle_ids | stale_vehicle_ids
        if not relevant_ids:
            self.stdout.write("No active trips and nothing to clear. Nothing to do.")
            return

        vehicles_by_id = {
            v.id: v
            for v in Fleet.objects.filter(id__in=relevant_ids).only(
                "id", "sim_lat", "sim_lon", "sim_heading", "current_trip_id", "updated_at"
            )
        }

        to_update = []
        positioned = 0
        skipped = 0

        for active_trip in active_trips:
            vehicle = vehicles_by_id.get(active_trip.vehicle_id)
            if vehicle is None:
                # Vehicle referenced by the ActiveTrip no longer exists --
                # shouldn't happen (FK), but guard anyway.
                continue

            position = self.compute_position(active_trip, now)
            if position is None:
                skipped += 1
                continue

            lat, lon, heading = position
            vehicle.sim_lat = lat
            vehicle.sim_lon = lon
            vehicle.sim_heading = heading
            vehicle.current_trip_id = active_trip.trip_id
            vehicle.updated_at = now
            to_update.append(vehicle)
            positioned += 1

        # Clear vehicles that still reference a trip with no ActiveTrip
        # row left (trip ended/missed and was cleaned up already) so the
        # map doesn't keep showing a stale marker.
        cleared = 0
        for vehicle_id in stale_vehicle_ids:
            vehicle = vehicles_by_id.get(vehicle_id)
            if vehicle is None:
                continue
            vehicle.sim_lat = None
            vehicle.sim_lon = None
            vehicle.sim_heading = None
            vehicle.current_trip_id = None
            vehicle.updated_at = now
            to_update.append(vehicle)
            cleared += 1

        if to_update:
            Fleet.objects.bulk_update(
                to_update, FLEET_UPDATE_FIELDS, batch_size=BULK_UPDATE_BATCH_SIZE
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Positioned {positioned}, cleared {cleared}, skipped {skipped} "
                f"of {len(active_trips)} active trip(s)."
            )
        )

    # ------------------------------------------------------------------
    def compute_position(self, active_trip, now):
        """
        Linear time-based interpolation along track_route's coordinate
        list. Not geo-accurate (doesn't account for uneven point spacing
        along the polyline), but cheap and good enough for a live sim
        marker. Returns (lat, lon, heading_degrees) or None if we don't
        have enough data to place the vehicle.
        """
        coords = self._extract_coordinates(active_trip.track_route)
        if not coords or len(coords) < 2:
            return None

        start = active_trip.start_datetime
        end = active_trip.end_datetime
        if not start:
            return None

        if not end or end <= start:
            # No usable duration -- park it at the start of the route.
            progress = 0.0
        else:
            elapsed = (now - start).total_seconds()
            total = (end - start).total_seconds()
            progress = elapsed / total

        progress = max(0.0, min(1.0, progress))

        index_float = progress * (len(coords) - 1)
        index = int(index_float)
        index = max(0, min(len(coords) - 2, index))  # leave room for a "next" point

        lon1, lat1 = coords[index]
        lon2, lat2 = coords[index + 1]

        # sub-segment interpolation between the two bracketing points
        segment_progress = index_float - index
        lat = lat1 + (lat2 - lat1) * segment_progress
        lon = lon1 + (lon2 - lon1) * segment_progress

        heading = self._bearing(lat1, lon1, lat2, lon2)

        return lat, lon, heading

    def _extract_coordinates(self, track_route):
        """
        track_route is stored as {"type": "snapped"|"stops", "coordinates": [[lon, lat], ...]}
        """
        if not track_route:
            return None
        coords = track_route.get("coordinates")
        if not coords:
            return None
        return coords

    def _bearing(self, lat1, lon1, lat2, lon2):
        """Compass bearing in degrees (0-360) from point 1 to point 2."""
        lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
        delta_lon = math.radians(lon2 - lon1)

        x = math.sin(delta_lon) * math.cos(lat2_r)
        y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(delta_lon)

        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360