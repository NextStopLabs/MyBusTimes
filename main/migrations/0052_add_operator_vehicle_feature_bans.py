from django.db import migrations


FEATURE_BAN_TYPES = [
    'creating_operators',
    'deleting_operators',
    'mass_add_vehicles',
    'mass_edit_vehicles',
]


def add_operator_vehicle_feature_bans(apps, schema_editor):
    BanType = apps.get_model('main', 'BanType')
    for name in FEATURE_BAN_TYPES:
        BanType.objects.get_or_create(name=name)


def reverse_add_operator_vehicle_feature_bans(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0051_limit_feature_ban_types'),
    ]

    operations = [
        migrations.RunPython(add_operator_vehicle_feature_bans, reverse_add_operator_vehicle_feature_bans),
    ]
