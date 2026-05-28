# Generated manually for block vehicle swap limits.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fleet', '0031_historicalcompanyupdate_historicalfleetchange_and_more'),
        ('routes', '0012_historicaldaytype_historicalduty_historicaldutytrip_and_more'),
        ('tracking', '0010_historicaltrip_trip_inbound_trip_trip_inbound'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlockVehicleSwap',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_date', models.DateField(db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('board_id', models.PositiveIntegerField(db_index=True)),
                ('swap_from_trip_id', models.PositiveIntegerField(blank=True, null=True)),
                ('from_vehicle_id', models.PositiveIntegerField(blank=True, null=True)),
                ('to_vehicle_id', models.PositiveIntegerField(blank=True, null=True)),
                ('created_by_id', models.PositiveIntegerField(blank=True, null=True)),
            ],
        ),
        migrations.AddIndex(
            model_name='blockvehicleswap',
            index=models.Index(fields=['board_id', 'service_date'], name='trk_blkswap_board_date_idx'),
        ),
    ]
