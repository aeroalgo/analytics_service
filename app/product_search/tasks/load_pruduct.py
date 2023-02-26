import time
import datetime
from typing import List
from urllib.parse import quote
from app.analytics.settings import env
from app.common.logger.logg import logger
from dateutil.rrule import rrule, MONTHLY
from app.product_search.tasks.mixins import ParseSkuMixin
from app.common.async_task_interface.interface import ProcessAsyncTask
from app.product_search.tasks.maincrawler import Pool, ExtractData, Task
from app.product_search.models import ProductProperty, Product, PeriodData, Last30DaysData, Categories, ProductPhoto, \
    SizeProduct


class LoadData(ParseSkuMixin):

    def add_brand_data_period(self, response, cd_kwargs):
        item = response.get("data")[0]
        category, is_created = Categories.objects.get_or_create(name=item.get("category"))
        if is_created:
            category = Categories.objects.get(name=item.get("category"))
        product = Product.objects.get(sku=cd_kwargs.get("item_id"))
        instance = PeriodData()
        instance.sku = product
        instance.date_start = cd_kwargs.get("d1")
        instance.date_end = cd_kwargs.get("d2")
        instance.lost_profit = item.get("lost_profit")
        instance.revenue = item.get("revenue")
        instance.final_price_average = item.get("final_price_average")
        instance.sales = item.get("sales")
        instance.category = category
        exist_date = list(PeriodData.objects.filter(sku_id=product.id).values_list('date_start', flat=True))
        if cd_kwargs.get("d1") not in exist_date:
            instance.save()

    def add_brand_data_30days(self, response, cd_kwargs):
        item = response.get("data")[0]
        category, is_created = Categories.objects.get_or_create(name=item.get("category"))
        if is_created:
            category = Categories.objects.get(name=item.get("category"))
        product = Product.objects.get(sku=cd_kwargs.get("item_id"))
        exist = Last30DaysData.objects.filter(sku=product.id)
        exist_photo = ProductPhoto.objects.filter(sku=product.id)
        if exist:
            instance = exist[0]
        else:
            instance = Last30DaysData()
        instance.sku = product
        instance.first_date = item.get("sku_first_date")
        instance.revenue = item.get("revenue")
        instance.final_price_average = item.get("final_price_average")
        instance.sales = item.get("sales")
        instance.rating = item.get("rating")
        instance.date_update = datetime.datetime.now().date()
        instance.comments = item.get("comments")
        instance.category = category
        instance.last_price = item.get("final_price")
        instance.graph = item.get("graph")
        instance.price_graph = item.get("price_graph")
        instance.name = item.get("name")
        instance.client_sale = item.get("client_sale")
        instance.client_price = item.get("client_price")
        instance.days_in_stock = item.get("days_in_stock")
        instance.most_sales = self.most_sales(graph=item.get("graph"), price_graph=item.get("price_graph"))
        now = datetime.datetime.now().date()
        data = Last30DaysData.objects.filter(sku_id=product.id, date_update=now)
        if exist_photo:
            instance_photo = exist_photo[0]
        else:
            instance_photo = ProductPhoto()
        instance_photo.sku = product
        instance_photo.link = cd_kwargs.get('item_photo_url')
        instance_photo.filename = cd_kwargs.get('item_photo_url').split("/")[-1]
        instance_photo.get_remote_image()
        if not data:
            instance.save()

    def add_size_data(self, response, cd_kwargs):
        result = {}
        for val in response.values():
            for size, data in val.items():
                if size in result.keys():
                    for key, values in data.items():
                        if key in ('sales', 'balance'):
                            result.get(size).get(key).append(values)
                else:
                    result[size] = {
                        "sales": [data.get("sales")],
                        "balance": [data.get("balance")],
                        "size_name": data.get("size_name"),
                        "size_origin": data.get("size_origin"),
                    }
        product = Product.objects.get(sku=cd_kwargs.get("item_id"))
        SizeProduct.objects.filter(sku=product.id).delete()
        all_size = []
        print(result)
        for size, data in result.items():
            instance = SizeProduct()
            instance.sku = product
            instance.sales = data.get("sales")
            instance.size_name = data.get("size_name")
            instance.size_origin = data.get("size_origin")
            instance.title = size
            instance.balance = data.get("balance")
            all_size.append(instance)
        SizeProduct.objects.bulk_create(all_size)




