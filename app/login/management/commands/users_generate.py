from itertools import islice

from app.common.console.base_generate import BaseGenerate
from django.contrib.auth.models import Group
from django.core.management import BaseCommand
from django.db import connection
from app.common.logger.logg import logger
from app.login.models import UserProfile
from django.contrib.auth.hashers import make_password


class Command(BaseGenerate, BaseCommand):
    help = "Генерирует рандомных пользователей"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--batch_size", action="store", type=int, default=20)
        parser.add_argument("count", type=int)

    def handle(self, *args, **options):
        count = options.get("count")
        batch_size = options.get("batch_size", 20)
        force = options.get("force", False)

        if force:
            self.delete_users()

        client_locks = (self.fake_user() for i in range(count))
        inserted_count = 0
        while True:

            batch = list(islice(client_locks, batch_size))
            if not batch:
                break
            UserProfile.objects.bulk_create(batch, batch_size)

            for user in batch:
                user.groups.add(Group.objects.get(pk=self.fake_user_group()))

            inserted_count += batch_size
            inserted_percent = inserted_count / (count * 0.01)
            logger.info(msg=f"""
            event="users_generate__handle",
            message="Inserted count",
            payload__inserted_count={inserted_count},
            payload__count={count},
            payload__inserted_percent={inserted_percent},
            """)

    @staticmethod
    def delete_users():
        with connection.cursor() as cursor:
            tables = [
                UserProfile.objects.model._meta.db_table + "_user_permissions",
                UserProfile.objects.model._meta.db_table + "_groups",
            ]

            for table in tables:
                logger.info(msg=f"""
                event="delete_users"
                message="delete table"
                payload__table={table}
                """)
                cursor.execute("TRUNCATE %s CASCADE" % table)

            cursor.execute(
                "DELETE FROM %s WHERE id != 1"
                % UserProfile.objects.model._meta.db_table
            )

    def fake_user(self):
        return UserProfile(
            email=self.fake_email(),
            login=self.fake_login(),
            password=make_password(self.fake_password()),
            full_name=self.fake_full_name(),
            first_name=self.fake_first_name(),
            last_name=self.fake_last_name(),
            middle_name=self.fake_middle_name(),
            source_modified=self.fake_datetime()
        )
