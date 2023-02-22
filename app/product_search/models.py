import datetime
import os
from urllib import request
from django.db import models
from django.utils import timezone
from django.core.files import File
from app.login.models import UserProfile


class Product(models.Model):
    MP_WB = 1
    MP_OZON = 2
    MARKETS = (
        (MP_WB, "WB"),
        (MP_OZON, "OZ"),
    )
    sku = models.CharField(
        verbose_name="SKU", max_length=12, unique=True, blank=False, null=False
    )
    mp = models.IntegerField(
        verbose_name="Маркетплейс", blank=True, choices=MARKETS, null=True,
    )


class Assembly(models.Model):
    skus = models.ManyToManyField(
        Product, related_name="assembly_sku", verbose_name="Идентификаторы в сборке", blank=True
    )
    name = models.CharField(
        verbose_name="Название сборки", blank=False, max_length=255, null=True, unique=True
    )

    user = models.ForeignKey(
        UserProfile, related_name="assembly_user", blank=True, null=True, on_delete=models.CASCADE
    )


class ProductProperty(models.Model):
    COMPETITION_STRAIGHT = 1
    COMPETITION_ANALOG = 2
    COMPETITION_ANALYZE = 3
    COMPETITIONS = (
        (COMPETITION_STRAIGHT, "Прямой"),
        (COMPETITION_ANALOG, "Аналог"),
        (COMPETITION_ANALYZE, "Анализируемый товар"),
    )

    sku = models.ForeignKey(
        Product, verbose_name="Артикул", blank=False, related_name="property", on_delete=models.CASCADE
    )
    assembly = models.ForeignKey(
        Assembly, verbose_name="Сборка", blank=False, related_name="property_assembly", on_delete=models.CASCADE,
        null=True
    )
    competition = models.IntegerField(
        verbose_name="Тип конкуренции", blank=True, choices=COMPETITIONS, null=True
    )


class Categories(models.Model):
    name = models.TextField(
        verbose_name="Категория", unique=True, blank=False, null=False
    )


class PeriodData(models.Model):
    MONTH_QUARTER = {
        1: 1,
        2: 1,
        3: 1,
        4: 2,
        5: 2,
        6: 2,
        7: 3,
        8: 3,
        9: 3,
        10: 4,
        11: 4,
        12: 4,
    }

    sku = models.ForeignKey(
        Product, verbose_name="Артикул", blank=False, related_name="period_sku", on_delete=models.CASCADE
    )
    date_start = models.DateField(
        verbose_name="Дата начала периода", blank=False, default=timezone.localdate
    )
    date_end = models.DateField(
        verbose_name="Дата окончания периода", blank=False, default=timezone.localdate
    )
    lost_profit = models.FloatField(
        verbose_name="Упущенная выручка", blank=True, null=True
    )
    revenue = models.FloatField(
        verbose_name="Выручка за период", blank=True, null=True
    )
    final_price_average = models.FloatField(
        verbose_name="Средняя цена за период (выручка / число продаж)", blank=True, null=True,
    )
    sales = models.IntegerField(
        verbose_name="Количество проданных единиц товара за период", blank=True, null=True
    )
    category = models.ForeignKey(
        Categories, verbose_name="Категория", blank=False, related_name="period_sku_category", on_delete=models.CASCADE,
        null=True
    )


class Last30DaysData(models.Model):
    sku = models.ForeignKey(
        Product, verbose_name="Артикул", blank=False, related_name="days_data", on_delete=models.CASCADE, null=True
    )
    date_update = models.DateField(
        verbose_name="Дата загрузки", blank=False, default=timezone.localdate
    )
    first_date = models.DateField(
        verbose_name="Первое появление", blank=True, null=True
    )
    revenue = models.FloatField(
        verbose_name="Выручка за последние 30 дней", blank=True, null=True
    )
    final_price_average = models.FloatField(
        verbose_name="Средняя цена за период (выручка / число продаж) за последние 30 дней", blank=True, null=True
    )
    sales = models.IntegerField(
        verbose_name="Количество проданных единиц товара за период за последние 30 дней", blank=True, null=True
    )

    categories_pos = models.FloatField(
        verbose_name="Средняя позиция в выдаче", blank=True, null=True
    )
    category = models.ForeignKey(
        Categories, verbose_name="Категория", blank=False, related_name="days_data_category", on_delete=models.CASCADE,
        null=True
    )
    rating = models.FloatField(
        verbose_name="Рейтинг карточки", blank=True, null=True
    )
    comments = models.FloatField(
        verbose_name="Количество отзывов", blank=True, null=True
    )
    start_price = models.FloatField(
        verbose_name="Стартовая цена продажи", blank=True, null=True
    )
    lost_profit = models.FloatField(
        verbose_name="Упущенная выручка", blank=True, null=True
    )
    last_price = models.FloatField(
        verbose_name="Последняя цена", blank=True, null=True
    )
    most_sales = models.FloatField(
        verbose_name="Цена 80% продаж", blank=True, null=True
    )
    graph = models.JSONField(
        verbose_name="График продаж", blank=True, null=True
    )
    price_graph = models.JSONField(
        verbose_name="График цены", blank=True, null=True
    )
    name = models.TextField(
        verbose_name="Наименование позиции", blank=True, null=True
    )


def image_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/product/id/<filename>
    return 'product/{0}/{1}'.format(instance.sku.id, filename)


class ProductPhoto(models.Model):
    sku = models.ForeignKey(Product, verbose_name="Фото sku", on_delete=models.CASCADE, related_name="photo")
    link = models.TextField(verbose_name="Ссылка на фото", blank=True, null=True)
    photo = models.ImageField(verbose_name="Фото", blank=True, null=True, upload_to=image_path)
    filename = models.TextField(verbose_name="Имя файла", blank=True, null=True)

    def get_remote_image(self):
        if self.link and not self.photo:
            result = request.urlretrieve(self.link)
            self.photo.save(
                os.path.basename(self.link),
                File(open(result[0], 'rb'))
            )
            self.save()
