from django.core.management.base import BaseCommand
from django.utils.text import slugify
from fleet.models import MBTOperator

MAX_SLUG_LENGTH = 50  # match your model's max_length

class Command(BaseCommand):
    help = "Populate blank operator_slug fields with unique slugs"

    def handle(self, *args, **options):
        count = 0
        # Existing slugs to ensure uniqueness
        seen = set(MBTOperator.objects.exclude(operator_slug="").values_list("operator_slug", flat=True))

        for op in MBTOperator.objects.filter(operator_slug__isnull=True) | MBTOperator.objects.filter(operator_slug=""):
            base_slug = slugify(op.operator_name) or f"operator-{op.id}"
            slug = base_slug[:MAX_SLUG_LENGTH]  # truncate to fit
            counter = 1

            # Ensure uniqueness across DB + already-generated slugs
            while slug in seen or MBTOperator.objects.filter(operator_slug=slug).exclude(id=op.id).exists():
                suffix = f"-{counter}"
                # truncate base_slug to leave room for suffix
                slug = f"{base_slug[:MAX_SLUG_LENGTH - len(suffix)]}{suffix}"
                counter += 1

            op.operator_slug = slug
            op.save()
            seen.add(slug)
            count += 1
            self.stdout.write(self.style.SUCCESS(f"Set slug for {op.operator_name} → {slug}"))

        if count == 0:
            self.stdout.write(self.style.WARNING("No blank slugs found."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Filled {count} missing slugs."))
