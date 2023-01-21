from django.core import serializers
from app.login.interface import Serializer


class ProfileSerializer(Serializer):
    fields = ("email", "login", "full_name", "direction", "groups__name", "is_active",)


class GroupDirectionSerializer(Serializer):
    fields = ("name",)
