from app.login import permissions
from app.common.logger.logg import logger
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = "Sync database permissions"

    def handle(self, *awgs, **kwargs):
        content_type, created = ContentType.objects.get_or_create(
            app_label="permissions", model="virtual"
        )

        for group_id, group_name in permissions.BASE_GROUPS:
            group = Group()
            group.id = group_id
            group.name = group_name
            group.save()

            if group_id in permissions.GROUP_RIGHTS:
                logger.info(msg=f"""
                event=sync_permissions__handle
                payload__group_name={group_name}
                """)

                group.permissions.clear()
                for group_permission in permissions.GROUP_RIGHTS[group_id]:
                    permission_name = group_permission.split(".")
                    permission, created = Permission.objects.get_or_create(
                        content_type=content_type,
                        codename=".".join(permission_name[1:]),
                        name=group_permission,
                    )

                    group.permissions.add(permission)
                    logger.info(msg=f"""
                    event="sync_permissions__handle"
                    message="Added permission to group",
                    payload__group_permission={group_permission},
                    payload__group_name={group_name},
                    """)
