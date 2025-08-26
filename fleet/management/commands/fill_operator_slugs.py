from django.core.management.base import BaseCommand
from django.utils.text import slugify
from fleet.models import MBTOperator


class Command(BaseCommand):
    help = "Populate blank operator_slug fields with unique slugs"

    def handle(self, *args, **options):
        count = 0
        seen = set(MBTOperator.objects.exclude(operator_slug="").values_list("operator_slug", flat=True))

        for op in MBTOperator.objects.filter(operator_slug__isnull=True) | MBTOperator.objects.filter(operator_slug=""):
            base_slug = slugify(op.operator_name) or f"operator-{op.id}"
            slug = base_slug
            counter = 1

            # Ensure uniqueness across DB + already-generated slugs
            while slug in seen or MBTOperator.objects.filter(operator_slug=slug).exclude(id=op.id).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"

            op.operator_slug = slug
            op.save()
            seen.add(slug)
            count += 1
            self.stdout.write(self.style.SUCCESS(f"Set slug for {op.operator_name} → {slug}"))

        if count == 0:
            self.stdout.write(self.style.WARNING("No blank slugs found."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Filled {count} missing slugs."))
