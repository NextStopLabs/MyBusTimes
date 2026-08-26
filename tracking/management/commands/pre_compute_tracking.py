import json
import math
from collections import defaultdict
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import Q, F
from django.utils import timezone

from tracking.models import Trip, ActiveTrip
from routes.models import routeStop as RouteStop, timetableEntry as TimetableEntry


LOOKAHEAD_MINUTES = 5
# Grace period past a trip's scheduled end_datetime before we force-clear
# its ActiveTrip row, even if trip_ended/trip_missed never got set on the
# source Trip. Tune to how late trips realistically run.
OVERDUE_GRACE_MINUTES = 15
# Small buffer only to cover drift between scheduled runs (e.g. this
# command running every minute but firing a few seconds late) -- NOT a
# backfill window. Trips are precomputed once, shortly before they start;
# there's no reason to re-scan hours of history looking for them, and
# doing so just re-creates rows that cleanup only just deleted.
STARTED_GRACE_MINUTES = 2

# track_route/track_timing JSON blobs can be large (thousands of coords
# per route). Without a batch_size, bulk_create tries to send every
# surviving row as ONE giant multi-row INSERT, which can blow past
# statement_timeout or packet-size limits and kill the connection.
BULK_CREATE_BATCH_SIZE = 200

# Trip rows are wide; we only ever touch these fields, so pull just these
# off the wire instead of the whole row.
TRIP_FIELDS = (
    "trip_id",
    "trip_route_id",
    "trip_vehicle_id",
    "trip_start_at",
    "trip_end_at",
    "trip_start_location",
    "trip_end_location",
    "trip_inbound",
)


