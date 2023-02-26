REPORT_FIELDS_SKELETONS = {
    "main": [
        {
            "title": "Обновлено",
            "value": lambda x: x.date_update
        },
        {
            "title": "Фото",
            "value": lambda x: x.photo
        },
        {
            "title": "Ссылка",
            "value": lambda x: x.date_finish.replace(tzinfo=timezone.utc).astimezone(
                pytz.timezone(settings.TIME_ZONE)
            ),
        },
        {
            "title": "Наименование",
            "value": lambda x, a: round((x.date_finish - a).total_seconds() / 60)
            if x.date_finish is not None and a is not None
            else 0,
        },
        {
            "title": "Бренд",
            "value": lambda x, a: round((x.date_finish - a).total_seconds() / 60)
            if x.date_finish is not None and a is not None
            else 0,
        },
        {
            "title": "Категория",
            "value": lambda x, a: round((x.date_finish - a).total_seconds() / 60)
            if x.date_finish is not None and a is not None
            else 0,
        },
        {
            "title": "Тип конкуренции",
            "value": lambda x, a: round((x.date_finish - a).total_seconds() / 60)
            if x.date_finish is not None and a is not None
            else 0,
        },
        {
            "title": "Последняя цена",
            "value": lambda x, a: round((x.date_finish - a).total_seconds() / 60)
            if x.date_finish is not None and a is not None
            else 0,
        },
        {
            "title": "Цена 80% продаж",
            "value": lambda x, a: round((x.date_finish - a).total_seconds() / 60)
            if x.date_finish is not None and a is not None
            else 0,
        },
        {
            "title": "СПП",
            "value": lambda x, a: round((x.date_finish - a).total_seconds() / 60)
            if x.date_finish is not None and a is not None
            else 0,
        },
        {
            "title": "Цена с СПП",
            "value": lambda x, a: round((x.date_finish - a).total_seconds() / 60)
            if x.date_finish is not None and a is not None
            else 0,
        },
        {
            "title": "Выручка за 30 дней",
            "value": lambda x, a: round((x.date_finish - a).total_seconds() / 60)
            if x.date_finish is not None and a is not None
            else 0,
        },
        {
            "title": "Средняя цена за 30 дней",
            "value": lambda x, a: round((x.date_finish - a).total_seconds() / 60)
            if x.date_finish is not None and a is not None
            else 0,
        },
        {
            "title": "Средняя в выдаче",
            "value": lambda x, a: round((x.date_finish - a).total_seconds() / 60)
            if x.date_finish is not None and a is not None
            else 0,
        },
        {
            "title": "Дата первого появления",
            "value": lambda x, a: round((x.date_finish - a).total_seconds() / 60)
            if x.date_finish is not None and a is not None
            else 0,
        },
        {
            "title": "Стартовая цена",
            "value": lambda x, a: round((x.date_finish - a).total_seconds() / 60)
            if x.date_finish is not None and a is not None
            else 0,
        },
        {
            "title": "Цвет",
            "value": lambda x, a: round((x.date_finish - a).total_seconds() / 60)
            if x.date_finish is not None and a is not None
            else 0,
        },
        {
            "title": "Заказы всего",
            "value": lambda x, a: round((x.date_finish - a).total_seconds() / 60)
            if x.date_finish is not None and a is not None
            else 0,
        },
        {
            "title": "Дней в наличии",
            "value": lambda x, a: round((x.date_finish - a).total_seconds() / 60)
            if x.date_finish is not None and a is not None
            else 0,
        },

    ],
    "advanced": [
        {
            "title": "Размер",
            "value": lambda x: x.user.position_state_relation.title
            if x.user.position_state_relation is not None
            else "Не указано",
        },
        {
            "title": "Заказы по размеру",
            "value": lambda x: x.user.get_full_name()
        },
        {
            "title": "Средний остаток по размеру",
            "value": lambda x: x.user.user_principal_name
        },
    ],
}
