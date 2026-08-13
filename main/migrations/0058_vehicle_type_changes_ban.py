from django.db import migrations


VEHICLE_TYPE_CHANGES_BAN = 'vehicle_type_changes'


def add_vehicle_type_changes_ban(apps, schema_editor):
    BanType = apps.get_model('main', 'BanType')
    BanType.objects.get_or_create(name=VEHICLE_TYPE_CHANGES_BAN)


def remove_vehicle_type_changes_ban(apps, schema_editor):
    BanType = apps.get_model('main', 'BanType')
    BanType.objects.filter(name=VEHICLE_TYPE_CHANGES_BAN).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0057_customuser_fleet_icons_and_more'),
    ]

    operations = [
        migrations.RunPython(add_vehicle_type_changes_ban, remove_vehicle_type_changes_ban),
    ]