class ParseSkuWB(ExtractData, ParseSkuMixin):

    def get_payload(self, sku):
        return {"startRow": 0, "endRow": 100,
                "filterModel": {"id": {"filterType": "number", "type": "equals", "filter": sku, "filterTo": None}},
                "sortModel": [{"colId": "revenue", "sort": "desc"}]}

    def start_extract(self, response, headers, cookie):
        next_tasks = []
        item = response.get('item')
        item_brand = item.get('brand')
        item_id = item.get('id')
        item_first_date = item.get('first_date')
        item_photo_url = response.get('photos')[0].get('f')
        dates = self.get_period_date(item_first_date)
        NEXT_URL = 'https://mpstats.io/api/wb/get/brand?d1={d1}&d2={d2}&path={item_brand}'
        logger.info(response)
        payload = self.get_payload(item_id)
        product = Product.objects.get(sku=item_id)
        exist_date = list(PeriodData.objects.filter(sku_id=product.id).values_list('date_start', flat=True))
        d1, d2 = self.get_date(delta=30)

        cd_kwargs = {
            "clothes": False,
            "item_id": item_id,
            "item_photo_url": "https:" + item_photo_url,
            "d1": d1,
            "d2": d2
        }
        item_sizeandstores = item.get('sizeandstores', False)
        if item_sizeandstores:
            cd_kwargs["clothes"] = True
        next_tasks.append(Task(url=NEXT_URL.format(d1=d1, d2=d2, item_brand=quote(item_brand)),
                               headers=headers.copy(), callback=self.get_brand_data_30days,
                               payload=payload, cd_kwargs=cd_kwargs.copy()))
        for date in dates:
            if date["d1"] not in exist_date:
                cd_kwargs = {
                    "item_id": item_id,
                    "d1": date["d1"],
                    "d2": date["d2"]
                }

                next_tasks.append(Task(url=NEXT_URL.format(d1=date["d1"], d2=date["d2"], item_brand=quote(item_brand)),
                                       headers=headers.copy(), callback=self.get_brand_data_period,
                                       payload=payload, cd_kwargs=cd_kwargs.copy()))

        return next_tasks

    def get_brand_data_30days(self, response, headers, cookie, payload, cd_kwargs):
        next_tasks = []
        NEXT_URL = "https://mpstats.io/api/wb/get/item/{sku}/orders_by_size?d1={d1}&d2={d2}"
        logger.info(response)
        load = LoadData()
        load.add_brand_data_30days(response=response, cd_kwargs=cd_kwargs)
        if cd_kwargs.get("clothes"):
            next_tasks.append(
                Task(url=NEXT_URL.format(d1=cd_kwargs.get("d1"), d2=cd_kwargs.get("d2"), sku=cd_kwargs.get("item_id")),
                     headers=headers.copy(), callback=self.get_size_data, cd_kwargs=cd_kwargs.copy()))
        return next_tasks

    def get_size_data(self, response, headers, cookie, payload, cd_kwargs):
        load = LoadData()
        load.add_size_data(response=response, cd_kwargs=cd_kwargs)

    def get_category_pos(self, response, headers, cookie, payload, cd_kwargs):
        now = datetime.datetime.now().date()
        product = Product.objects.get(sku=cd_kwargs.get("item_id"))
        # print(response)
        # Last30DaysData.objects.filter(sku_id=product.id, date_update=now).update()
        pass

    def get_brand_data_period(self, response, headers, cookie, payload, cd_kwargs):
        logger.info(response)
        load = LoadData()
        load.add_brand_data_period(response=response, cd_kwargs=cd_kwargs)


