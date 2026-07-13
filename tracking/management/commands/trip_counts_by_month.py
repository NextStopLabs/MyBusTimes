import calendar
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.functions import TruncDay, TruncMonth
from tracking.models import Trip, TripArchive


class Command(BaseCommand):
    help = "List each month/year and how many trips (and archived trips) exist"

    def add_arguments(self, parser):
        parser.add_argument(
            "--archived",
            action="store_true",
            help="Include archived trips in the counts",
        )
        parser.add_argument(
            "--month",
            type=str,
            metavar="YYYY-MM",
            help="Show day-by-day breakdown for a specific month (e.g. 2026-07)",
        )

    def _print_day_breakdown(self, model, month_str, options):
        year, month = map(int, month_str.split("-"))
        _, last_day = calendar.monthrange(year, month)

        qs = (
            model.objects
            .filter(
                trip_start_at__year=year,
                trip_start_at__month=month,
            )
            .annotate(day=TruncDay("trip_start_at"))
            .values("day")
            .annotate(count=Count("pk"))
            .order_by("day")
        )

        heading = f"Day-by-day breakdown for {month_str}"
        self.stdout.write(self.style.MIGRATE_HEADING(heading))
        self.stdout.write(self.style.MIGRATE_HEADING(f"{'Day':<12} {'Trips':>8}"))
        self.stdout.write(self.style.MIGRATE_HEADING("-" * 22))

        total = 0
        day_counts = {row["day"].day: row["count"] for row in qs if row["day"]}
        for d in range(1, last_day + 1):
            count = day_counts.get(d, 0)
            total += count
            label = f"{month_str}-{d:02d}"
            self.stdout.write(f"{label:<12} {count:>8}")

        self.stdout.write(self.style.MIGRATE_HEADING("-" * 22))
        self.stdout.write(f"{'Total':<12} {total:>8}")

    def handle(self, *args, **options):
        month_str = options["month"]
        include_archived = options["archived"]

        if month_str:
            self._print_day_breakdown(Trip, month_str, options)
            if include_archived:
                self.stdout.write("")
                self.stdout.write(self.style.MIGRATE_HEADING("Archived Trips:"))
                self._print_day_breakdown(TripArchive, month_str, options)
            return

        qs = (
            Trip.objects
            .annotate(month=TruncMonth("trip_start_at"))
            .values("month")
            .annotate(count=Count("trip_id"))
            .order_by("month")
        )

        self.stdout.write(self.style.MIGRATE_HEADING(f"{'Month':<12} {'Trips':>8}"))
        self.stdout.write(self.style.MIGRATE_HEADING("-" * 22))

        total_trips = 0
        for row in qs:
            month = row["month"]
            count = row["count"]
            label = month.strftime("%Y-%m") if month else "No date"
            total_trips += count
            self.stdout.write(f"{label:<12} {count:>8}")

        self.stdout.write(self.style.MIGRATE_HEADING("-" * 22))
        self.stdout.write(f"{'Total':<12} {total_trips:>8}")

        if include_archived:
            archived_qs = (
                TripArchive.objects
                .annotate(month=TruncMonth("trip_start_at"))
                .values("month")
                .annotate(count=Count("original_trip_id"))
                .order_by("month")
            )

            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING("Archived Trips:"))
            self.stdout.write(self.style.MIGRATE_HEADING(f"{'Month':<12} {'Trips':>8}"))
            self.stdout.write(self.style.MIGRATE_HEADING("-" * 22))

            total_archived = 0
            for row in archived_qs:
                month = row["month"]
                count = row["count"]
                label = month.strftime("%Y-%m") if month else "No date"
                total_archived += count
                self.stdout.write(f"{label:<12} {count:>8}")

            self.stdout.write(self.style.MIGRATE_HEADING("-" * 22))
            self.stdout.write(f"{'Total':<12} {total_archived:>8}")
