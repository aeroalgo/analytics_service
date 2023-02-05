import time
import datetime
from urllib.parse import quote
from app.analytics.settings import env
from app.common.logger.logg import logger
from dateutil.rrule import rrule, MONTHLY
from app.product_search.models import ProductProperty, Product, PeriodData, Last30DaysData, Categories
from app.common.async_task_interface.interface import ProcessAsyncTask
from app.product_search.tasks.maincrawler import Pool, ExtractData, Task


class ParseSkuWB(ExtractData):

    def get_payload(self, sku):
        return {"startRow": 0, "endRow": 100,
                "filterModel": {"id": {"filterType": "number", "type": "equals", "filter": sku, "filterTo": None}},
                "sortModel": [{"colId": "revenue", "sort": "desc"}]}

    def get_date(self, delta: int):
        d2 = datetime.datetime.now() - datetime.timedelta(days=1)
        d2 = d2.date()
        d1 = d2 - datetime.timedelta(days=delta)
        return d1, d2

    def get_period_date(self, first_date):
        dates = []
        first_date = datetime.datetime.strptime(first_date, '%Y-%m-%d').date()

        now = datetime.datetime.now().date()
        now = now - datetime.timedelta(days=now.day - 1)

        start_date = datetime.datetime.now().date() - datetime.timedelta(weeks=52)
        if first_date < start_date:
            day_delta = start_date.day
            start_date = start_date - datetime.timedelta(days=day_delta - 1)
        else:
            day_delta = first_date.day
            start_date = first_date - datetime.timedelta(days=day_delta - 1)
        freq_date = list(rrule(freq=MONTHLY, count=13, dtstart=start_date))

        for idx, date in enumerate(freq_date):
            if date == datetime.datetime.strptime(str(now), '%Y-%m-%d'):
                break
            if idx + 1 != len(freq_date):
                dates.append({
                    "d1": freq_date[idx].date(),
                    "d2": freq_date[idx + 1].date()
                })
        return dates

    def start_extract(self, response, headers, cookie):
        next_tasks = []
        item = response.get('item')
        item_brand = item.get('brand')
        item_id = item.get('id')
        item_first_date = item.get('first_date')
        dates = self.get_period_date(item_first_date)
        NEXT_URL = 'https://mpstats.io/api/wb/get/brand?d1={d1}&d2={d2}&path={item_brand}'
        logger.info(response)
        payload = self.get_payload(item_id)
        product = Product.objects.get(sku=item_id)
        exist_date = list(PeriodData.objects.filter(sku_id=product.id).values_list('date_start', flat=True))
        for date in dates:
            if date["d1"] not in exist_date:
                cd_kwargs = {
                    "item_id": item_id,
                    "d1": date["d1"],
                    "d2": date["d2"]
                }

                next_tasks.append(Task(url=NEXT_URL.format(d1=date["d1"], d2=date["d2"], item_brand=item_brand),
                                       headers=headers.copy(), callback=self.get_brand_data_period,
                                       payload=payload, cd_kwargs=cd_kwargs.copy()))

        d1, d2 = self.get_date(delta=30)
        cd_kwargs = {
            "item_id": item_id,
            "d1": d1,
            "d2": d2
        }
        now = datetime.datetime.now().date()
        data = Last30DaysData.objects.filter(sku_id=product.id, date_update=now)
        if not data:
            next_tasks.append(Task(url=NEXT_URL.format(d1=d1, d2=d2, item_brand=item_brand),
                                   headers=headers.copy(), callback=self.get_brand_data_30days,
                                   payload=payload, cd_kwargs=cd_kwargs.copy()))
        return next_tasks

    def get_brand_data_30days(self, response, headers, cookie, payload, cd_kwargs):
        next_tasks = []
        NEXT_URL = "https://mpstats.io/api/wb/get/item/{sku}/by_category?d1={d1}&d2={d2}"
        item = response.get("data")[0]
        source, _ = Categories.objects.get_or_create(name=item.get("category"))
        product = Product.objects.get(sku=cd_kwargs.get("item_id"))
        instance = Last30DaysData()
        instance.sku = product
        instance.first_date = item.get("sku_first_date")
        instance.revenue = item.get("revenue")
        instance.final_price_average = item.get("final_price_average")
        instance.sales = item.get("sales")
        instance.rating = item.get("rating")
        instance.comments = item.get("comments")
        instance.category = source
        instance.start_price = item.get("start_price")
        now = datetime.datetime.now().date()
        data = Last30DaysData.objects.filter(sku_id=product.id, date_update=now)
        if not data:
            instance.save()
        # next_tasks.append(
        #     Task(url=NEXT_URL.format(d1=cd_kwargs.get("d1"), d2=cd_kwargs.get("d2"), sku=cd_kwargs.get("item_id")),
        #          headers=headers.copy(), callback=self.get_category_pos, cd_kwargs=cd_kwargs.copy()))
        # return next_tasks

    def get_category_pos(self, response, headers, cookie, payload, cd_kwargs):
        now = datetime.datetime.now().date()
        product = Product.objects.get(sku=cd_kwargs.get("item_id"))
        # print(response)
        # Last30DaysData.objects.filter(sku_id=product.id, date_update=now).update()
        pass

    def get_brand_data_period(self, response, headers, cookie, payload, cd_kwargs):
        item = response.get("data")[0]
        source, _ = Categories.objects.get_or_create(name=item.get("category"))
        product = Product.objects.get(sku=cd_kwargs.get("item_id"))
        instance = PeriodData()
        instance.sku = product
        instance.date_start = cd_kwargs.get("d1")
        instance.date_end = cd_kwargs.get("d2")
        instance.lost_profit = item.get("lost_profit")
        instance.revenue = item.get("revenue")
        instance.final_price_average = item.get("final_price_average")
        instance.sales = item.get("sales")
        instance.category = source

        exist_date = list(PeriodData.objects.filter(sku_id=product.id).values_list('date_start', flat=True))
        if cd_kwargs.get("d1") not in exist_date:
            instance.save()


class ParseSkuOzon(ExtractData):
    def start_extract(self, response, headers, cookie):
        print(response)


class GetSku(Pool):
    GET_ITEM_SKU = {
        ProductProperty.MP_WB: "https://mpstats.io/api/wb/get/item/{sku}",
        ProductProperty.MP_OZON: "https://mpstats.io/api/oz/get/item/{sku}"
    }
    HEADERS = {
        "X-Mpstats-TOKEN": f"{env('MP_STATS_TOKEN')}",
        "Content-Type": "application/json"
    }
    EXTRACT_DATA_CLASSES = {
        ProductProperty.MP_WB: ParseSkuWB(),
        ProductProperty.MP_OZON: ParseSkuOzon()
    }

    def __init__(self, *args, **kwargs):
        self.skus = kwargs.get("skus")
        self.mp = kwargs.get("mp")
        self.extract_data_class = self.EXTRACT_DATA_CLASSES.get(self.mp)

        self.max_rate = 10
        super().__init__(max_rate=self.max_rate, extract_data_class=self.extract_data_class,
                         param={
                             "skus": self.skus,
                             "mp": self.mp
                         })

    def process(self):
        for sku in self.skus:
            self.start_url.append({
                'url': self.GET_ITEM_SKU.get(self.mp).format(sku=sku),
                'headers': self.HEADERS,
            })
        self.create_first_tasks()
        return {"status": "ok"}

    def finalize(self):
        return True
