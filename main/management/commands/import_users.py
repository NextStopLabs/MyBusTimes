import csv
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from main.models import CustomUser, badge, theme, MBTAdminPermission
from datetime import datetime

def parse_date(value, fmt="%d/%m/%Y %H:%M"):
    if not value or value.upper() == "NULL":
        return None
    for fmt_try in [fmt, "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]:
        try:
            return datetime.strptime(value, fmt_try)
        except ValueError:
            continue
    print(f"⚠️ Invalid date format: {value}")
    return None

def parse_date_aware(value, fmt="%d/%m/%Y %H:%M"):
    dt = parse_date(value, fmt)
    if dt and timezone.is_naive(dt):
        return timezone.make_aware(dt)
    return dt

def parse_bool_int(value):
    if not value or value.upper() == "NULL":
        return False
    try:
        return bool(int(value))
    except ValueError:
        return False

class Command(BaseCommand):
    help = "Import users from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        fallback_date = timezone.make_aware(datetime(2024, 8, 22, 0, 0))

        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=',', quotechar='"')
            reader.fieldnames = [h.strip() for h in reader.fieldnames]

            print("CSV Headers:", reader.fieldnames)

            for row in reader:
                join_date = parse_date_aware(row.get('Create_At'))
                username = row['Username']
                email = row['Eamil']  # Make sure this matches your CSV header exactly
                name = row['Name']
                password = row['Password']
                user_id = row['ID']

                print(f"Processing user: {username}")
                if not username:
                    print("⚠️ Skipping row with no username:", row)
                    continue

                user, created = CustomUser.objects.get_or_create(username=username)

                user.email = email
                user.first_name = name
                user.password = password

                user.last_login_ip = None
                user.total_user_reports = int(row.get('TotalReports', 0))
                user.banned = parse_bool_int(row.get('Restricted'))
                user.banned_reason = row.get('RestrictedReson', '') or ''
                user.banned_date = parse_date_aware(row.get('UnbanDate'))
                user.ad_free_until = None
                user.ticketer_code = row.get('code') or None

                if user_id == '0' and username == 'Kai':
                    user.is_superuser = True
                    user.is_staff = True
                    user.password = make_password('#Anslow2022')
                else:
                    user.is_superuser = False
                    user.is_staff = False

                if row.get('PFP'):
                    user.pfp = f'images/profile_pics/{row["PFP"]}'
                if row.get('Banner'):
                    user.banner = f'images/profile_banners/{row["Banner"]}'

                if created:
                    user.join_date = join_date or fallback_date
                    user.save()
                else:
                    user.save()  # Save other fields
                    # Force update join_date to bypass any potential auto_now_add behavior
                    CustomUser.objects.filter(pk=user.pk).update(join_date=join_date or fallback_date)

                print(f"{'Created' if created else 'Updated'} user {username}")

            self.stdout.write(self.style.SUCCESS("User import completed successfully!"))
