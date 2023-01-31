import datetime
from django.db import models
from django.contrib.auth.models import UserManager
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager

from app.login.serializers import ProfileSerializer, GroupDirectionSerializer


class MyUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, login, password, **extra_fields):
        """
        Creates and saves a User with the given username, email and password.
        """
        login = self.normalize_email(login)
        user = self.model(login=login, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, login=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(login, password, **extra_fields)

    def create_superuser(self, login, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(login, password, **extra_fields)


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


class UserProfile(AbstractBaseUser, PermissionsMixin):
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

    objects = MyUserManager()

    USERNAME_FIELD = "login"

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
