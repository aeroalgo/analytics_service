# Generated by Django 4.1.5 on 2023-02-05 15:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product_search', '0009_categories_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='last30daysdata',
            name='lost_profit',
            field=models.FloatField(blank=True, null=True, verbose_name='Упущенная выручка'),
        ),
        migrations.AddField(
            model_name='last30daysdata',
            name='start_price',
            field=models.FloatField(blank=True, null=True, verbose_name='Стартовая цена продажи'),
        ),
    ]