from django.core.management.base import BaseCommand
from fleet.models import fleet

class Command(BaseCommand):
    help = "Fix singular feature names in fleet.features (Power Socket → Power Sockets, Seat Belt → Seat Belts)."

    def handle(self, *args, **options):
        replacements = {
            "Power Socket": "Power Sockets",
            "Seat Belt": "Seat Belts",
        }

        updated_count = 0

        for f in fleet.objects.all():
            if not f.features:
                continue

            updated_features = []
            changed = False

            for feature in f.features:
                new_feature = replacements.get(feature, feature)
                if new_feature != feature:
                    changed = True
                updated_features.append(new_feature)

            if changed:
                f.features = updated_features
                f.save(update_fields=["features"])
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Updated fleet ID {f.id}: {updated_features}")
                )

        self.stdout.write(self.style.SUCCESS(f"✅ Done! Updated {updated_count} fleet records."))
