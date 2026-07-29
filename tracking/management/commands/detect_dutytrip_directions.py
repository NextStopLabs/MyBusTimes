# yourapp/management/commands/detect_dutytrip_directions.py
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

import re
import json
from math import ceil

# Adjust these imports to match your app names if they're different
from routes.models import dutyTrip, route, routeStop

# ---------- Helpers ----------

def normalize_location(text):
    """
    Normalize free-text stop or destination names for fuzzy matching.
    
    Performs normalization such as lowercasing, removing parenthetical content, punctuation, common noise words (e.g. "stand", "bay", "platform", "near"), standalone numbers, and collapsing whitespace.
    
    Parameters:
        text: The free-text stop or destination value to normalize (may be any object; it will be converted to a string).
    
    Returns:
        The normalized string (empty string for falsy input).
    """
    if not text:
        return ""

    # ensure str
    text = str(text)

    # remove parenthetical content like "(Stand 1)"
    text = re.sub(r"\(.*?\)", " ", text)

    # lowercase
    text = text.lower()

    # remove punctuation except for spaces
    text = re.sub(r"[^\w\s]", " ", text)

    # remove noise words and trailing numbers (stand, bay, platform, stop, adjacent, opposite, near)
    noise_pattern = r"\b(stand|bay|platform|stop|adjacent|opposite|near|outside|outside of|next to|by|at|opp|adj)\b"
    text = re.sub(noise_pattern, " ", text)

    # remove standalone numbers
    text = re.sub(r"\b\d+\b", " ", text)

    # collapse multiple spaces
    text = " ".join(text.split())

    return text


def token_overlap_match(a, b, min_common_tokens=1):
    """
    Determine whether two location strings have sufficient token overlap to be considered a match.
    
    Performs normalization of inputs, treats substring containment as a high-confidence match, and otherwise requires at least `min_common_tokens` tokens in common or at least half of the smaller token set.
    
    Parameters:
        a (str): First location string to compare.
        b (str): Second location string to compare.
        min_common_tokens (int): Minimum number of shared tokens required to consider a match.
    
    Returns:
        bool: `True` if the inputs match according to the overlap rules, `False` otherwise.
    """
    if not a or not b:
        return False

    a_n = normalize_location(a)
    b_n = normalize_location(b)

    if not a_n or not b_n:
        return False

    # substring check (quick high-confidence)
    if a_n in b_n or b_n in a_n:
        return True

    atoks = set(a_n.split())
    btoks = set(b_n.split())

    if not atoks or not btoks:
        return False

    common = atoks.intersection(btoks)
    # require at least 1 token in common and at least half of the smaller set
    threshold = max(min_common_tokens, ceil(min(len(atoks), len(btoks)) / 2))

    return len(common) >= threshold


def fuzzy_match(a, b):
    """
    Perform a fuzzy comparison of two location strings to determine if they match.
    
    Parameters:
        a (str): First location string to compare.
        b (str): Second location string to compare.
    
    Returns:
        bool: `true` if the strings are considered a fuzzy match, `false` otherwise.
    """
    return token_overlap_match(a, b, min_common_tokens=1)


def extract_stop_names_from_stops_json(stops_json):
    """
    Extract stop name strings from a routeStop.stops JSON structure.
    
    Parses either a JSON string or a Python list and returns a list of stop names.
    For list inputs, each item may be a dict (common keys checked: "stop", "name", "stop_name") or a plain string; matching values are converted to strings. For malformed input the function attempts a best-effort fallback by searching for `"stop":"<value>"` patterns in a JSON-dumped representation.
    
    Parameters:
        stops_json: JSON string or Python list representing route stops; falsy values return an empty list.
    
    Returns:
        list: A list of stop name strings (empty if none found).
    """
    stops = []
    if not stops_json:
        return stops

    try:
        if isinstance(stops_json, str):
            data = json.loads(stops_json)
        else:
            data = stops_json

        if isinstance(data, list):
            for item in data:
                # item may be dict with key 'stop' or 'name' etc. try common keys
                if isinstance(item, dict):
                    name = item.get("stop") or item.get("name") or item.get("stop_name")
                    if name:
                        stops.append(str(name))
                else:
                    # if item is plain string
                    stops.append(str(item))
    except Exception:
        # fallback: try to coerce to string
        try:
            # crude fallback: find "stop":"..." occurrences
            text = json.dumps(stops_json)
            candidates = re.findall(r'"stop"\s*:\s*"([^"]+)"', text)
            stops.extend(candidates)
        except Exception:
            pass

    return stops


# ---------- Detection logic per dutyTrip ----------

