from django.core.management.base import BaseCommand

from fleet.models import process_due_scheduled_transfers


class Command(BaseCommand):
    help = (
        "Move vehicles for due scheduled transfer requests "
        "(status=scheduled, scheduled_for in the past). "
        "Normally processed lazily by high-traffic fleet views; "
        "this command is a backup (e.g. run via cron)."
    )

    def handle(self, *args, **options):
        total = 0
        while True:
            moved = process_due_scheduled_transfers()
            total += moved
            if moved == 0:
                break
        self.stdout.write(
            self.style.SUCCESS(
                f"Scheduled transfers processed — moved: {total}."
            )
        )
