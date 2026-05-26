from django.db import migrations


def readd_creating_games_ban_type(apps, schema_editor):
    BanType = apps.get_model('main', 'BanType')
    BanType.objects.get_or_create(name='creating_games')


def reverse_readd_creating_games_ban_type(apps, schema_editor):
    BanType = apps.get_model('main', 'BanType')
    BanType.objects.filter(name='creating_games').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0053_remove_creating_games_ban_type'),
    ]

    operations = [
        migrations.RunPython(readd_creating_games_ban_type, reverse_readd_creating_games_ban_type),
    ]
