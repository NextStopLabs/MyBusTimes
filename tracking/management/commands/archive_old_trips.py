from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
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
            default=200,
            help="Rows per bulk operation (default: 200)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Skip actual archiving, just show what would be done",
        )

    def _old_enough_filter(self, cutoff):
        return Q(trip_end_at__lt=cutoff) | Q(trip_end_at__isnull=True, trip_updated_at__lt=cutoff)

    def _archive_chunk(self, trip_ids, chunk_size):
        self.stdout.write(
            f"  Archiving {len(trip_ids)} trip(s) (IDs {min(trip_ids)}–{max(trip_ids)}) ...",
            ending=" ",
        )
        self.stdout.flush()

        Tracking.objects.filter(tracking_trip_id__in=trip_ids).update(tracking_trip=None)

        with transaction.atomic():
            trips = list(Trip.objects.filter(trip_id__in=trip_ids))
            archive_objs = [
                TripArchive(
                    original_trip_id=t.trip_id,
                    trip_display_id=t.trip_display_id,
                    trip_vehicle=t.trip_vehicle,
                    trip_route=t.trip_route,
                    trip_route_num=t.trip_route_num,
                    trip_driver=t.trip_driver,
                    trip_start_location=t.trip_start_location,
                    trip_end_location=t.trip_end_location,
                    trip_start_at=t.trip_start_at,
                    trip_end_at=t.trip_end_at,
                    trip_updated_at=t.trip_updated_at,
                    trip_ended=t.trip_ended,
                    trip_missed=t.trip_missed,
                    trip_inbound=t.trip_inbound,
                    trip_board=t.trip_board,
                )
                for t in trips
            ]
            TripArchive.objects.bulk_create(archive_objs, batch_size=chunk_size)
            Trip.objects.filter(trip_id__in=trip_ids).delete()

        self.stdout.write("✓")

    def _process_queryset(self, qs, chunk_size):
        total = qs.count()
        processed = 0
        while True:
            trip_ids = list(qs.values_list("trip_id", flat=True)[:chunk_size])
            if not trip_ids:
                break
            self._archive_chunk(trip_ids, chunk_size)
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
            from_date = timezone.make_aware(from_date, timezone.get_current_timezone())
            qs = qs.filter(
                Q(trip_end_at__gte=from_date) | Q(trip_end_at__isnull=True, trip_updated_at__gte=from_date)
            )

        if not qs.exists():
            self.stdout.write("No trips to archive.")
            return

        self.stdout.write(f"Archiving {qs.count()} trip(s) older than {cutoff.date()}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes made"))
            return

        total_archived = self._process_queryset(qs, chunk_size)
        self.stdout.write(self.style.SUCCESS(f"Done. {total_archived} trip(s) archived."))
