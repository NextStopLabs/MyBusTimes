from contextlib import contextmanager

from django.db import transaction, connection
from django.db.models import Count
from django.core.management.base import BaseCommand

from fleet.models import (
    MBTOperator,
    fleet,
    ticket,
    companyUpdate,
    helper,
    favouriteOperator,
    operatorTransferRequest,
    vehicleTransferRequest,
    AbandonedBusOrder,
)
from routes.models import route, duty, dutyTrip, board_category, timetableEntry
from tracking.models import Trip, ActiveTrip, Tracking, TripArchive


class Command(BaseCommand):
    help = (
        "Permanently remove an operator and everything belonging to it, in stages so the "
        "site stays alive: times first, then vehicles in batches, then routes one by one, "
        "then tickets/boards/other data, then the operator itself."
    )

    def add_arguments(self, parser):
        parser.add_argument("operator_id", type=str, help="The ID (or operator code) of the operator to remove")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without deleting anything")
        parser.add_argument("--yes", action="store_true", help="Skip the confirmation prompt")
        parser.add_argument("--vehicle-batch-size", type=int, default=50, help="How many vehicles to delete per batch (default 50)")
        parser.add_argument("--time-batch-size", type=int, default=1000, help="How many trips/tracking rows to delete per batch (default 1000)")
        parser.add_argument(
            "--delete-shared-routes",
            action="store_true",
            help="Also delete routes that are shared with other operators (they are normally just unlinked)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        operator = self._get_operator(options["operator_id"])
        if operator is None:
            return

        if operator.operator_code == "UC":
            self.stdout.write(self.style.ERROR("Refusing to remove the default 'UC' (Unknown Company) operator."))
            return

        self.stdout.write(self.style.WARNING(f"\nTarget: {operator.operator_name} ({operator.operator_code}) [ID {operator.pk}]"))

        # --------------------------------- overview ---------------------------------
        vehicle_ids = list(fleet.objects.filter(operator=operator).values_list("id", flat=True))
        solo_route_ids, shared_route_ids = self._split_routes(operator)

        counts = {
            "vehicles (owned, deleted)": len(vehicle_ids),
            "vehicles (loaned out, kept by loanee)": fleet.objects.filter(operator=operator, loan_operator__isnull=False).exclude(loan_operator=operator).count(),
            "vehicles (loaned in, loan just cleared)": fleet.objects.filter(loan_operator=operator).count(),
            "active trips": ActiveTrip.objects.filter(vehicle_id__in=vehicle_ids).count(),
            "tracking rows": Tracking.objects.filter(tracking_vehicle_id__in=vehicle_ids).count(),
            "trips": Trip.objects.filter(trip_vehicle_id__in=vehicle_ids).count(),
            "trip archives": TripArchive.objects.filter(trip_vehicle_id__in=vehicle_ids).count(),
            "solo routes (deleted)": len(solo_route_ids),
            "shared routes (unlinked only)": len(shared_route_ids),
            "timetable entries": timetableEntry.objects.filter(route_id__in=solo_route_ids).count(),
            "fare tickets": ticket.objects.filter(operator=operator).count(),
            "board categories": board_category.objects.filter(operator=operator).count(),
            "duties": duty.objects.filter(duty_operator=operator).count(),
            "company updates": companyUpdate.objects.filter(operator=operator).count(),
            "helpers": helper.objects.filter(operator=operator).count(),
            "favourites": favouriteOperator.objects.filter(operator=operator).count(),
            "transfer requests": (
                operatorTransferRequest.objects.filter(operator=operator).count()
                + vehicleTransferRequest.objects.filter(from_operator=operator).count()
                + vehicleTransferRequest.objects.filter(to_operator=operator).count()
            ),
            "abandoned bus orders": AbandonedBusOrder.objects.filter(destination_operator=operator).count(),
        }

        self.stdout.write("\nThis will remove:")
        for label, count in counts.items():
            self.stdout.write(f"  {label}: {count:,}")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("\n[DRY RUN] Nothing was deleted."))
            return

        if not options["yes"]:
            confirm = input(f"\nType the operator code '{operator.operator_code}' to confirm removal: ").strip()
            if confirm != operator.operator_code:
                self.stdout.write(self.style.ERROR("Confirmation did not match - aborting."))
                return

        total_deleted = 0

        # ------------------------------ phase 1: times ------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("\nPhase 1/5: removing all times from this operator's vehicles..."))
        total_deleted += self._delete_in_batches(ActiveTrip.objects.filter(vehicle_id__in=vehicle_ids), options["time_batch_size"], "active trips")
        total_deleted += self._delete_in_batches(Tracking.objects.filter(tracking_vehicle_id__in=vehicle_ids), options["time_batch_size"], "tracking rows")
        total_deleted += self._delete_in_batches(Trip.objects.filter(trip_vehicle_id__in=vehicle_ids), options["time_batch_size"], "trips")
        total_deleted += self._delete_in_batches(TripArchive.objects.filter(trip_vehicle_id__in=vehicle_ids), options["time_batch_size"], "trip archives")

        # ----------------------------- phase 2: vehicles ----------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("\nPhase 2/5: removing vehicles..."))
        # Vehicles on loan FROM this operator become owned by the operator borrowing
        # them (same behaviour as the operator_delete view), so the borrower keeps them.
        with self._atomic():
            loaned_out = fleet.objects.filter(operator=operator, loan_operator__isnull=False).exclude(loan_operator=operator)
            borrower_ids = {v["id"]: v["loan_operator_id"] for v in loaned_out.values("id", "loan_operator_id")}
        for vehicle_id, borrower_id in borrower_ids.items():
            with self._atomic():
                fleet.objects.filter(id=vehicle_id, operator=operator).update(
                    operator_id=borrower_id, loan_operator=None, loan_until=None, loan_snapshot=None
                )
        if borrower_ids:
            self.stdout.write(f"Transferred {len(borrower_ids):,} loaned vehicles to the operators borrowing them.")

        # Vehicles this operator had borrowed from others just have the loan cleared.
        with self._atomic():
            cleared = fleet.objects.filter(loan_operator=operator).update(loan_operator=None, loan_until=None, loan_snapshot=None)
        if cleared:
            self.stdout.write(f"Cleared {cleared:,} incoming vehicle loans.")

        total_deleted += self._delete_in_batches(
            fleet.objects.filter(operator=operator), options["vehicle_batch_size"], "vehicles", batch_size_override=options["vehicle_batch_size"]
        )

        # ------------------------------ phase 3: routes -----------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("\nPhase 3/5: removing routes one by one..."))
        routes_to_delete = list(solo_route_ids)
        if options["delete_shared_routes"]:
            routes_to_delete += list(shared_route_ids)
            self.stdout.write(self.style.WARNING("--delete-shared-routes given: shared routes will be deleted too."))

        # Detach anything still referencing these routes (trips/tracking rows remaining
        # here belong to other operators' vehicles, which would otherwise be
        # cascade-deleted along with the route).
        total_deleted += self._detach_route_references(routes_to_delete)

        deleted_routes = 0
        for route_id in routes_to_delete:
            with self._atomic():
                obj = route.objects.filter(id=route_id).first()
                if obj is None:
                    continue
                obj.delete()
            deleted_routes += 1
            self._progress("routes", deleted_routes, len(routes_to_delete))
        self.stdout.write("")
        total_deleted += deleted_routes

        # Unlink shared routes we are keeping.
        if shared_route_ids and not options["delete_shared_routes"]:
            with self._atomic():
                route.route_operators.through.objects.filter(route_id__in=shared_route_ids, mbtoperator_id=operator.pk).delete()
            self.stdout.write(f"Unlinked {len(shared_route_ids):,} shared routes (still used by other operators).")

        # ------------------------ phase 4: other operator data ----------------------
        self.stdout.write(self.style.MIGRATE_HEADING("\nPhase 4/5: removing tickets, boards and other operator data..."))
        total_deleted += self._delete_in_batches(ticket.objects.filter(operator=operator), 500, "fare tickets")
        total_deleted += self._delete_in_batches(board_category.objects.filter(operator=operator), 500, "board categories")
        total_deleted += self._delete_in_batches(dutyTrip.objects.filter(duty__duty_operator=operator), options["time_batch_size"], "duty trips")
        total_deleted += self._delete_in_batches(duty.objects.filter(duty_operator=operator), 500, "duties")
        total_deleted += self._delete_in_batches(companyUpdate.objects.filter(operator=operator), 500, "company updates")
        total_deleted += self._delete_in_batches(helper.objects.filter(operator=operator), 500, "helpers")
        total_deleted += self._delete_in_batches(favouriteOperator.objects.filter(operator=operator), 500, "favourites")
        total_deleted += self._delete_in_batches(operatorTransferRequest.objects.filter(operator=operator), 500, "operator transfer requests")
        total_deleted += self._delete_in_batches(
            vehicleTransferRequest.objects.filter(from_operator=operator) | vehicleTransferRequest.objects.filter(to_operator=operator),
            500,
            "vehicle transfer requests",
        )
        # destination_operator is PROTECT, so these must go before the operator itself.
        total_deleted += self._delete_in_batches(AbandonedBusOrder.objects.filter(destination_operator=operator), 500, "abandoned bus orders")

        # --------------------------- phase 5: the operator --------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("\nPhase 5/5: removing the operator itself..."))
        with self._atomic():
            operator.region.clear()
            operator.delete()
        # simple_history rows are not cascade-deleted; clear them explicitly.
        with self._atomic():
            MBTOperator.history.model.objects.filter(id=operator.pk).delete()
        self.stdout.write(self.style.SUCCESS(f"Operator '{operator.operator_name}' deleted."))

        self.stdout.write(self.style.SUCCESS(f"\nDone. Approximately {total_deleted:,} rows removed."))

    # ------------------------------------------------------------------- helpers --

    def _get_operator(self, identifier):
        if identifier.isdigit():
            operator = MBTOperator.objects.filter(pk=int(identifier)).first()
            if operator is None:
                self.stdout.write(self.style.ERROR(f"No operator found with ID '{identifier}'"))
                return None
        else:
            operator = MBTOperator.objects.filter(operator_code=identifier).first()
            if operator is None:
                self.stdout.write(self.style.ERROR(f"No operator found with code '{identifier}'"))
                return None
        return operator

    def _split_routes(self, operator):
        """Return (solo route ids, shared route ids) for routes linked to this operator."""
        op_route_ids = list(route.objects.filter(route_operators=operator).values_list("id", flat=True))
        # Count operators per route in a separate query - combining the filter and the
        # annotation on the same M2M reuses the join and makes every route look solo.
        counts = dict(
            route.objects.filter(id__in=op_route_ids)
            .annotate(operator_count=Count("route_operators"))
            .values_list("id", "operator_count")
        )
        solo = [i for i in op_route_ids if counts.get(i, 0) == 1]
        shared = [i for i in op_route_ids if counts.get(i, 0) > 1]
        return solo, shared

    def _detach_route_references(self, route_ids):
        """Null route references on remaining trips/tracking/duty trips so route
        deletion doesn't cascade into other operators' data."""
        detached = 0
        with self._atomic():
            detached += Trip.objects.filter(trip_route_id__in=route_ids).update(trip_route=None)
            detached += Tracking.objects.filter(tracking_route_id__in=route_ids).update(tracking_route=None)
            detached += dutyTrip.objects.filter(route_link_id__in=route_ids).update(route_link=None)
        if detached:
            self.stdout.write(self.style.WARNING(f"Detached {detached:,} trips/tracking rows belonging to other operators from these routes."))
        return detached

    def _delete_in_batches(self, queryset, batch_size, label, batch_size_override=None):
        total = queryset.count()
        if total == 0:
            self.stdout.write(f"  {label}: none")
            return 0
        size = batch_size_override or batch_size
        deleted = 0
        while True:
            pks = list(queryset.order_by("pk").values_list("pk", flat=True)[:size])
            if not pks:
                break
            with self._atomic():
                queryset.model.objects.filter(pk__in=pks).delete()
            deleted += len(pks)
            self._progress(label, deleted, total)
        self.stdout.write("")
        return deleted

    def _progress(self, label, done, total):
        pct = (done / total * 100) if total else 100
        self.stdout.write(f"\r  {label}: {done:,}/{total:,} ({pct:.0f}%)", ending="")
        self.stdout.flush()

    @contextmanager
    def _atomic(self):
        """Each batch runs in its own short transaction so locks are held briefly,
        and the Postgres statement timeout is lifted for big deletes
        (same approach as the operator_delete view)."""
        with transaction.atomic():
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL statement_timeout = 0")
                    cursor.execute("SET LOCAL lock_timeout = '30s'")
            yield
