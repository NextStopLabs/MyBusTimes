import csv
from django.contrib.auth.models import User
from django.db import transaction

csv_file = "/tmp/users.csv"

with open(csv_file, newline='', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    users = []

    for row in reader:
        users.append(User(
            id=row["ID"],  # If you want to keep IDs, but may conflict
            username=row["Username"],
            email=row["Eamil"],
            password=row["Password"],
            first_name=row["Name"],
            last_name='',
            is_staff=0,
            is_superuser=0,
            is_active=1,
            banned=row["Restricted"],
            banned_date=row["UnbanDate"],
            banned_reason=row["RestrictedReson"],
            theme_id=row["DarkMode"],
            badges=row["Badges"],
            ticketer_code=row["code"],
            date_joined=row["Create_At"],
            last_login_ip=row["IPHash"],
            static_ticketer_code=row["rolling_code"],
            total_user_reports=row["TotalReports"]
        ))

    with transaction.atomic():  # Ensures safe bulk import
        User.objects.bulk_create(users)
