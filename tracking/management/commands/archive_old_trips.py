from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction, connection
from django.db.models import Q
from tracking.models import Trip, TripArchive, Tracking
from datetime import timedelta


class Command(BaseCommand):
    help = "Archive trips older than the specified age to TripArchive"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Archive trips older than this many days (default: 7)",
        )
        parser.add_argument(
            "--from-date",
            type=str,
            help="Start date (YYYY-MM-DD). Defaults to oldest trip found.",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=10000,
            help="Rows per bulk operation (default: 10000)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Skip actual archiving, just show what would be done",
        )

    def _old_enough_filter(self, cutoff):
        return Q(trip_end_at__lt=cutoff) | Q(
            trip_end_at__isnull=True, trip_updated_at__lt=cutoff
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

        self.stdout.write("✓")

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
        days = options["days"]
        chunk_size = options["chunk_size"]
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(days=days)

        qs = Trip.objects.filter(self._old_enough_filter(cutoff))

        if options["from_date"]:
            from datetime import datetime as dt

            from_date = dt.strptime(options["from_date"], "%Y-%m-%d")
            from_date = timezone.make_aware(
                from_date, timezone.get_current_timezone()
            )
            qs = qs.filter(
                Q(trip_end_at__gte=from_date)
                | Q(
                    trip_end_at__isnull=True,
                    trip_updated_at__gte=from_date,
                )
            )

        if not qs.exists():
            self.stdout.write("No trips to archive.")
            return

        self.stdout.write(
            f"Archiving {qs.count()} trip(s) older than {cutoff.date()}"
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes made"))
            return

        total_archived = self._process_queryset(qs, chunk_size)
        self.stdout.write(
            self.style.SUCCESS(f"Done. {total_archived} trip(s) archived.")
        )
