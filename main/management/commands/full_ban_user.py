import ipaddress

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from main.cloudflare_ips import is_cloudflare_ip
from main.models import BannedIps


class Command(BaseCommand):
    help = (
        'Ban a user account and ban every IP found in their simple-history records.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'user_id',
            type=int,
            help='Numeric user ID to ban.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List the collected IPs without banning the user or creating IP bans.',
        )
        parser.add_argument(
            '--reason',
            help='Reason to store against the user ban and each banned IP.',
        )

    def handle(self, *args, **options):
        user_id = options['user_id']
        dry_run = options['dry_run']
        reason = (options['reason'] or '').strip()

        if not dry_run and not reason:
            raise CommandError('--reason cannot be empty.')

        user_model = get_user_model()

        try:
            user = user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist as exc:
            raise CommandError(f'No user found with ID {user_id}.') from exc

        ips, skipped_cloudflare = self.collect_user_ips(user)

        if dry_run:
            self.stdout.write(
                f'Dry run for user {user_id}: {len(ips)} unique IP(s) found.'
            )
            for ip in sorted(ips):
                self.stdout.write(ip)
            if skipped_cloudflare:
                self.stdout.write(
                    f'Skipped {len(skipped_cloudflare)} Cloudflare IP(s): '
                    + ', '.join(sorted(skipped_cloudflare))
                )
            return

        user.banned = True
        user.banned_reason = reason
        user.banned_date = None
        user.save(update_fields=['banned', 'banned_reason', 'banned_date'])

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for ip in sorted(ips):
            banned_ip, created = BannedIps.objects.get_or_create(
                ip_address=ip,
                defaults={
                    'reason': reason,
                    'related_user': user,
                },
            )

            if created:
                created_count += 1
                continue

            changed = False
            if not banned_ip.reason:
                banned_ip.reason = reason
                changed = True

            if banned_ip.related_user_id != user.id:
                banned_ip.related_user = user
                changed = True

            if changed:
                banned_ip.save(update_fields=['reason', 'related_user'])
                updated_count += 1
            else:
                skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'User {user_id} banned. Created {created_count} IP ban(s), '
                f'updated {updated_count}, skipped {skipped_count}. '
                f'Collected {len(ips)} unique IP(s). '
                f'Skipped {len(skipped_cloudflare)} Cloudflare IP(s).'
            )
        )

    def collect_user_ips(self, user):
        ips = set()
        skipped_cloudflare = set()

        for value in (getattr(user, 'last_ip', None), getattr(user, 'last_login_ip', None)):
            normalized = self.normalize_ip(value)
            if normalized:
                self.add_ip_or_skip_cloudflare(normalized, ips, skipped_cloudflare)

        historical_model = user.__class__.history.model
        history_entries = historical_model.objects.filter(id=user.id).only(
            'last_ip',
            'last_login_ip',
        )

        for entry in history_entries:
            for field_name in ('last_ip', 'last_login_ip'):
                normalized = self.normalize_ip(getattr(entry, field_name, None))
                if normalized:
                    self.add_ip_or_skip_cloudflare(normalized, ips, skipped_cloudflare)

        return ips, skipped_cloudflare

    def add_ip_or_skip_cloudflare(self, value, ips, skipped_cloudflare):
        if is_cloudflare_ip(value):
            skipped_cloudflare.add(value)
            return

        ips.add(value)

    def normalize_ip(self, value):
        if not value:
            return None

        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            return None