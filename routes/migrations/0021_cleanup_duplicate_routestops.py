from django.db import migrations


def cleanup_duplicates(apps, schema_editor):
    routeStop = apps.get_model("routes", "routeStop")
    from django.db.models import Count, Max

    duplicates = (
        routeStop.objects.values("route", "inbound")
        .annotate(count=Count("id"), max_id=Max("id"))
        .filter(count__gt=1)
    )
    for dup in duplicates:
        routeStop.objects.filter(
            route_id=dup["route"],
            inbound=dup["inbound"],
        ).exclude(id=dup["max_id"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("routes", "0020_add_route_indexes"),
    ]

    operations = [
        migrations.RunPython(cleanup_duplicates, reverse_code=migrations.RunPython.noop),
    ]
