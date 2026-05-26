from django.db import migrations


ALLOWED_FEATURE_BAN_TYPES = [
    'forums',
    'tickets',
    'messaging',
    'wiki_edit',
    'buying_buses',
    'selling_buses',
    'creating_liveries',
    'creating_vehicles',
    'creating_games',
    'reporting',
    'groups',
    'giveaways',
    'tracking',
    'live_maps',
    'community_hub',
]

FEATURE_BAN_ALIASES = {
    'forum': 'forums',
    'ticket': 'tickets',
    'wiki_editing': 'wiki_edit',
}


def limit_feature_ban_types(apps, schema_editor):
    BanType = apps.get_model('main', 'BanType')
    CustomUser = apps.get_model('main', 'CustomUser')

    allowed = {
        name: BanType.objects.get_or_create(name=name)[0]
        for name in ALLOWED_FEATURE_BAN_TYPES
    }

    for old_name, new_name in FEATURE_BAN_ALIASES.items():
        old_ban_type = BanType.objects.filter(name=old_name).first()
        if not old_ban_type:
            continue

        user_ids = old_ban_type.banned_users.values_list('id', flat=True)
        for user in CustomUser.objects.filter(id__in=user_ids):
            user.banned_from.add(allowed[new_name])
            user.banned_from.remove(old_ban_type)

    BanType.objects.exclude(name__in=ALLOWED_FEATURE_BAN_TYPES).delete()


def reverse_limit_feature_ban_types(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0050_seed_more_feature_ban_types'),
    ]

    operations = [
        migrations.RunPython(limit_feature_ban_types, reverse_limit_feature_ban_types),
    ]
