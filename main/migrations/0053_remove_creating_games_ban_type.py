from django.db import migrations


def remove_creating_games_ban_type(apps, schema_editor):
    BanType = apps.get_model('main', 'BanType')
    BanType.objects.filter(name='creating_games').delete()


def reverse_remove_creating_games_ban_type(apps, schema_editor):
    BanType = apps.get_model('main', 'BanType')
    BanType.objects.get_or_create(name='creating_games')


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0052_add_operator_vehicle_feature_bans'),
    ]

    operations = [
        migrations.RunPython(remove_creating_games_ban_type, reverse_remove_creating_games_ban_type),
    ]
