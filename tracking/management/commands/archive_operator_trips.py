from django.core.management.base import BaseCommand
from django.db import transaction, connection
from tracking.models import Trip, TripArchive
from fleet.models import MBTOperator


class Command(BaseCommand):
    help = "Archive all trips whose vehicle belongs to a given operator code"

    def add_arguments(self, parser):
        parser.add_argument(
            "operator_code",
            type=str,
            help="Code of the operator whose trips should be archived",
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

    def _process_queryset(self, qs, chunk_size):
        total = qs.count()
        processed = 0
        last_id = 0
        while True:
            trip_ids = list(
                qs.filter(trip_id__gt=last_id)
                .order_by("trip_id")
                .values_list("trip_id", flat=True)[:chunk_size]
            )
            if not trip_ids:
                break
            last_id = trip_ids[-1]
            self._archive_chunk(trip_ids)
            processed += len(trip_ids)
            pct = int(processed / total * 100) if total else 0
            self.stdout.write(f"  Progress: {processed}/{total} ({pct}%)")
        return processed

    def handle(self, *args, **options):
        operator_code = options["operator_code"]
        chunk_size = options["chunk_size"]
        dry_run = options["dry_run"]

        try:
            operator = MBTOperator.objects.get(operator_code=operator_code)
        except MBTOperator.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Operator with code '{operator_code}' not found."))
            return

        qs = Trip.objects.filter(trip_vehicle__operator=operator)

        total = qs.count()
        if total == 0:
            self.stdout.write(f"No trips found for operator '{operator.operator_name}' (code {operator_code}).")
            return

        self.stdout.write(
            f"Operator: {operator.operator_name} (code {operator_code})"
        )
        self.stdout.write(f"Trips to archive: {total}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes made"))
            return

        total_archived = self._process_queryset(qs, chunk_size)
        self.stdout.write(
            self.style.SUCCESS(f"Done. {total_archived} trip(s) archived.")
        )
