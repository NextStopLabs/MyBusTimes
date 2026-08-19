from django.core.management.base import BaseCommand
from fleet.models import auto_return_expired_loans


class Command(BaseCommand):
    help = "Return all vehicles whose loan has expired back to their originating operator."

    def handle(self, *args, **options):
        returned = auto_return_expired_loans()
        self.stdout.write(self.style.SUCCESS(f"Returned {returned} vehicle(s) to their originating operator."))
