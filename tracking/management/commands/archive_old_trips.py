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
            "--dry-run",
            action="store_true",
            help="Count trips that would be archived without actually archiving",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(days=days)

        old_trips = Trip.objects.filter(trip_end_at__lt=cutoff)

        total = old_trips.count()
        self.stdout.write(f"Found {total} trip(s) ending before {cutoff.isoformat()}")

        if total == 0:
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(f"Dry run: {total} trip(s) would be archived"))
            return

        # Nullify Tracking references first to avoid CASCADE delete
        tracking_updated = Tracking.objects.filter(
            tracking_trip__in=old_trips
        ).update(tracking_trip=None)

        self.stdout.write(f"Nullified tracking_trip on {tracking_updated} Tracking record(s)")

        # Build archive objects
        archive_objs = []
        for trip in old_trips.iterator(chunk_size=500):
            archive_objs.append(TripArchive(
                original_trip_id=trip.trip_id,
                trip_display_id=trip.trip_display_id,
                trip_vehicle=trip.trip_vehicle,
                trip_route=trip.trip_route,
                trip_route_num=trip.trip_route_num,
                trip_driver=trip.trip_driver,
                trip_start_location=trip.trip_start_location,
                trip_end_location=trip.trip_end_location,
                trip_start_at=trip.trip_start_at,
                trip_end_at=trip.trip_end_at,
                trip_updated_at=trip.trip_updated_at,
                trip_ended=trip.trip_ended,
                trip_missed=trip.trip_missed,
                trip_inbound=trip.trip_inbound,
                trip_board=trip.trip_board,
            ))

        with transaction.atomic():
            TripArchive.objects.bulk_create(archive_objs, batch_size=500)
            deleted_count, _ = old_trips.delete()

        self.stdout.write(self.style.SUCCESS(
            f"Archived {len(archive_objs)} trip(s) (deleted {deleted_count} from Trip)"
        ))
