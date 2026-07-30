import json
import math
import logging
from datetime import datetime, time, timedelta
from django.utils import timezone
from routes.models import routeStop, timetableEntry

logger = logging.getLogger(__name__)


def get_snapped_coords(rs):
    """
    Parse rs.snapped_route (JSON text) -> list[(lat,lng)]
    DB format is [[lng, lat], ...] so flip to (lat, lng).
    """
    if not rs.snapped_route:
        return None

    try:
        data = json.loads(rs.snapped_route)
        coords = []
        for pair in data:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                continue
            lng, lat = pair
            coords.append((float(lat), float(lng)))
        return coords if coords else None
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        logger.debug("Failed to parse snapped_route for routeStop %s: %s", getattr(rs, 'pk', None), e)
        return None


def calculate_heading(lat1, lng1, lat2, lng2):
    """
    Returns heading in degrees (0-360),
    where 0 = North, 90 = East, 180 = South, 270 = West.
    """
    if abs(lat1 - lat2) < 1e-9 and abs(lng1 - lng2) < 1e-9:
        return 0.0

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    d_lng = math.radians(lng2 - lng1)

    x = math.sin(d_lng) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - \
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(d_lng)

    heading = math.degrees(math.atan2(x, y))
    return (heading + 360) % 360


def get_route_coordinates(route_id, trip):
    """
    Determine which routeStop direction to use and return coordinates
    as a list of (lat, lng).
    """
    stops_qs = routeStop.objects.filter(route_id=route_id).order_by("id")
    if not stops_qs:
        return []

    if trip.trip_inbound is False:
        if stops_qs.count() >= 2:
            return extract_coords_from_routeStop(stops_qs[1])
        return extract_coords_from_routeStop(stops_qs[0])

    if trip.trip_inbound is True:
        return extract_coords_from_routeStop(stops_qs[0])

    # Fallback: auto-detect by matching trip_end_location against last stop name
    direction_candidates = []
    for rs in stops_qs:
        coords, last_stop_name = extract_coords_and_last_stop(rs)
        if coords:
            direction_candidates.append({
                "coords": coords,
                "last_stop": last_stop_name,
            })

    if not direction_candidates:
        return []

    trip_end_location = (trip.trip_end_location or "").lower().strip()
    for d in direction_candidates:
        ls = (d["last_stop"] or "").lower().strip()
        if trip_end_location and ls and trip_end_location in ls:
            return d["coords"]

    return direction_candidates[0]["coords"]


def extract_coords_from_routeStop(rs):
    snapped = get_snapped_coords(rs)
    if snapped:
        return snapped
    coords, _ = extract_coords_and_last_stop(rs)
    return coords or []


def extract_coords_and_last_stop(rs):
    snapped = get_snapped_coords(rs)
    if snapped:
        return snapped, None

    coords = []
    last_stop_name = None

    if not rs.stops or not isinstance(rs.stops, list):
        return coords, None

    for stop in rs.stops:
        if not isinstance(stop, dict):
            continue

        sname = stop.get("stop") or stop.get("name") or stop.get("title")
        if sname:
            last_stop_name = sname

        cords = stop.get("cords") or stop.get("coords")
        if cords:
            try:
                lat_str, lng_str = cords.split(",")
                coords.append((float(lat_str.strip()), float(lng_str.strip())))
                continue
            except (ValueError, AttributeError):
                pass

        lat = stop.get("lat") or stop.get("latitude")
        lng = stop.get("lng") or stop.get("longitude") or stop.get("long")
        if lat is not None and lng is not None:
            try:
                coords.append((float(lat), float(lng)))
                continue
            except (ValueError, TypeError):
                pass

    return coords, last_stop_name


def get_progress(trip):
    """Simple time-based progress (0..1) along a trip. Fallback when no timetable."""
    now = timezone.now()
    start = trip.trip_start_at
    end = trip.trip_end_at
    duration = (end - start).total_seconds()
    elapsed = (now - start).total_seconds()
    if elapsed <= 0:
        return 0.0
    if elapsed >= duration:
        return 1.0
    return elapsed / duration


def interpolate(coords, progress):
    """Linear interpolation along a coordinate list at a given progress (0..1)."""
    if not coords:
        return (None, None, None)
    if len(coords) == 1:
        return coords[0][0], coords[0][1], 0

    total_segments = len(coords) - 1
    segment_float = progress * total_segments
    seg_index = int(segment_float)

    if seg_index >= total_segments:
        return coords[-1][0], coords[-1][1], total_segments - 1

    seg_progress = segment_float - seg_index
    (lat1, lng1) = coords[seg_index]
    (lat2, lng2) = coords[seg_index + 1]

    lat = lat1 + (lat2 - lat1) * seg_progress
    lng = lng1 + (lng2 - lng1) * seg_progress

    return lat, lng, seg_index