class ParseSkuOzon(ExtractData, ParseSkuMixin):

    def get_payload(self, sku):
        return {"startRow": 0, "endRow": 100,
                "filterModel": {"delivery_scheme": {"values": ["0", "1"], "filterType": "set"},
                                "id": {"filterType": "number", "type": "equals", "filter": sku,
                                       "filterTo": None}}, "sortModel": [{"colId": "revenue", "sort": "desc"}]}

    def start_extract(self, response, headers, cookie):
        next_tasks = []
        item = response.get('item')
        item_brand = item.get('brand')
        item_id = item.get('id')
        item_first_date = item.get('first_date')
        pk = Product.objects.get(sku=item_id).id
        exist_date = []
        if item_first_date is None:
            exist_date = list(PeriodData.objects.filter(sku_id=pk).order_by(
                "date_start").values_list("date_start", flat=True))
            if exist_date:
                item_first_date = exist_date[0]
        dates = self.get_period_date(item_first_date, db_date=True)
        NEXT_URL = 'https://mpstats.io/api/oz/get/brand?d1={d1}&d2={d2}&path={item_brand}'
        logger.info(response)
        payload = self.get_payload(item_id)
        d1, d2 = self.get_date(delta=30)
        cd_kwargs = {
            "item_id": item_id,
            "d1": d1,
            "d2": d2
        }
        next_tasks.append(Task(url=NEXT_URL.format(d1=d1, d2=d2, item_brand=quote(item_brand)),
                               headers=headers.copy(), callback=self.get_brand_data_30days,
                               payload=payload, cd_kwargs=cd_kwargs.copy()))
        for date in dates:
            if date["d1"] not in exist_date:
                cd_kwargs = {
                    "item_id": item_id,
                    "d1": date["d1"],
                    "d2": date["d2"]
                }

                next_tasks.append(Task(url=NEXT_URL.format(d1=date["d1"], d2=date["d2"], item_brand=quote(item_brand)),
                                       headers=headers.copy(), callback=self.load_data_period,
                                       payload=payload, cd_kwargs=cd_kwargs.copy()))
        return next_tasks

    def get_brand_data_30days(self, response, headers, cookie, payload, cd_kwargs):
        next_tasks = []
        NEXT_URL = "https://mpstats.io/api/wb/get/item/{sku}/by_category?d1={d1}&d2={d2}"
        logger.info(response)
        load = LoadData()
        load.add_brand_data_30days(response=response, cd_kwargs=cd_kwargs)
        # next_tasks.append(
        #     Task(url=NEXT_URL.format(d1=cd_kwargs.get("d1"), d2=cd_kwargs.get("d2"), sku=cd_kwargs.get("item_id")),
        #          headers=headers.copy(), callback=self.get_category_pos, cd_kwargs=cd_kwargs.copy()))
        # return next_tasks

    def get_size_data(self):
        pass

    def load_data_period(self, response, headers, cookie, payload, cd_kwargs):
        logger.info(response)
        load = LoadData()
        load.add_brand_data_period(response=response, cd_kwargs=cd_kwargs)


class GetSku(Pool):
    GET_ITEM_SKU = {
        Product.MP_WB: "https://mpstats.io/api/wb/get/item/{sku}",
        Product.MP_OZON: "https://mpstats.io/api/oz/get/item/{sku}"
    }
    HEADERS = {
        "X-Mpstats-TOKEN": f"{env('MP_STATS_TOKEN')}",
        "Content-Type": "application/json"
    }
    EXTRACT_DATA_CLASSES = {
        Product.MP_WB: ParseSkuWB(),
        Product.MP_OZON: ParseSkuOzon()
    }

    def __init__(self, *args, **kwargs):
        self.skus: List = kwargs.get("skus")
        self.mp: int = kwargs.get("mp")
        self.extract_data_class = self.EXTRACT_DATA_CLASSES.get(self.mp)

        self.max_rate = 10
        super().__init__(max_rate=self.max_rate, extract_data_class=self.extract_data_class,
                         param={
                             "skus": self.skus,
                             "mp": self.mp
                         })

    def process(self):
        for sku in self.skus:
            product = Product.objects.get(sku=sku)
            now = datetime.datetime.now().date()
            data = Last30DaysData.objects.filter(sku_id=product.id, date_update=now)
            if not data:
                self.start_url.append({
                    'url': self.GET_ITEM_SKU.get(self.mp).format(sku=sku),
                    'headers': self.HEADERS,
                })
            else:
                logger.info(msg=f"""
                event=update_sku
                payload__sku_id={sku}
                message="Дата обновления = Дата сегодня Обновление не трубется"
                                """)
        if self.start_url:
            self.create_first_tasks()
        return {"status": "ok"}

    def finalize(self):
        return True
