from django.db import migrations


FEATURE_BAN_TYPES = [
    'forums',
    'tickets',
    'messaging',
    'wiki_edit',
    'buying_buses',
    'selling_buses',
]

BAN_TYPE_ALIASES = {
    'forum': 'forums',
    'ticket': 'tickets',
}


def seed_feature_ban_types(apps, schema_editor):
    BanType = apps.get_model('main', 'BanType')
    CustomUser = apps.get_model('main', 'CustomUser')

    ban_types = {
        name: BanType.objects.get_or_create(name=name)[0]
        for name in FEATURE_BAN_TYPES
    }

    for old_name, new_name in BAN_TYPE_ALIASES.items():
        old_ban_type = BanType.objects.filter(name=old_name).first()
        if not old_ban_type:
            continue

        user_ids = old_ban_type.banned_users.values_list('id', flat=True)
        for user in CustomUser.objects.filter(id__in=user_ids):
            user.banned_from.add(ban_types[new_name])
            user.banned_from.remove(old_ban_type)

        if not old_ban_type.banned_users.exists():
            old_ban_type.delete()


def reverse_seed_feature_ban_types(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0048_merge_20260511_2252'),
    ]

    operations = [
        migrations.RunPython(seed_feature_ban_types, reverse_seed_feature_ban_types),
    ]