def detect_direction_for_dutytrip(dt):
    """
    Determine the travel direction (inbound or outbound) for a dutyTrip record.
    
    Uses route destinations, routeStop first/last stops, and aggregated stop-name matches to infer whether the trip is inbound or outbound. If the dutyTrip has no associated route_link or the heuristics cannot decide, the result is ambiguous.
    
    Parameters:
        dt (dutyTrip): The dutyTrip model instance to analyze.
    
    Returns:
        True if the trip is inbound, False if the trip is outbound, None if the direction is ambiguous or cannot be determined.
    """

    # Skip if no route_link
    if not getattr(dt, "route_link", None):
        return None

    route_obj = dt.route_link

    start_text = dt.start_at or ""
    end_text = dt.end_at or ""

    # 1) Try matching against route destinations
    inbound_dest = route_obj.inbound_destination or ""
    outbound_dest = route_obj.outbound_destination or ""

    # If both start & end are present, check patterns:
    # inbound: starts near outbound_dest and ends near inbound_dest
    inbound_match = False
    outbound_match = False

    try:
        if start_text and end_text and outbound_dest and inbound_dest:
            inbound_match = (fuzzy_match(start_text, outbound_dest) and fuzzy_match(end_text, inbound_dest))
            outbound_match = (fuzzy_match(start_text, inbound_dest) and fuzzy_match(end_text, outbound_dest))

            if inbound_match and not outbound_match:
                return True
            if outbound_match and not inbound_match:
                return False
    except Exception:
        # ignore and continue to next step
        pass

    # 2) Try first and last stop of routeStop entries (inbound and outbound)
    # Fetch routeStop rows for this route; there may be two rows (inbound True/False)
    rstop_qs = routeStop.objects.filter(route=route_obj)

    # helper to get first/last stop names for inbound/outbound
    def first_last_stops_for(direction_bool):
        """
        Get the first and last stop names for the given direction from the surrounding routeStop queryset.
        
        Attempts to find a routeStop row matching the provided direction and falls back to another available routeStop if none match. Returns the first and last stop names extracted from the row's stops JSON, or (None, None) if no suitable stops are available.
        
        Parameters:
            direction_bool (bool): True to select inbound stops, False to select outbound stops.
        
        Returns:
            (str | None, str | None): A tuple of (first_stop, last_stop); each is a string when available or None when not.
        """
        try:
            rs = rstop_qs.get(inbound=direction_bool)
        except (routeStop.DoesNotExist, routeStop.MultipleObjectsReturned):
            rs = rstop_qs.filter(inbound=direction_bool).first()

        if not rs:
            # try any routeStop for route with that inbound flag missing
            rs = rstop_qs.first()
            if not rs:
                return None, None

        stops = extract_stop_names_from_stops_json(rs.stops)
        if not stops:
            return None, None

        return stops[0], stops[-1]

    # inbound routeStop: inbound=True. For a trip that is inbound,
    # it commonly starts at outbound end (first or last depending on how stops are ordered).
    # We'll treat 'first' as the start-of-journey stop for that routeStop row.
    in_first, in_last = first_last_stops_for(True)
    out_first, out_last = first_last_stops_for(False)

    try:
        # Check whether duty start/end match first/last pair for inbound/outbound
        # We'll consider both (first->last) and (last->first) orderings to tolerate different list orders.
        def matches_first_last(start, end, first, last):
            """
            Check whether the start and end texts match the provided first and last stop names in either order.
            
            Parameters:
                start (str): Start location text to compare.
                end (str): End location text to compare.
                first (str): Name of the first stop.
                last (str): Name of the last stop.
            
            Returns:
                bool: `True` if (`start` ≈ `first` and `end` ≈ `last`) or (`start` ≈ `last` and `end` ≈ `first`); `False` otherwise. Empty `first` or `last` yields `False`.
            """
            if not first or not last:
                return False
            # match start ≈ first AND end ≈ last OR start ≈ last AND end ≈ first
            return ((fuzzy_match(start, first) and fuzzy_match(end, last)) or
                    (fuzzy_match(start, last) and fuzzy_match(end, first)))

        if matches_first_last(start_text, end_text, in_first, in_last) and not matches_first_last(start_text, end_text, out_first, out_last):
            return True
        if matches_first_last(start_text, end_text, out_first, out_last) and not matches_first_last(start_text, end_text, in_first, in_last):
            return False
    except Exception:
        pass

    # 3) If still not found: scan all stops for token matches.
    # Count how many matches the start and end texts have within inbound stops vs outbound stops,
    # and pick direction with higher combined matches.

    try:
        inbound_stops = []
        outbound_stops = []
        # collect stops lists from routeStop rows
        for rs in rstop_qs:
            names = extract_stop_names_from_stops_json(rs.stops)
            if rs.inbound:
                inbound_stops.extend(names)
            else:
                outbound_stops.extend(names)

        def count_matches_in_list(text, stop_list):
            """
            Count how many strings in a list fuzzy-match a reference text.
            
            Parameters:
                text (str): Reference text to match against each item.
                stop_list (iterable): Iterable of stop name strings to compare.
            
            Returns:
                int: Number of items in `stop_list` that fuzzy-match `text`.
            """
            if not text or not stop_list:
                return 0
            count = 0
            for s in stop_list:
                if fuzzy_match(text, s):
                    count += 1
            return count

        start_in_matches = count_matches_in_list(start_text, inbound_stops)
        end_in_matches = count_matches_in_list(end_text, inbound_stops)
        start_out_matches = count_matches_in_list(start_text, outbound_stops)
        end_out_matches = count_matches_in_list(end_text, outbound_stops)

        # choose the direction with higher total matches (start+end)
        inbound_total = start_in_matches + end_in_matches
        outbound_total = start_out_matches + end_out_matches

        if inbound_total > outbound_total:
            return True
        if outbound_total > inbound_total:
            return False

    except Exception:
        pass

    # if none of the above returned, ambiguous
    return None


