import datetime
from django.db import models
from django.contrib.auth.models import UserManager
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager

from app.login.serializers import ProfileSerializer, GroupDirectionSerializer

class Direction(models.Model):
    DIRECTION_VTMP = 0
    DIRECTION_GFG = 1
    DIRECTION_OPR = 2
    DIRECTION_KITCHEN = 3
    DIRECTIONS = (
        (DIRECTION_VTMP, "ВТМП"),
        (DIRECTION_GFG, "ГФГ"),
        (DIRECTION_OPR, "ОПР"),
        (DIRECTION_KITCHEN, "Кухня"),
    )

    name = models.CharField(
        verbose_name="Название направления", blank=False, max_length=255, null=True, unique=True
    )
    key = models.CharField(
        verbose_name="Ключ направления", blank=False, max_length=255, null=True
    )

    class Meta:
        managed = False
        app_label = 'login'


class UserProfile(models.Model):
    login = models.CharField(
        "Логин", max_length=255, blank=False, null=True, unique=True
    )
    password = models.CharField(
        "Пароль", max_length=128, default=None, blank=True, null=True
    )
    last_name = models.CharField("Фамилия", max_length=255, blank=False, null=True)
    first_name = models.CharField("Имя", max_length=255, blank=False, null=True)
    middle_name = models.CharField("Отчество", max_length=255, blank=True, null=True)
    full_name = models.CharField("ФИО", max_length=255, blank=True, null=True)
    email = models.EmailField("Email", blank=True, null=True)
    source_modified = models.DateField(
        "Дата изменения в источнике", blank=False, default=datetime.date(1970, 1, 1)
    )
    direction = models.ManyToManyField(
        Direction, verbose_name="Направление", related_name="user_direction", blank=False
    )
    is_staff = models.BooleanField("Персонал", default=False)
    is_active = models.BooleanField("Активный", default=True)


    class Meta:
        managed = False
        app_label = 'login'

    @staticmethod
    def profile_information(id):
        """Забираем информацию по профилю"""
        # Профиль
        user = UserProfile.objects.get(id=id)
        data = ProfileSerializer(data=[user])
        data.serialize()
        profile_data = data.to_dict[0]
        # Группы
        groups = GroupDirectionSerializer(user.groups.all())
        groups.serialize()
        groups = groups.to_dict
        # Направления
        directions = GroupDirectionSerializer(user.direction.all())
        directions.serialize()
        directions = directions.to_dict
        return {"user": user, "profile": profile_data, "groups": groups, "directions": directions}
