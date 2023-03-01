from app.login.models import Direction
from app.common.logger.logg import logger
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = "Sync database direction"

    def handle(self, *awgs, **kwargs):
        for direction_key, direction_title in Direction.DIRECTIONS:
            direction = Direction.objects.get_or_create(key=direction_key, name=direction_title)
            logger.info(msg=f"""
            event=sync_permissions__handle,
            payload__group_name={direction_title}
            """)
