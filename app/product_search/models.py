import datetime

from django.db import models
from django.utils import timezone
from app.login.models import UserProfile


class Product(models.Model):
    sku = models.CharField(
        verbose_name="SKU", max_length=12, unique=True, blank=False, null=False
    )


class ProductProperty(models.Model):
    MP_WB = 1
    MP_OZON = 2
    MARKETS = (
        (MP_WB, "Wildberries"),
        (MP_OZON, "Ozon"),
    )

    COMPETITION_STRAIGHT = 1
    COMPETITION_ANALOG = 2
    COMPETITIONS = (
        (COMPETITION_STRAIGHT, "Прямой"),
        (COMPETITION_ANALOG, "Аналог"),
    )

    sku = models.ForeignKey(
        Product, verbose_name="Артикул", blank=False, related_name="property", on_delete=models.CASCADE
    )
    mp = models.IntegerField(
        verbose_name="Маркетплейс", blank=True, choices=MARKETS, null=True,
    )
    competition = models.IntegerField(
        verbose_name="Тип конкуренции", blank=True, choices=COMPETITIONS, null=True
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


class Categories(models.Model):
    name = models.TextField(
        verbose_name="Категория", unique=True, blank=False, null=False
    )


class PeriodData(models.Model):
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
        verbose_name="Средняя цена за период (выручка / число продаж)", blank=True, null=True
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
        verbose_name="Первое появление", blank=False, default=timezone.localdate
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