# =========================================================================
#  NEW: Timetable-aware simulation
# =========================================================================

def time_str_to_minutes(t_str):
    """Convert 'HH:MM' or 'HH:MM:SS' to total minutes since midnight."""
    parts = t_str.strip().split(":")
    if len(parts) >= 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0


def parse_timetable_stop_times(entry):
    """Parse timetableEntry.stop_times into a plain dict."""
    data = entry.stop_times
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return {}
    if not isinstance(data, dict):
        return {}
    return data


def get_route_stop_for_trip(trip):
    """Return the routeStop that matches a trip's direction."""
    stops_qs = routeStop.objects.filter(route_id=trip.trip_route_id).order_by("id")
    if not stops_qs:
        return None

    if trip.trip_inbound is False:
        count = stops_qs.count()
        return stops_qs[1] if count >= 2 else stops_qs[0]
    return stops_qs[0]


def get_stop_coords_map(route_stop):
    """
    Build a dict mapping normalized stop names to (lat, lng) from a routeStop.
    """
    coords_map = {}
    if not route_stop or not isinstance(route_stop.stops, list):
        return coords_map

    for stop in route_stop.stops:
        if not isinstance(stop, dict):
            continue

        name = (
            stop.get("stop")
            or stop.get("name")
            or stop.get("title")
            or stop.get("stopname")
            or ""
        )
        if not name:
            continue

        lat = None
        lng = None

        cords = stop.get("cords") or stop.get("coords")
        if cords and isinstance(cords, str):
            try:
                lat_str, lng_str = cords.split(",")
                lat = float(lat_str.strip())
                lng = float(lng_str.strip())
            except (ValueError, AttributeError):
                pass

        if lat is None:
            lat = stop.get("lat") or stop.get("latitude")
            lng = stop.get("lng") or stop.get("longitude") or stop.get("long")
            if lat is not None and lng is not None:
                try:
                    lat = float(lat)
                    lng = float(lng)
                except (ValueError, TypeError):
                    continue

        if lat is not None and lng is not None:
            coords_map[name.lower().strip()] = (lat, lng)

    return coords_map


def find_matching_timetable_and_column(trip):
    """
    Find the timetableEntry + column index matching a trip.

    Strategy:
      1. Filter timetable entries by route ID + active.
      2. Narrow by inbound flag if the trip has one.
      3. For each timetable, inspect the first stop's "times" list.
      4. Pick the column whose start time matches trip.trip_start_at
         (within a 2-minute tolerance).

    Returns (timetable_entry, column_index) or None.
    """
    if not trip.trip_route_id:
        return None

    entries = timetableEntry.objects.filter(route_id=trip.trip_route_id, active=True)
    if not entries.exists():
        return None

    if trip.trip_inbound is True:
        direction_filtered = entries.filter(inbound=True)
        if direction_filtered.exists():
            entries = direction_filtered
    elif trip.trip_inbound is False:
        direction_filtered = entries.filter(inbound=False)
        if direction_filtered.exists():
            entries = direction_filtered

    trip_start_minutes = trip.trip_start_at.hour * 60 + trip.trip_start_at.minute

    best_match = None
    best_score = float("inf")

    for entry in entries:
        stop_times_data = parse_timetable_stop_times(entry)
        if not stop_times_data:
            continue

        sorted_keys = sorted(
            stop_times_data.keys(),
            key=lambda k: stop_times_data[k].get("order", 0),
        )
        if not sorted_keys:
            continue

        first_stop = stop_times_data[sorted_keys[0]]
        times = first_stop.get("times", [])

        for idx, t in enumerate(times):
            t_minutes = time_str_to_minutes(t)
            diff = abs(t_minutes - trip_start_minutes)
            if diff < best_score:
                best_score = diff
                best_match = (entry, idx)

    if best_match and best_score <= 2:
        return best_match
    return None


