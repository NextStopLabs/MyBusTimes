import ipaddress

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'List all other users that currently or historically used any IP address from a given user.'

    def add_arguments(self, parser):
        parser.add_argument(
            'user_id',
            type=int,
            help='User ID to inspect.',
        )

    def handle(self, *args, **options):
        user_model = get_user_model()
        historical_model = user_model.history.model

        user_id = options['user_id']

        try:
            target_user = user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist as exc:
            raise CommandError(f'No user found with ID {user_id}.') from exc

        ip_addresses = self.collect_user_ips(target_user)

        if not ip_addresses:
            self.stdout.write(f'No IPs found for user {target_user.id} ({target_user.username}).')
            return

        current_user_ids = set(
            user_model.objects.filter(
                last_ip__in=ip_addresses,
            ).values_list('id', flat=True)
        )
        current_user_ids.update(
            user_model.objects.filter(
                last_login_ip__in=ip_addresses,
            ).values_list('id', flat=True)
        )

        historical_user_ids = set(
            historical_model.objects.filter(last_ip__in=ip_addresses).values_list('id', flat=True)
        )
        historical_user_ids.update(
            historical_model.objects.filter(last_login_ip__in=ip_addresses).values_list('id', flat=True)
        )

        user_ids = sorted(current_user_ids | historical_user_ids)

        if not user_ids:
            self.stdout.write(
                f'No users found that share any IPs from user {target_user.id} ({target_user.username}).'
            )
            return

        users = user_model.objects.filter(id__in=user_ids).exclude(id=target_user.id).order_by('id')

        if not users.exists():
            self.stdout.write(
                f'No other users found that share any IPs from user {target_user.id} '
                f'({target_user.username}).'
            )
            return

        self.stdout.write(
            f'Found {users.count()} other user(s) that share {len(ip_addresses)} IP(s) from '
            f'user {target_user.id} ({target_user.username}). Each user is listed once.'
        )
        self.stdout.write('-' * 120)
        self.stdout.write('IPs: ' + ', '.join(sorted(ip_addresses)))
        self.stdout.write('-' * 120)

        for user in users:
            self.stdout.write(
                f'id={user.id} | username={user.username} | email={user.email or "-"} | '
                f'last_ip={user.last_ip or "-"} | last_login_ip={user.last_login_ip or "-"}'
            )

    def collect_user_ips(self, user):
        ips = set()

        for value in (getattr(user, 'last_ip', None), getattr(user, 'last_login_ip', None)):
            normalized = self.normalize_ip(value)
            if normalized:
                ips.add(normalized)

        historical_model = user.__class__.history.model
        history_entries = historical_model.objects.filter(id=user.id).only(
            'last_ip',
            'last_login_ip',
        )

        for entry in history_entries:
            for field_name in ('last_ip', 'last_login_ip'):
                normalized = self.normalize_ip(getattr(entry, field_name, None))
                if normalized:
                    ips.add(normalized)

        return ips

    def normalize_ip(self, value):
        if not value:
            return None

        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            return None