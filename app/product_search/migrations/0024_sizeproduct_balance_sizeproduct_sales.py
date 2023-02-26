# Generated by Django 4.1.5 on 2023-02-22 18:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product_search', '0023_remove_sizeproduct_balance_remove_sizeproduct_sales'),
    ]

    operations = [
        migrations.AddField(
            model_name='sizeproduct',
            name='balance',
            field=models.JSONField(blank=True, null=True, verbose_name='Остаток единиц товара за период последние 30 дней'),
        ),
        migrations.AddField(
            model_name='sizeproduct',
            name='sales',
            field=models.JSONField(blank=True, null=True, verbose_name='Количество проданных единиц товара за период последние 30 дней'),
        ),
    ]
