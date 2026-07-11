from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
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
            "--batch-days",
            type=int,
            default=1,
            help="Process this many days per batch (default: 1)",
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

    def handle(self, *args, **options):
        days = options["days"]
        batch_days = options["batch_days"]
        chunk_size = options["chunk_size"]
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(days=days)

        if options["from_date"]:
            from datetime import datetime as dt
            oldest_date = dt.strptime(options["from_date"], "%Y-%m-%d")
            oldest_date = timezone.make_aware(oldest_date, timezone.get_current_timezone())
        else:
            oldest = Trip.objects.filter(trip_end_at__lt=cutoff).order_by("trip_end_at").values("trip_end_at").first()
            if not oldest:
                self.stdout.write("No trips to archive.")
                return
            oldest_date = oldest["trip_end_at"]

        self.stdout.write(f"Archiving trips ending between {oldest_date.date()} and {cutoff.date()}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes made"))
            return

        batch_start = oldest_date
        total_archived = 0

        while batch_start < cutoff:
            batch_end = batch_start + timedelta(days=batch_days)
            if batch_end > cutoff:
                batch_end = cutoff

            self.stdout.write(f"  Batch {batch_start.date()} to {batch_end.date()} ...", ending=" ")
            self.stdout.flush()

            batch_qs = Trip.objects.filter(
                trip_end_at__gte=batch_start,
                trip_end_at__lt=batch_end,
            )

            processed = 0
            while True:
                trip_ids = list(batch_qs.values_list("trip_id", flat=True)[:chunk_size])
                if not trip_ids:
                    break

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

                processed += len(trip_ids)
                total_archived += len(trip_ids)

            self.stdout.write(f"✓ {processed} trips")
            batch_start += timedelta(days=batch_days)

        self.stdout.write(self.style.SUCCESS(f"Done. {total_archived} trip(s) archived."))
