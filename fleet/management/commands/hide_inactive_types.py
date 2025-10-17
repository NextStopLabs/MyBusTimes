from django.core.management.base import BaseCommand
from fleet.models import vehicleType  # adjust if your model is in a different app

class Command(BaseCommand):
    help = 'Sets hidden=True for all vehicleType entries where active=False'

    def handle(self, *args, **kwargs):
        inactive_types = vehicleType.objects.filter(active=False, hidden=False)
        count = inactive_types.update(hidden=True)
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} vehicleType(s) to hidden=True'))
