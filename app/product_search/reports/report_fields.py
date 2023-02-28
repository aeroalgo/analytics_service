from statistics import mean

from app.product_search.models import ProductProperty

REPORT_FIELDS_SKELETONS = {
    "main": [
        {
            "title": "Обновлено",
            "value": lambda x: x.days_data.first().date_update
        },
        {
            "title": "Фото",
            "value": lambda x: x.photo.first().photo
        },
        {
            "title": "Ссылка",
            "value": lambda x: x.days_data.first().link
        },
        {
            "title": "Наименование",
            "value": lambda x: x.days_data.first().name
        },
        {
            "title": "Бренд",
            "value": " "
        },
        {
            "title": "Категория",
            "value": lambda x: x.days_data.first().category.name
        },
        {
            "title": "Тип конкуренции",
            "value": lambda x: dict(ProductProperty.COMPETITIONS).get(x.property.first().competition)
        },
        {
            "title": "Последняя цена",
            "value": lambda x: x.days_data.first().last_price
        },
        {
            "title": "Цена 80% продаж",
            "value": lambda x: x.days_data.first().most_sales
        },
        {
            "title": "СПП",
            "value": lambda x: x.days_data.first().client_sale
        },
        {
            "title": "Цена с СПП",
            "value": lambda x: x.days_data.first().client_price
        },
        {
            "title": "Выручка за 30 дней",
            "value": lambda x: x.days_data.first().revenue
        },
        {
            "title": "Средняя цена за 30 дней",
            "value": lambda x: x.days_data.first().final_price_average
        },
        {
            "title": "Средняя в выдаче",
            "value": lambda x: x.days_data.first().categories_pos
        },
        {
            "title": "Дата первого появления",
            "value": lambda x: x.days_data.first().first_date
        },
        {
            "title": "Стартовая цена",
            "value": lambda x: x.days_data.first().start_price
        },
        {
            "title": "Цвет",
            "value": " "
        },
        {
            "title": "Заказы всего",
            "value": lambda x: x.days_data.first().sales
        },
        {
            "title": "Дней в наличии",
            "value": lambda x: x.days_data.first().days_in_stock
        },

    ],
    "advanced": [
        {
            "title": "Размер",
            "value": lambda x: x.title
        },
        {
            "title": "Заказы по размеру",
            "value": lambda x: sum(x.sales)
        },
        {
            "title": "Средний остаток по размеру",
            "value": lambda x: mean(x.balance)
        },
    ],
}
