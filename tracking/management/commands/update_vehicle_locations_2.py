import bisect
import math

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from tracking.models import ActiveTrip
from fleet.models import fleet as Fleet


# Fleet updates here only touch small scalar fields (no JSON), so a much
# larger batch than the precompute command's JSON-heavy inserts is safe --
# this just cuts the number of round-trip UPDATE statements.
BULK_UPDATE_BATCH_SIZE = 2000

# Stream ActiveTrip rows from the DB in chunks instead of materializing
# all of them (each carrying a track_route/track_timing JSON blob) in
# memory at once. Keeps peak memory bounded at scale.
ACTIVE_TRIP_CHUNK_SIZE = 2000

FLEET_UPDATE_FIELDS = ("sim_lat", "sim_lon", "sim_heading", "current_trip_id", "updated_at")


class Command(BaseCommand):
    help = "Update vehicle sim position (lat/lon/heading) and current_trip from ActiveTrip data"

    def handle(self, *args, **options):
        now = timezone.now()
        now_ts = now.timestamp()  # computed once, not per trip

        active_trip_vehicle_ids = ActiveTrip.objects.values("vehicle_id")

        vehicles_qs = Fleet.objects.filter(
            Q(id__in=active_trip_vehicle_ids) | Q(current_trip__isnull=False)
        ).only("id", "sim_lat", "sim_lon", "sim_heading", "current_trip_id", "updated_at")

        vehicles_by_id = {v.id: v for v in vehicles_qs}

        if not vehicles_by_id:
            self.stdout.write("No active trips and nothing to clear. Nothing to do.")
            return

        to_update = []
        positioned = 0
        skipped = 0
        active_vehicle_ids = set()

        active_trips = ActiveTrip.objects.only(
            "trip_id", "vehicle_id", "start_datetime", "end_datetime",
            "track_route", "track_timing",
        ).iterator(chunk_size=ACTIVE_TRIP_CHUNK_SIZE)

        total = 0
        for active_trip in active_trips:
            total += 1
            active_vehicle_ids.add(active_trip.vehicle_id)

            vehicle = vehicles_by_id.get(active_trip.vehicle_id)
            if vehicle is None:
                continue

            position = self.compute_position(active_trip, now, now_ts)
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

        # Anything fetched above that isn't on an active trip this run but
        # still has a current_trip set is stale -- clear it.
        cleared = 0
        for vehicle_id, vehicle in vehicles_by_id.items():
            if vehicle_id in active_vehicle_ids:
                continue
            if vehicle.current_trip_id is None:
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
                f"of {total} active trip(s)."
            )
        )

    # ------------------------------------------------------------------
    # Position: real distance-along-route, timed against actual
    # scheduled stop times -- not a naive start/end time fraction.
    # ------------------------------------------------------------------
    def compute_position(self, active_trip, now, now_ts):
        track_route = active_trip.track_route
        track_timing = active_trip.track_timing

        coords = (track_route or {}).get("coordinates")
        cumulative = (track_route or {}).get("cumulative_distances")
        stop_markers = (track_route or {}).get("stops")

        if not coords or len(coords) < 2 or not cumulative or not stop_markers or not track_timing:
            return self._fallback_time_position(active_trip, now, coords)

        # (distance_m, epoch_seconds) pairs -- epoch already precomputed
        # at precompute time, so this is pure dict/list access, no
        # parsing, no datetime object construction.
        timeline = []
        for marker in stop_markers:
            timing_entry = track_timing.get(marker["name"])
            if not timing_entry:
                continue
            ts = timing_entry.get("scheduled_at_ts")
            if ts is None:
                # older row precomputed before scheduled_at_ts existed --
                # fall back to parsing just this once.
                scheduled_at = timing_entry.get("scheduled_at")
                if not scheduled_at:
                    continue
                try:
                    from datetime import datetime
                    ts = datetime.fromisoformat(scheduled_at).timestamp()
                except ValueError:
                    continue
            timeline.append((marker["distance_m"], ts))

        if len(timeline) < 2:
            return self._fallback_time_position(active_trip, now, coords)

        timeline.sort(key=lambda pair: pair[1])

        if now_ts <= timeline[0][1]:
            target_distance = timeline[0][0]
        elif now_ts >= timeline[-1][1]:
            target_distance = timeline[-1][0]
        else:
            target_distance = None
            for (d0, t0), (d1, t1) in zip(timeline, timeline[1:]):
                if t0 <= now_ts <= t1:
                    total_seconds = t1 - t0
                    frac = 0.0 if total_seconds <= 0 else (now_ts - t0) / total_seconds
                    target_distance = d0 + frac * (d1 - d0)
                    break
            if target_distance is None:
                return self._fallback_time_position(active_trip, now, coords)

        return self._position_at_distance(coords, cumulative, target_distance)

    def _position_at_distance(self, coords, cumulative, target_distance):
        target_distance = max(0.0, min(cumulative[-1], target_distance))

        # O(log n) instead of a linear scan -- matters at this scale,
        # repeated for every trip on every tick.
        index = bisect.bisect_right(cumulative, target_distance) - 1
        index = max(0, min(len(cumulative) - 2, index))

        d0, d1 = cumulative[index], cumulative[index + 1]
        seg_len = d1 - d0
        seg_frac = 0.0 if seg_len <= 0 else (target_distance - d0) / seg_len

        lon1, lat1 = coords[index]
        lon2, lat2 = coords[index + 1]

        lat = lat1 + (lat2 - lat1) * seg_frac
        lon = lon1 + (lon2 - lon1) * seg_frac
        heading = self._bearing(lat1, lon1, lat2, lon2)

        return lat, lon, heading

    def _fallback_time_position(self, active_trip, now, coords):
        if not coords or len(coords) < 2:
            return None

        start = active_trip.start_datetime
        end = active_trip.end_datetime
        if not start:
            return None

        if not end or end <= start:
            progress = 0.0
        else:
            progress = (now - start).total_seconds() / (end - start).total_seconds()
        progress = max(0.0, min(1.0, progress))

        index_float = progress * (len(coords) - 1)
        index = max(0, min(len(coords) - 2, int(index_float)))
        seg_frac = index_float - index

        lon1, lat1 = coords[index]
        lon2, lat2 = coords[index + 1]
        lat = lat1 + (lat2 - lat1) * seg_frac
        lon = lon1 + (lon2 - lon1) * seg_frac
        heading = self._bearing(lat1, lon1, lat2, lon2)

        return lat, lon, heading

    def _bearing(self, lat1, lon1, lat2, lon2):
        lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
        delta_lon = math.radians(lon2 - lon1)

        x = math.sin(delta_lon) * math.cos(lat2_r)
        y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(delta_lon)

        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360