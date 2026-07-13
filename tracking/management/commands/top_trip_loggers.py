from django.core.management.base import BaseCommand
from django.db.models import Count
from tracking.models import Trip, TripArchive


class Command(BaseCommand):
    help = "Show which operators logged the most trips in a given month"

    def add_arguments(self, parser):
        parser.add_argument(
            "month",
            type=str,
            metavar="YYYY-MM",
            help="Month to analyse (e.g. 2026-07)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Number of top operators to show (default: 20)",
        )
        parser.add_argument(
            "--archived",
            action="store_true",
            help="Include archived trips in the counts",
        )

    def _print_leaderboard(self, model, year, month, limit, label):
        qs = (
            model.objects
            .filter(
                trip_start_at__year=year,
                trip_start_at__month=month,
                trip_vehicle__operator__isnull=False,
            )
            .values("trip_vehicle__operator__operator_name")
            .annotate(trip_count=Count("pk"))
            .order_by("-trip_count")[:limit]
        )

        self.stdout.write(self.style.MIGRATE_HEADING(f"\n{label}:"))
        self.stdout.write(
            self.style.MIGRATE_HEADING(f"{'Operator':<35} {'Trips':>8}")
        )
        self.stdout.write(self.style.MIGRATE_HEADING("-" * 45))

        for rank, row in enumerate(qs, 1):
            name = row["trip_vehicle__operator__operator_name"] or "(no operator)"
            count = row["trip_count"]
            self.stdout.write(f"{rank:<4} {name:<35} {count:>8}")

    def handle(self, *args, **options):
        month_str = options["month"]
        limit = options["limit"]
        include_archived = options["archived"]

        try:
            year, month = map(int, month_str.split("-"))
        except ValueError:
            self.stdout.write(self.style.ERROR("Invalid format. Use YYYY-MM (e.g. 2026-07)."))
            return

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Top {limit} operators by trips logged in {month_str}"
            )
        )

        self._print_leaderboard(Trip, year, month, limit, "Active Trips")

        if include_archived:
            self._print_leaderboard(TripArchive, year, month, limit, "Archived Trips")
