from django.db import models

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
        Product, related_name="assembly_sku", verbose_name="Идентификаторы в сборке", blank=True, null=True
    )
    name = models.CharField(
        verbose_name="Название сборки", blank=False, max_length=255, null=True, unique=True
    )

    user = models.ForeignKey(
        UserProfile, related_name="assembly_user", blank=True, null=True, on_delete=models.PROTECT
    )
