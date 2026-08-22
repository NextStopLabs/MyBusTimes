from django.core.management.base import BaseCommand
from django.db import transaction, connection
from tracking.models import Trip
from main.models import CustomUser


class Command(BaseCommand):
    help = "Archive all trips from operators owned by a given username"

    def add_arguments(self, parser):
        parser.add_argument(
            "username",
            type=str,
            help="Username whose operators' trips should be archived",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Skip actual archiving, just show what would be done",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=10000,
            help="Rows per bulk operation (default: 10000)",
        )

    def _archive_chunk(self, trip_ids):
        self.stdout.write(
            f"  Archiving {len(trip_ids)} trip(s) (IDs {min(trip_ids)}–{max(trip_ids)}) ...",
            ending=" ",
        )
        self.stdout.flush()

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE tracking_tracking SET tracking_trip_id = NULL WHERE tracking_trip_id = ANY(%s)",
                    [list(trip_ids)],
                )
                cursor.execute(
                    """
                    INSERT INTO tracking_triparchive (
                        original_trip_id, trip_display_id, trip_vehicle_id, trip_route_id,
                        trip_route_num, trip_driver_id, trip_start_location, trip_end_location,
                        trip_start_at, trip_end_at, trip_updated_at, trip_ended, trip_missed,
                        trip_inbound, trip_board_id, archived_at
                    )
                    SELECT
                        trip_id, trip_display_id, trip_vehicle_id, trip_route_id,
                        trip_route_num, trip_driver_id, trip_start_location, trip_end_location,
                        trip_start_at, trip_end_at, trip_updated_at, trip_ended, trip_missed,
                        trip_inbound, trip_board_id, NOW()
                    FROM tracking_trip
                    WHERE trip_id = ANY(%s)
                    """,
                    [list(trip_ids)],
                )
                cursor.execute(
                    "DELETE FROM tracking_trip WHERE trip_id = ANY(%s)",
                    [list(trip_ids)],
                )

        self.stdout.write("done")

    def _persist_last_trip_info(self, vehicle_ids, batch_size=5000):
        if not vehicle_ids:
            return
        self.stdout.write("  Persisting last trip info on vehicles ...", ending=" ")
        self.stdout.flush()

        vehicle_ids = list(vehicle_ids)

        total_updated = 0
        for i in range(0, len(vehicle_ids), batch_size):
            chunk = vehicle_ids[i : i + batch_size]
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
                    [chunk],
                )
                for row in cursor.fetchall():
                    vehicle_id, trip_start_at, trip_route_num = row
                    dt_str = trip_start_at.isoformat() if hasattr(trip_start_at, 'isoformat') else str(trip_start_at) if trip_start_at else None
                    updates.append((dt_str, trip_route_num or '', vehicle_id))
            if updates:
                with connection.cursor() as cursor:
                    cursor.executemany(
                        "UPDATE fleet_fleet SET last_trip_datetime = %s, last_trip_route_num = %s WHERE id = %s",
                        updates,
                    )
            total_updated += len(updates)
            done = i + len(chunk)
            self.stdout.write(
                f"  {done}/{len(vehicle_ids)} vehicles checked, "
                f"{total_updated} updated"
            )
        self.stdout.write(f"updated {total_updated} vehicle(s)")

    def _collect_vehicle_ids(self, trip_ids):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT trip_vehicle_id FROM tracking_trip WHERE trip_id = ANY(%s)",
                [list(trip_ids)],
            )
            return [row[0] for row in cursor.fetchall()]

    def _process_queryset(self, qs, chunk_size):
        total = qs.count()
        processed = 0
        last_id = 0
        all_vehicle_ids = set()
        while True:
            trip_ids = list(
                qs.filter(trip_id__gt=last_id)
                .order_by("trip_id")
                .values_list("trip_id", flat=True)[:chunk_size]
            )
            if not trip_ids:
                break
            last_id = trip_ids[-1]
            all_vehicle_ids.update(self._collect_vehicle_ids(trip_ids))
            self._archive_chunk(trip_ids)
            processed += len(trip_ids)
            pct = int(processed / total * 100) if total else 0
            self.stdout.write(f"  Progress: {processed}/{total} ({pct}%)")
        self._persist_last_trip_info(all_vehicle_ids)
        return processed

    def handle(self, *args, **options):
        username = options["username"]
        chunk_size = options["chunk_size"]
        dry_run = options["dry_run"]

        try:
            user = CustomUser.objects.get(username=username)
        except CustomUser.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User '{username}' not found."))
            return

        operator_ids = list(
            user.owner.values_list("id", flat=True)
        )

        if not operator_ids:
            self.stdout.write(f"User '{username}' does not own any operators.")
            return

        self.stdout.write(
            f"User: {username} (ID {user.id}) — {len(operator_ids)} operator(s): {operator_ids}"
        )

        qs = Trip.objects.filter(trip_vehicle__operator_id__in=operator_ids)

        total = qs.count()
        if total == 0:
            self.stdout.write("No trips found for this user's operators.")
            return

        self.stdout.write(f"Trips to archive: {total}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes made"))
            return

        total_archived = self._process_queryset(qs, chunk_size)
        self.stdout.write(
            self.style.SUCCESS(f"Done. {total_archived} trip(s) archived.")
        )
