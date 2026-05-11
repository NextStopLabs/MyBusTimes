from django.db import migrations


FLUFFYNET_TILE_URL = "https://tiles.fluffynet.dev/styles/mtt-light/{z}/{x}/{y}.png"
FLUFFYNET_ATTRIBUTION = "MTTMaps, Provided by FluffyNET"


def update_default_tiles(apps, schema_editor):
    map_tile_set = apps.get_model("fleet", "mapTileSet")
    map_tile_set.objects.update_or_create(
        name="Real World",
        defaults={
            "tile_url": FLUFFYNET_TILE_URL,
            "attribution": FLUFFYNET_ATTRIBUTION,
            "is_default": True,
        },
    )


def restore_osm_tiles(apps, schema_editor):
    map_tile_set = apps.get_model("fleet", "mapTileSet")
    map_tile_set.objects.filter(name="Real World").update(
        tile_url="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        attribution="© OpenStreetMap contributors",
        is_default=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("fleet", "0043_fleet_sim_delay_historicalfleet_sim_delay_and_more"),
    ]

    operations = [
        migrations.RunPython(update_default_tiles, restore_osm_tiles),
    ]
