from django.core.management.base import BaseCommand
from django.db import connection


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

        with connection.cursor() as cursor:
            if vehicle_ids:
                cursor.execute(
                    "SELECT id FROM fleet_fleet WHERE id = ANY(%s)",
                    [vehicle_ids],
                )
            else:
                cursor.execute("SELECT id FROM fleet_fleet")
            all_vehicle_ids = [row[0] for row in cursor.fetchall()]

        self.stdout.write(f"Total vehicles in fleet: {len(all_vehicle_ids)}")

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT trip_vehicle_id FROM tracking_trip",
            )
            vehicles_with_trips = {row[0] for row in cursor.fetchall()}

        eligible_ids = [vid for vid in all_vehicle_ids if vid not in vehicles_with_trips]

        skipped = len(all_vehicle_ids) - len(eligible_ids)
        self.stdout.write(f"Vehicles with unarchived trips (skipped): {skipped}")
        self.stdout.write(f"Vehicles eligible for backfill:      {len(eligible_ids)}")

        if not eligible_ids:
            self.stdout.write("Nothing to backfill.")
            return

        updates = []
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
                [eligible_ids],
            )
            for row in cursor.fetchall():
                vehicle_id, trip_start_at, trip_route_num = row
                dt_str = (
                    trip_start_at.isoformat()
                    if hasattr(trip_start_at, "isoformat")
                    else str(trip_start_at) if trip_start_at else None
                )
                updates.append((dt_str, trip_route_num or "", vehicle_id))

        no_archive = len(eligible_ids) - len(updates)
        self.stdout.write(f"Vehicles with no archive data:       {no_archive}")
        self.stdout.write(f"Vehicles to update:                  {len(updates)}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes made"))
            if updates:
                self.stdout.write("Sample (up to 10):")
                for dt_str, route_num, vid in updates[:10]:
                    self.stdout.write(f"  vehicle_id={vid}  route={route_num}  datetime={dt_str}")
            return

        if updates:
            with connection.cursor() as cursor:
                cursor.executemany(
                    "UPDATE fleet_fleet SET last_trip_datetime = %s, last_trip_route_num = %s WHERE id = %s",
                    updates,
                )
            self.stdout.write(
                self.style.SUCCESS(f"Updated {len(updates)} vehicle(s).")
            )
        else:
            self.stdout.write("No updates needed.")
