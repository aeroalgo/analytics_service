from app.login.models import Direction
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = "Sync database direction"

    def handle(self, *awgs, **kwargs):
        for direction_key, direction_title in Direction.DIRECTIONS:
            direction = Direction.objects.get(key=direction_key)
            print(direction)

