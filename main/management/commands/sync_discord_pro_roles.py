from django.core.management.base import BaseCommand

from main.discord_roles import sync_discord_pro_role, user_has_active_pro
from main.models import CustomUser


class Command(BaseCommand):
    help = "Sync Discord Pro roles for linked MyBusTimes users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all-linked",
            action="store_true",
            help="Also remove the Pro role from linked users who no longer have Pro.",
        )

    def handle(self, *args, **options):
        users = CustomUser.objects.filter(discord_id__isnull=False).exclude(discord_id="")
        if not options["all_linked"]:
            users = users.exclude(sub_plan="free")

        synced = 0
        failed = 0

        for user in users.iterator():
            has_pro = user_has_active_pro(user)
            if not has_pro and not options["all_linked"]:
                continue

            if sync_discord_pro_role(user, has_pro):
                synced += 1
                self.stdout.write(self.style.SUCCESS(f"Synced {user.username}"))
            else:
                failed += 1
                self.stdout.write(self.style.WARNING(f"Could not sync {user.username}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Synced: {synced}. Failed: {failed}."))
