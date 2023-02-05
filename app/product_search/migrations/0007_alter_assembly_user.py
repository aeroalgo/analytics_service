# Generated by Django 4.1.5 on 2023-02-03 15:16

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('product_search', '0006_remove_perioddata_name_month'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assembly',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='assembly_user', to=settings.AUTH_USER_MODEL),
        ),
    ]
