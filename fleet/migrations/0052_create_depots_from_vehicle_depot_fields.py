from django.db import migrations


def create_depots_from_vehicle_depots(apps, schema_editor):
    Fleet = apps.get_model('fleet', 'fleet')
    Depot = apps.get_model('fleet', 'Depot')

    if schema_editor.connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout = 0")

    existing = {
        (operator_id, (name or '').strip().casefold())
        for operator_id, name in Depot.objects.values_list('operator_id', 'name')
        if operator_id and (name or '').strip()
    }
    depot_rows = (
        Fleet.objects
        .exclude(depot__isnull=True)
        .exclude(depot='')
        .values_list('operator_id', 'depot')
        .distinct()
    )

    seen = set()
    depots_to_create = []
    for operator_id, depot_name in depot_rows:
        cleaned_name = (depot_name or '').strip()[:100]
        if not operator_id or not cleaned_name:
            continue

        key = (operator_id, cleaned_name.casefold())
        if key in seen:
            continue
        seen.add(key)

        if key in existing:
            continue

        depots_to_create.append(Depot(
            operator_id=operator_id,
            name=cleaned_name,
        ))

    if depots_to_create:
        Depot.objects.bulk_create(depots_to_create, batch_size=25, ignore_conflicts=True)


def noop_reverse(apps, schema_editor):
    # Do not delete depots on rollback; they may have been edited or assigned after creation.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('fleet', '0051_historicaldepotboardcategoryvehicleoptions_and_more'),
    ]

    operations = [
        migrations.RunPython(create_depots_from_vehicle_depots, noop_reverse),
    ]
