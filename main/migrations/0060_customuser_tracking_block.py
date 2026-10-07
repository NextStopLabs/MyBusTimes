# Generated on 2026-10-04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0059_add_user_block'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='tracking_block',
            field=models.BooleanField(default=False, help_text="If checked, none of this user's companies will be tracked on any tracking scripts including pre-compute tracking."),
        ),
        migrations.AddField(
            model_name='historicalcustomuser',
            name='tracking_block',
            field=models.BooleanField(default=False, help_text="If checked, none of this user's companies will be tracked on any tracking scripts including pre-compute tracking."),
        ),
    ]
