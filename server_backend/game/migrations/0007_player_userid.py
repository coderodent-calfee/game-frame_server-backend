# Generated by Django 5.1.4 on 2025-01-08 06:08

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("game", "0006_rename_game_id_game_gameid_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="player",
            name="userId",
            field=models.ForeignKey(
                default="1234567",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="players",
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=False,
        ),
    ]
