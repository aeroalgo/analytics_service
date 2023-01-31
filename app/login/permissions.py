# Файл настроек групп и прав на все приложения
# БД – не используем для простоты синхронизации

# id групп пользователей
ROLE_ADMINISTRATOR_SYSTEM = 0
ROLE_DIRECTOR = 1
ROLE_MANAGER = 2
ROLE_PRODUCT = 3

BASE_GROUPS = (
    (ROLE_ADMINISTRATOR_SYSTEM, "Админ системы"),
    (ROLE_DIRECTOR, "Директор"),
    (ROLE_MANAGER, "Руководитель"),
    (ROLE_PRODUCT, "Продакт"),
)

# Группы, имеющие право добавлять контент – для фильтров на клиенте;
# можно в цикле GROUP_RIGHTS на право редактирования проверять – потом

GROUP_RIGHTS = {}

"""
Список доступных прав, возможности:
- permissions.login – вход в систему

- permissions.system.settings – менять настройки системы

- permissions.common.search – искать в системе что-либо

- permissions.article.see_all – видеть все товары
- permissions.article.see – видеть товары своего направления
- permissions.article.add – закреплять товары своего направления
_ permissions.article.add_all - закреплять все товары 

– permissions.users.index – просматривать пользователей
– permissions.users.edit – редактировать пользователей

"""

GROUP_RIGHTS[ROLE_ADMINISTRATOR_SYSTEM] = [
    "permissions.admin.@superuser",
    "permissions.admin.index",
    "permissions.login",
    "permissions.users.edit",
    "permissions.users.index",

]

GROUP_RIGHTS[ROLE_DIRECTOR] = [
    "permissions.login",
    "permissions.common.search",
    "permissions.article.see_all",
    "permissions.article.add_all",
    "permissions.users.index"

]

GROUP_RIGHTS[ROLE_MANAGER] = [
    "permissions.login",
    "permissions.common.search",
    "permissions.article.see"
    "permissions.article.add"
    "permissions.users.index"
    ""
]

GROUP_RIGHTS[ROLE_PRODUCT] = [
    "permissions.login",
    "permissions.common.search",
    "permissions.article.see"
]