class Command(BaseCommand):
    help = "Cleanup finished ActiveTrip rows and precompute route/timing for trips starting soon"

    def handle(self, *args, **options):
        # Disable the web-tier statement_timeout (30s) for this bulk job which
        # can legitimately run longer when precomputing many trips.
        try:
            with connection.cursor() as cur:
                cur.execute("SET statement_timeout = 0")
        except Exception:
            pass

        self.cleanup_active_trips()
        self.precompute_upcoming_trips()

    # ------------------------------------------------------------------
    # Step 1: cleanup
    # ------------------------------------------------------------------
    def cleanup_active_trips(self):
        now = timezone.now()

        # a) trips that have finished or been marked missed
        finished_qs = ActiveTrip.objects.filter(
            Q(trip__trip_ended=True) | Q(trip__trip_missed=True)
        )
        finished_count, _ = finished_qs.delete()

        # b) trips whose source Trip changed since we precomputed them
        #    (route/driver/start time edited pre-departure) -- delete so
        #    step 2 below recomputes them fresh in this same run.
        stale_qs = ActiveTrip.objects.filter(trip__trip_updated_at__gt=F("computed_at"))
        stale_count, _ = stale_qs.delete()

        # c) safety net: don't rely solely on trip_ended/trip_missed ever
        #    getting flipped on the source Trip -- if the scheduled end
        #    time has clearly passed (with a grace buffer for lateness),
        #    clear it regardless. Without this, a trip whose trip_ended
        #    flag never gets set (missed driver action, stalled process,
        #    etc) leaves the vehicle showing stale route/timing forever.
        overdue_cutoff = now - timedelta(minutes=OVERDUE_GRACE_MINUTES)
        overdue_qs = ActiveTrip.objects.filter(end_datetime__lt=overdue_cutoff)
        overdue_count, _ = overdue_qs.delete()

        self.stdout.write(
            f"Cleanup: removed {finished_count} finished/missed, "
            f"{stale_count} stale, {overdue_count} overdue ActiveTrip row(s)"
        )

    # ------------------------------------------------------------------
    # Step 2: find upcoming trips and precompute
    # ------------------------------------------------------------------
    def precompute_upcoming_trips(self):
        now = timezone.now()
        cutoff_high = now + timedelta(minutes=LOOKAHEAD_MINUTES)
        # Only a small drift buffer, not a backfill window -- see comment
        # on STARTED_GRACE_MINUTES above.
        cutoff_low = now - timedelta(minutes=STARTED_GRACE_MINUTES)

        # Materialize up front (not .iterator()) -- we need the full set
        # in memory anyway to batch-fetch RouteStop/TimetableEntry, and
        # this is expected to be a small, bounded window of trips.
        trips = list(
            Trip.objects.filter(
                trip_start_at__isnull=False,
                trip_start_at__gte=cutoff_low,
                trip_start_at__lte=cutoff_high,
                trip_missed=False,
                trip_ended=False,
                activetrip__isnull=True,
            )
            # Extra safety net against the recreate-loop: even within the
            # narrow window above, don't precompute something whose
            # scheduled end has already passed -- trip_ended/trip_missed
            # not being set yet doesn't mean the trip is still relevant.
            .filter(Q(trip_end_at__isnull=True) | Q(trip_end_at__gt=now))
            .only(*TRIP_FIELDS)
            .order_by("trip_start_at")
        )

        if not trips:
            self.stdout.write("No upcoming trips to precompute.")
            return

        self.stdout.write(f"Precomputing {len(trips)} upcoming trip(s) ...")

        route_stops_by_key = self._fetch_route_stops(trips)
        timetable_entries_by_key = self._fetch_timetable_entries(trips)

        # Cache parsed stop_times JSON per timetable entry -- multiple
        # trips on the same route/direction/day share the same entry.
        stop_times_cache = {}
        # Cache built geometry per routeStop -- same route/direction
        # shares the same geometry for every trip.
        geometry_cache = {}

        to_create = []
        skipped = 0

        for trip in trips:
            key = (trip.trip_route_id, bool(trip.trip_inbound))

            route_stop = route_stops_by_key.get(key)
            if not route_stop:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Skipping trip {trip.trip_id}: no routeStop for "
                        f"route {trip.trip_route_id} inbound={trip.trip_inbound}"
                    )
                )
                skipped += 1
                continue

            timetable_entry = self._match_timetable_entry(
                timetable_entries_by_key.get(key, []), trip
            )
            if not timetable_entry:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Skipping trip {trip.trip_id}: no matching timetableEntry "
                        f"for route {trip.trip_route_id} on "
                        f"{trip.trip_start_at.date()} inbound={trip.trip_inbound}"
                    )
                )
                skipped += 1
                continue

            if timetable_entry.pk not in stop_times_cache:
                stop_times_cache[timetable_entry.pk] = self._parse_stop_times(timetable_entry)
            stop_times = stop_times_cache[timetable_entry.pk]

            timing = self.build_timing(trip, stop_times)
            if timing is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Skipping trip {trip.trip_id}: start "
                        f"{trip.trip_start_at.strftime('%H:%M')} not found in "
                        f"timetable stop_times"
                    )
                )
                skipped += 1
                continue

            if route_stop.pk not in geometry_cache:
                geometry_cache[route_stop.pk] = self.build_route_geometry(route_stop)
            snapped_route = geometry_cache[route_stop.pk]

            to_create.append(
                ActiveTrip(
                    trip_id=trip.trip_id,
                    vehicle_id=trip.trip_vehicle_id,
                    start_datetime=trip.trip_start_at,
                    end_datetime=trip.trip_end_at,
                    starts_at=trip.trip_start_location,
                    ends_at=trip.trip_end_location,
                    track_route=snapped_route,
                    track_timing=timing,
                )
            )

        created = 0
        if to_create:
            try:
                with transaction.atomic():
                    created_objs = ActiveTrip.objects.bulk_create(
                        to_create,
                        ignore_conflicts=True,
                        batch_size=BULK_CREATE_BATCH_SIZE,
                    )
                created = len(created_objs)
            except Exception as e:
                # FK race: Trip deleted between SELECT and bulk_create. Filter
                # to still-existing Trips and retry once.
                msg = str(e).lower()
                if "foreign key" in msg or "tracking_activetrip" in msg:
                    # Re-check which Trips still exist
                    try:
                        trip_ids = [a.trip_id for a in to_create]
                        existing = set(
                            Trip.objects.filter(trip_id__in=trip_ids).values_list(
                                "trip_id", flat=True
                            )
                        )
                        filtered = [a for a in to_create if a.trip_id in existing]
                        missing = len(to_create) - len(filtered)
                        if missing:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  FK race: {missing} trip(s) deleted before create, skipping them (e.g. {trip_ids[0] if trip_ids else '?'})"
                                )
                            )
                            skipped += missing
                        if filtered:
                            with transaction.atomic():
                                created_objs = ActiveTrip.objects.bulk_create(
                                    filtered,
                                    ignore_conflicts=True,
                                    batch_size=BULK_CREATE_BATCH_SIZE,
                                )
                            created = len(created_objs)
                    except Exception as inner_e:
                        self.stdout.write(
                            self.style.ERROR(f"  Retry after FK violation also failed: {inner_e}")
                        )
                        raise e from inner_e
                else:
                    raise

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {created}, skipped {skipped} of {len(trips)}."
            )
        )

    # ------------------------------------------------------------------
    # Batch fetch helpers -- one query each for the whole trip set,
    # instead of one query per trip.
    # ------------------------------------------------------------------
    def _fetch_route_stops(self, trips):
        route_ids = {t.trip_route_id for t in trips if t.trip_route_id}
        if not route_ids:
            return {}

        inbound_flags = {bool(t.trip_inbound) for t in trips}

        route_stops = RouteStop.objects.filter(
            route_id__in=route_ids, inbound__in=inbound_flags
        )
        return {(rs.route_id, rs.inbound): rs for rs in route_stops}

    def _fetch_timetable_entries(self, trips):
        route_ids = {t.trip_route_id for t in trips if t.trip_route_id}
        if not route_ids:
            return {}

        inbound_flags = {bool(t.trip_inbound) for t in trips}
        day_names = {
            timezone.localtime(t.trip_start_at).date().strftime("%A") for t in trips
        }

        entries = (
            TimetableEntry.objects.filter(
                route_id__in=route_ids,
                inbound__in=inbound_flags,
                active=True,
                day_type__name__in=day_names,
            )
            .prefetch_related("day_type")
            .distinct()
        )

        by_key = defaultdict(list)
        for entry in entries:
            # keep the resolved day-type names alongside the entry so
            # per-trip matching below is pure in-memory, no more queries
            entry_day_names = {d.name for d in entry.day_type.all()}
            by_key[(entry.route_id, entry.inbound)].append((entry, entry_day_names))
        return by_key

    def _match_timetable_entry(self, entries_for_key, trip):
        trip_date = timezone.localtime(trip.trip_start_at).date()
        day_name = trip_date.strftime("%A")

        for entry, entry_day_names in entries_for_key:
            if day_name not in entry_day_names:
                continue
            if entry.start_date and entry.start_date > trip_date:
                continue
            if entry.end_date and entry.end_date < trip_date:
                continue
            return entry
        return None

    # ------------------------------------------------------------------
    # Data assembly (pure Python, no queries)
    # ------------------------------------------------------------------
    def _parse_stop_times(self, timetable_entry):
        """
        stop_times is a JSON-encoded dict of:
            { stopname: {"times": [...], "departure_times": [...], ...}, ... }
        Parsed once per timetableEntry and cached by the caller.
        """
        try:
            stop_times = json.loads(timetable_entry.stop_times)
        except (TypeError, ValueError):
            return None
        return stop_times or None

    def build_timing(self, trip, stop_times):
        """
        Each stop's "times" list is column-aligned across every trip that
        runs that day (e.g. index 3 == the 12:50 departure at every stop).
        We find which column matches THIS trip's scheduled start time at
        the first stop, then read that same column for every other stop.
        """
        if not stop_times:
            return None

        stop_names = list(stop_times.keys())
        first_stop = stop_times[stop_names[0]]
        times_col = first_stop.get("times") or first_stop.get("departure_times") or []

        trip_time_str = timezone.localtime(trip.trip_start_at).strftime("%H:%M")
        try:
            col_index = times_col.index(trip_time_str)
        except ValueError:
            return None

        trip_date = timezone.localtime(trip.trip_start_at).date()
        timing = {}
        for stop_name, stop_data in stop_times.items():
            times_list = stop_data.get("times") or stop_data.get("departure_times") or []
            if col_index >= len(times_list):
                continue
            time_str = times_list[col_index]
            if not time_str:
                continue  # stop not served on this particular run (short-working)
            try:
                hh, mm = time_str.split(":")
                dt = timezone.make_aware(
                    datetime.combine(trip_date, datetime.min.time()).replace(
                        hour=int(hh), minute=int(mm)
                    ),
                    timezone.get_current_timezone(),
                )
            except ValueError:
                continue
            timing[stop_name] = {
                "timing_point": stop_data.get("timing_point", False),
                "scheduled_at": dt.isoformat(),
                # Epoch seconds, computed once here instead of being
                # re-parsed from the ISO string on every location-worker
                # tick for the lifetime of the trip.
                "scheduled_at_ts": dt.timestamp(),
            }

        return timing or None

    def build_route_geometry(self, route_stop):
        """
        Prefer the pre-snapped road-following polyline if present
        (routeStop.snapped_route -- JSON list of [lon, lat] pairs from a
        routing engine). Fall back to a straight line built from the stop
        coordinates in routeStop.stops if no snapped route exists.

        Also computes, once per (route, direction):
          - cumulative_distances: running distance in metres along
            `coordinates`, same length as `coordinates`.
          - stops: each named stop mapped to the coordinate index (and
            therefore distance-along-route) closest to it.

        This lets the location-update worker place a vehicle by actual
        distance travelled along the road, not just by raw polyline point
        index or a naive time/duration fraction.
        """
        stops = route_stop.stops or []

        coords = None
        route_type = "stops"
        if route_stop.snapped_route:
            try:
                parsed = json.loads(route_stop.snapped_route)
                if parsed:
                    coords = parsed
                    route_type = "snapped"
            except (TypeError, ValueError):
                pass

        if coords is None:
            # Fallback: coordinates ARE the stops, in order, one-to-one.
            coords = []
            for stop in stops:
                cords = stop.get("cords")
                if not cords:
                    continue
                try:
                    lat_str, lon_str = cords.split(",")
                    coords.append([float(lon_str), float(lat_str)])
                except ValueError:
                    continue
            route_type = "stops"

        if not coords:
            return {"type": route_type, "coordinates": [], "cumulative_distances": [], "stops": []}

        cumulative = self._cumulative_distances(coords)

        stop_markers = []
        if route_type == "stops":
            # coords were built directly from `stops` above, in the same
            # order and 1:1 -- no nearest-point search needed.
            for idx, stop in enumerate(stops):
                if idx >= len(coords):
                    break
                stop_markers.append(
                    {
                        "name": stop.get("stopname") or stop.get("stop"),
                        "coord_index": idx,
                        "distance_m": cumulative[idx],
                    }
                )
        else:
            # snapped polyline doesn't know about named stops -- find the
            # nearest polyline point to each stop's own coordinates.
            for stop in stops:
                cords = stop.get("cords")
                name = stop.get("stopname") or stop.get("stop")
                if not cords or not name:
                    continue
                try:
                    lat_str, lon_str = cords.split(",")
                    lat, lon = float(lat_str), float(lon_str)
                except ValueError:
                    continue
                idx = self._nearest_coord_index(lat, lon, coords)
                if idx is None:
                    continue
                stop_markers.append(
                    {"name": name, "coord_index": idx, "distance_m": cumulative[idx]}
                )

        return {
            "type": route_type,
            "coordinates": coords,
            "cumulative_distances": cumulative,
            "stops": stop_markers,
        }

    @staticmethod
    def _haversine_m(lat1, lon1, lat2, lon2):
        """Great-circle distance in metres between two lat/lon points."""
        R = 6371000.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)
        a = (
            math.sin(d_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
        )
        return 2 * R * math.asin(min(1.0, math.sqrt(a)))

    def _cumulative_distances(self, coords):
        """coords is [[lon, lat], ...] -- returns running distance in metres."""
        cumulative = [0.0]
        for i in range(1, len(coords)):
            lon1, lat1 = coords[i - 1]
            lon2, lat2 = coords[i]
            cumulative.append(cumulative[-1] + self._haversine_m(lat1, lon1, lat2, lon2))
        return cumulative

    def _nearest_coord_index(self, lat, lon, coords):
        """Index of the coordinate in `coords` ([lon, lat] pairs) closest to (lat, lon)."""
        best_index = None
        best_distance = None
        for i, (c_lon, c_lat) in enumerate(coords):
            d = self._haversine_m(lat, lon, c_lat, c_lon)
            if best_distance is None or d < best_distance:
                best_distance = d
                best_index = i
        return best_index