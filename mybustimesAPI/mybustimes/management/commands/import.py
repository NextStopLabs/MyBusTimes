import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from mybustimes.models import CustomUser
from django.db import transaction
from django.utils import timezone
from django.db.utils import IntegrityError

class Command(BaseCommand):
    help = 'Import users from a CSV file'

    def handle(self, *args, **kwargs):
        csv_file = "D:/OneDrive - South Staffordshire College/Desktop/MyBusTimes New/New-MyBusTimes/API/mybustimesAPI/tmp/users.csv"

        # Log the start of the import process
        self.stdout.write(self.style.NOTICE("Starting user import..."))

        try:
            with open(csv_file, newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                users = []

                for row in reader:
                    username = row["Username"].strip()

                    if not username:
                        self.stdout.write(self.style.WARNING("Skipping row with empty username."))
                        continue

                    self.stdout.write(self.style.NOTICE(f"Processing user: {username}"))

                    # Ensure username uniqueness before processing
                    if CustomUser.objects.filter(username=username).exists():
                        self.stdout.write(self.style.WARNING(f"Duplicate username: {username}, skipping..."))
                        continue

                    badges = row.get("Badges", "")
                    badges = badges.split(",") if badges else []

                    banned_date = row.get("UnbanDate", "").strip()
                    if banned_date:
                        try:
                            banned_date = datetime.strptime(banned_date, "%Y-%m-%d")
                            banned_date = timezone.make_aware(banned_date)
                        except ValueError:
                            self.stdout.write(self.style.WARNING(f"Invalid date format for 'UnbanDate' in user {username}, setting to None."))
                            banned_date = None
                    else:
                        banned_date = None

                    # Ensure large placeholder dates are avoided
                    if banned_date and banned_date.year >= 9999:
                        banned_date = None  # Or set a realistic future date

                    create_at = row.get("Create_At", "").strip()
                    if create_at:
                        try:
                            date_joined = datetime.strptime(create_at, "%Y-%m-%d %H:%M:%S.%f")
                            date_joined = timezone.make_aware(date_joined)
                        except ValueError:
                            self.stdout.write(self.style.WARNING(f"Invalid date format for 'Create_At' in user {username}, using current time."))
                            date_joined = timezone.now()
                    else:
                        date_joined = timezone.now()

                    # Extract and validate `Restricted`
                    restricted_value = row.get("Restricted", "").strip()
                    banned = bool(int(restricted_value)) if restricted_value.isdigit() else False  # Default to False

                    # Extract and validate `theme_id`
                    theme_id = row.get("DarkMode", "").strip()
                    theme_id = int(theme_id) if theme_id.isdigit() else 1  # Default to 1 if invalid

                    # Extract and validate `total_user_reports`
                    total_reports = row.get("TotalReports", "").strip()
                    total_user_reports = int(total_reports) if total_reports.isdigit() else 0  # Default to 0

                    # Extract and validate `rolling_code`
                    rolling_code_value = row.get("rolling_code", "").strip()

                    # Create and append the user object
                    users.append(CustomUser(
                        username=username,
                        email=row.get("Email", "").strip(),
                        password=make_password(row["Password"]),
                        first_name=row.get("Name", "").strip(),
                        last_name="",
                        is_staff=False,
                        is_superuser=False,
                        is_active=True,
                        banned=banned,
                        banned_date=banned_date,
                        banned_reason=row.get("RestrictedReason", "").strip(),
                        theme_id=theme_id,  # Now properly assigned
                        badges=badges,
                        ticketer_code=row.get("code", "").strip(),
                        date_joined=date_joined,
                        last_login_ip=row.get("IPHash", "").strip(),
                        static_ticketer_code=bool(int(rolling_code_value)) if rolling_code_value.isdigit() else True,  # Default to True
                        total_user_reports=total_user_reports  # Now properly assigned
                    ))

                if users:
                    self.stdout.write(self.style.NOTICE(f"Preparing to insert {len(users)} users into the database..."))
                    with transaction.atomic():
                        CustomUser.objects.bulk_create(users, ignore_conflicts=True)  # Ignore conflicts with duplicates
                    self.stdout.write(self.style.SUCCESS("✅ User import completed successfully!"))
                else:
                    self.stdout.write(self.style.WARNING("No valid users to import."))

        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f"Integrity error: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
