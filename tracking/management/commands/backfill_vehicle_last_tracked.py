from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone


CHUNK_SIZE = 5000


class Command(BaseCommand):
    help = "Backfill last_trip_datetime / last_trip_route_num from TripArchive for vehicles with no unarchived trips"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )
        parser.add_argument(
            "--vehicle-ids",
            type=int,
            nargs="+",
            help="Only process specific vehicle IDs",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        vehicle_ids = options["vehicle_ids"]

        self.stdout.write("=" * 60)
        self.stdout.write("Backfill Vehicle Last Tracked Status")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Started at: {timezone.now()}")
        self.stdout.write(f"Chunk size: {CHUNK_SIZE}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be committed"))
        self.stdout.write("")

        # --- Step 1: collect all vehicle IDs ---
        self.stdout.write("[1/4] Collecting all vehicle IDs from fleet_fleet ...")
        with connection.cursor() as cursor:
            if vehicle_ids:
                self.stdout.write(f"      Filtering to {len(vehicle_ids)} specified vehicle(s)")
                cursor.execute(
                    "SELECT id FROM fleet_fleet WHERE id = ANY(%s)",
                    [vehicle_ids],
                )
            else:
                cursor.execute("SELECT id FROM fleet_fleet")
            all_vehicle_ids = [row[0] for row in cursor.fetchall()]
        self.stdout.write(f"      → {len(all_vehicle_ids):,} vehicle(s) in fleet")
        self.stdout.write("")

        # --- Step 2: find vehicles that still have unarchived trips ---
        self.stdout.write("[2/4] Finding vehicles with unarchived trips (these will be skipped) ...")
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT trip_vehicle_id FROM tracking_trip")
            vehicles_with_trips = {row[0] for row in cursor.fetchall()}
        self.stdout.write(f"      → {len(vehicles_with_trips):,} vehicle(s) still have live Trip records")
        eligible_ids = [vid for vid in all_vehicle_ids if vid not in vehicles_with_trips]
        skipped = len(all_vehicle_ids) - len(eligible_ids)
        self.stdout.write(f"      → {skipped:,} will be skipped, {len(eligible_ids):,} eligible for backfill")
        self.stdout.write("")

        if not eligible_ids:
            self.stdout.write("Nothing to backfill — all vehicles still have unarchived trips.")
            return

        # --- Step 3: query TripArchive in chunks ---
        self.stdout.write("[3/4] Querying TripArchive for most-recent non-missed trip per eligible vehicle ...")
        total_chunks = (len(eligible_ids) + CHUNK_SIZE - 1) // CHUNK_SIZE
        self.stdout.write(f"      Processing in {total_chunks} chunk(s) ...")
        all_updates = []
        for i in range(0, len(eligible_ids), CHUNK_SIZE):
            chunk = eligible_ids[i : i + CHUNK_SIZE]
            chunk_idx = (i // CHUNK_SIZE) + 1
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT DISTINCT ON (trip_vehicle_id)
                        trip_vehicle_id, trip_start_at, trip_route_num
                    FROM tracking_triparchive
                    WHERE trip_vehicle_id = ANY(%s)
                      AND trip_missed = FALSE
                    ORDER BY trip_vehicle_id, trip_start_at DESC
                    """,
                    [chunk],
                )
                chunk_results = cursor.fetchall()
                for row in chunk_results:
                    vehicle_id, trip_start_at, trip_route_num = row
                    dt_str = (
                        trip_start_at.isoformat()
                        if hasattr(trip_start_at, "isoformat")
                        else str(trip_start_at) if trip_start_at else None
                    )
                    all_updates.append((dt_str, trip_route_num or "", vehicle_id))

            found_in_chunk = len(chunk_results)
            self.stdout.write(
                f"      Chunk {chunk_idx}/{total_chunks}: "
                f"checked {len(chunk):,} vehicles, "
                f"found {found_in_chunk:,} in archive, "
                f"total accumulated: {len(all_updates):,}"
            )

        no_archive = len(eligible_ids) - len(all_updates)
        self.stdout.write(f"      → {no_archive:,} eligible vehicle(s) have no archive data at all")
        self.stdout.write(f"      → {len(all_updates):,} vehicle(s) have archived trip data to apply")
        self.stdout.write("")

        if not all_updates:
            self.stdout.write("No archive data found. Nothing to update.")
            return

        # --- Step 4: show sample / apply updates ---
        if dry_run:
            self.stdout.write("[4/4] " + self.style.WARNING("DRY RUN — showing sample only"))
            self.stdout.write(f"      {len(all_updates):,} vehicle(s) would be updated")
            if all_updates:
                self.stdout.write("      Sample (up to 10):")
                for dt_str, route_num, vid in all_updates[:10]:
                    self.stdout.write(
                        f"        vehicle_id={vid}  "
                        f"last_trip_datetime={dt_str}  "
                        f"last_trip_route_num={route_num}"
                    )
            return

        self.stdout.write("[4/4] Writing last_trip_datetime / last_trip_route_num to fleet_fleet ...")
        total_updates = len(all_updates)
        for i in range(0, total_updates, CHUNK_SIZE):
            batch = all_updates[i : i + CHUNK_SIZE]
            with connection.cursor() as cursor:
                cursor.executemany(
                    "UPDATE fleet_fleet SET last_trip_datetime = %s, last_trip_route_num = %s WHERE id = %s",
                    batch,
                )
            self.stdout.write(f"      Wrote batch {len(batch):,} ({i + 1:,}–{i + len(batch):,} / {total_updates:,})")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"DONE. Updated {total_updates:,} vehicle(s)."))
        self.stdout.write("=" * 60)
