#!/usr/bin/env sh

set -e

# Ожидаем запуска postgres
dockerize -wait tcp://${PSQL_HOST_ANALYTICS}:${PSQL_PORT_ANALYTICS}

# Миграция и синхронизация
#./manage.py migrate auth
./manage.py migrate --noinput
./manage.py sync_permissions

# Запуск команды
./manage.py runserver 0.0.0.0:${APP_PORT_ANALYTICS}