def calculate_timetable_position(trip):
    """
    Use the timetable to figure out exactly where a vehicle should be
    on its trip right now.

    Returns a dict:
        {
            "lat": float,
            "lng": float,
            "heading": float,
            "delay": float,       # minutes (positive = late, negative = early)
            "progress": float,    # 0..1
        }
    or None when the timetable can't be used.
    """
    # --- 1. Find matching timetable entry + column index ---
    match = find_matching_timetable_and_column(trip)
    if not match:
        return None

    entry, col_idx = match

    stop_times_data = parse_timetable_stop_times(entry)
    sorted_keys = sorted(
        stop_times_data.keys(),
        key=lambda k: stop_times_data[k].get("order", 0),
    )
    if len(sorted_keys) < 2:
        return None

    # --- 2. Resolve datetimes for each stop in this column ---
    trip_date = trip.trip_start_at.date()
    first_minutes = None
    stop_dts = []  # list of (stop_key, datetime, stop_data)

    prev_minutes = None
    day_offset = 0
    for key in sorted_keys:
        sd = stop_times_data[key]
        times = sd.get("times", [])
        if col_idx >= len(times):
            return None
        t_minutes = time_str_to_minutes(times[col_idx])

        if prev_minutes is not None and t_minutes < prev_minutes:
            day_offset += 1
        prev_minutes = t_minutes

        stop_date = trip_date + timedelta(days=day_offset)
        stop_dt = timezone.make_aware(
            datetime.combine(stop_date, time(hour=t_minutes // 60, minute=t_minutes % 60))
        )
        stop_dts.append((key, stop_dt, sd))

        if first_minutes is None:
            first_minutes = t_minutes

    # --- 3. Figure out which two stops bracket "now" ---
    now = timezone.now()

    if now <= stop_dts[0][1]:
        # Before first stop
        delay_seconds = (now - stop_dts[0][1]).total_seconds()
        pos = _lookup_stop_position(trip, stop_dts[0][0])
        if pos is None:
            return None
        return {
            "lat": pos[0],
            "lng": pos[1],
            "heading": 0.0,
            "delay": delay_seconds / 60.0,
            "progress": 0.0,
        }

    if now >= stop_dts[-1][1]:
        # After last stop
        delay_seconds = (now - stop_dts[-1][1]).total_seconds()
        pos = _lookup_stop_position(trip, stop_dts[-1][0])
        if pos is None:
            return None
        return {
            "lat": pos[0],
            "lng": pos[1],
            "heading": 0.0,
            "delay": delay_seconds / 60.0,
            "progress": 1.0,
        }

    for i in range(len(stop_dts) - 1):
        prev_key, prev_dt, prev_sd = stop_dts[i]
        next_key, next_dt, next_sd = stop_dts[i + 1]

        if prev_dt <= now <= next_dt:
            # Vehicle is between these two stops
            segment_duration = (next_dt - prev_dt).total_seconds()
            segment_elapsed = (now - prev_dt).total_seconds()
            segment_progress = (
                segment_elapsed / segment_duration if segment_duration > 0 else 0
            )

            # Overall progress (spread stops evenly across the route)
            total_stops = len(stop_dts)
            overall_progress = (i + segment_progress) / (total_stops - 1)

            # Get coordinates for the two stops
            pos_a = _lookup_stop_position(trip, prev_key)
            pos_b = _lookup_stop_position(trip, next_key)

            if pos_a is None or pos_b is None:
                return None

            # Linear interpolation between the two stop coordinates
            lat = pos_a[0] + (pos_b[0] - pos_a[0]) * segment_progress
            lng = pos_a[1] + (pos_b[1] - pos_a[1]) * segment_progress

            heading = calculate_heading(pos_a[0], pos_a[1], pos_b[0], pos_b[1])

            # Delay: how far is the vehicle from the schedule?
            scheduled_time_at_progress = prev_dt + timedelta(
                seconds=segment_duration * segment_progress
            )
            delay_seconds = (now - scheduled_time_at_progress).total_seconds()

            return {
                "lat": lat,
                "lng": lng,
                "heading": heading,
                "delay": delay_seconds / 60.0,
                "progress": overall_progress,
            }

    return None


# Module-level LRU cache for stop-coords lookups (cleared each run)
_stop_coords_cache = {}


def _lookup_stop_position(trip, stop_key):
    """
    Find the lat/lng for a timetable stop by its key.
    The key looks like 'Stop Name_idx_0' — we strip the '_idx_N' suffix
    to get the raw stop name, then match against routeStop.stops.
    """
    cache_key = (trip.trip_route_id, trip.trip_inbound, stop_key)
    if cache_key in _stop_coords_cache:
        return _stop_coords_cache[cache_key]

    # Strip trailing '_idx_N' from the key to get the raw stop name
    raw_name = stop_key.rsplit("_idx_", 1)[0] if "_idx_" in stop_key else stop_key

    rs = get_route_stop_for_trip(trip)
    if rs is None:
        _stop_coords_cache[cache_key] = None
        return None

    coords_map = get_stop_coords_map(rs)

    # Direct lookup
    result = coords_map.get(raw_name.lower().strip())
    if result is not None:
        _stop_coords_cache[cache_key] = result
        return result

    # Try matching raw_name contained in coords_map keys
    for cs_name, cs_coords in coords_map.items():
        if raw_name.lower().strip() in cs_name:
            _stop_coords_cache[cache_key] = cs_coords
            return cs_coords

    _stop_coords_cache[cache_key] = None
    return None


def clear_sim_cache():
    """Reset the internal stop-coords cache (call at the start of each run)."""
    _stop_coords_cache.clear()
