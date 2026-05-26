from django.db import migrations


FEATURE_BAN_TYPES = [
    'forums',
    'tickets',
    'messaging',
    'wiki_edit',
    'buying_buses',
    'selling_buses',
    'account_settings',
    'subscriptions',
    'ticketer_code',
    'creating_liveries',
    'creating_vehicles',
    'creating_games',
    'reporting',
    'groups',
    'giveaways',
    'tracking',
    'live_maps',
    'community_hub',
    'data_import',
]


def seed_more_feature_ban_types(apps, schema_editor):
    BanType = apps.get_model('main', 'BanType')
    for name in FEATURE_BAN_TYPES:
        BanType.objects.get_or_create(name=name)


def reverse_seed_more_feature_ban_types(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0049_seed_feature_ban_types'),
    ]

    operations = [
        migrations.RunPython(seed_more_feature_ban_types, reverse_seed_more_feature_ban_types),
    ]