# ---------- Command ----------

class Command(BaseCommand):
    help = "Detect direction (inbound/outbound) for dutyTrip rows and save into dutyTrip.direction"

    def add_arguments(self, parser):
        """
        Add command-line arguments for the management command: --limit, --batch-size, and --force.
        
        Parameters:
            parser: argparse.ArgumentParser
                The argument parser to which the options are added. The added options are:
                - --limit: integer; limits how many dutyTrip rows are processed.
                - --batch-size: integer; number of rows to update per database transaction.
                - --force: flag; when present, forces re-detection even if a dutyTrip already has a direction set.
        """
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of dutyTrips processed (useful for testing).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=200,
            help="How many rows to update per DB transaction.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-detection even if direction is already set.",
        )

    def handle(self, *args, **options):
        """
        Process dutyTrip rows, detect their inbound/outbound direction, and persist the detected direction to the database.
        
        This command iterates dutyTrip records (ordered by id), runs direction detection for each row, and updates the model's direction field with one of: True (inbound), False (outbound), or None (ambiguous). It accepts the following options via `options`:
        - "limit": (int) restrict the number of rows processed.
        - "batch_size": (int) number of rows to save in a single transaction.
        - "force": (bool) re-run detection even when a row already has a direction set.
        
        Processing is performed in batches using database transactions; rows without an associated route_link are skipped. The method writes progress and a final summary (processed, updated, ambiguous, skipped, failed) to standard output/error.
        """
        limit = options["limit"]
        batch_size = options["batch_size"]
        force = options["force"]

        qs = dutyTrip.objects.all().order_by("id")
        total = qs.count()
        self.stdout.write(f"Found {total} dutyTrip rows total.")

        if limit:
            qs = qs[:limit]
            self.stdout.write(f"Limiting to first {limit} rows.")

        updated = 0
        ambiguous = 0
        skipped = 0
        failed = 0

        buffer = []
        processed = 0

        for dt in qs:
            processed += 1

            # skip if no route_link
            if not getattr(dt, "route_link", None):
                skipped += 1
                continue

            # if already set and not forcing, skip
            if getattr(dt, "direction", None) is not None and not force:
                continue

            try:
                detected = detect_direction_for_dutytrip(dt)
            except Exception as e:
                self.stderr.write(f"Error detecting for dutyTrip id={dt.id}: {e}")
                failed += 1
                continue

            if detected is None:
                ambiguous += 1
                # optionally write null / leave as-is. We'll set to None explicitly.
                try:
                    dt.direction = None
                    buffer.append(dt)
                except Exception:
                    pass
            else:
                dt.inbound = detected
                buffer.append(dt)
                updated += 1

            # batch save
            if len(buffer) >= batch_size:
                try:
                    with transaction.atomic():
                        for b in buffer:
                            # Save only the direction field if possible
                            try:
                                b.save(update_fields=["direction"])
                            except Exception:
                                b.save()
                        buffer = []
                except Exception as e:
                    self.stderr.write(f"Batch save failed: {e}")
                    failed += len(buffer)
                    buffer = []

        # final flush
        if buffer:
            try:
                with transaction.atomic():
                    for b in buffer:
                        try:
                            b.save(update_fields=["direction"])
                        except Exception:
                            b.save()
            except Exception as e:
                self.stderr.write(f"Final batch save failed: {e}")
                failed += len(buffer)

        self.stdout.write("---- Summary ----")
        self.stdout.write(f"Processed: {processed}")
        self.stdout.write(f"Updated  : {updated}")
        self.stdout.write(f"Ambiguous: {ambiguous}")
        self.stdout.write(f"Skipped  : {skipped} (no route_link)")
        self.stdout.write(f"Failed   : {failed}")
        self.stdout.write("Done.")