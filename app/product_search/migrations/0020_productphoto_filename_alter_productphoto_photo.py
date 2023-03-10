# Generated by Django 4.1.5 on 2023-02-21 15:38

import app.product_search.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product_search', '0019_productphoto_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='productphoto',
            name='filename',
            field=models.TextField(blank=True, null=True, verbose_name='Имя файла'),
        ),
        migrations.AlterField(
            model_name='productphoto',
            name='photo',
            field=models.ImageField(blank=True, null=True, upload_to=app.product_search.models.image_path, verbose_name='Фото'),
        ),
    ]
