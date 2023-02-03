import time
import datetime
from urllib.parse import quote

import orjson

from app.analytics.settings import env
from app.common.logger.logg import logger
from app.product_search.models import ProductProperty
from app.common.async_task_interface.interface import ProcessAsyncTask
from app.product_search.tasks.maincrawler import Pool, ExtractData, Task


class ParseSkuWB(ExtractData):

    def get_payload(self, sku):
        # return {"startRow": 0, "endRow": 100,
        #         "filterModel": {"id": {"filterType": "number", "type": "equals", "filter": sku, "filterTo": None}},
        #         "sortModel": [{"colId": "revenue", "sort": "desc"}]}

        return '{{"filterModel":' \
               '{{"id":{{"filterType":"number","type":"equals","filter":{sku},"filterTo":null}}}},' \
               '"sortModel":[{{"colId":"revenue","sort":"desc"}}]}}'.format(sku=sku)

    def get_date(self, delta: int):
        d2 = datetime.datetime.now() - - datetime.timedelta(days=1)
        d2 = d2.date()
        d1 = d2 - datetime.timedelta(days=delta)
        return d1, d2

    def start_extract(self, response, headers, cookie):
        next_tasks = []
        d1, d2 = self.get_date(delta=1)
        NEXT_URL = 'https://mpstats.io/api/wb/get/brand?d1={d1}&d2={d2}&path={item_brand}'
        logger.info(response)
        item = response.get('item')
        item_brand = item.get('brand')
        item_id = item.get('id')
        cd_kwargs = {
            "item_id": item_id
        }
        payload = orjson.loads(self.get_payload(cd_kwargs.get("item_id")))
        next_tasks.append(Task(url=NEXT_URL.format(d1=d1, d2=d2, item_brand=item_brand),
                               headers=headers.copy(), callback=self.get_category,
                               string_data=payload, cd_kwargs=cd_kwargs))
        return next_tasks

    def get_category(self, response, headers, cookie, payload, cd_kwargs):
        next_tasks = []
        d1, d2 = self.get_date(delta=10)
        NEXT_URL = "http://mpstats.io/api/wb/get/category?d1={d1}&d2={d2}&path={quote}"
        data = response.get("data")

        item_category = ''
        for item in data:
            item_category = item.get("category")
            if item_category:
                break

        logger.info(cd_kwargs)
        logger.info(NEXT_URL.format(d1=d1, d2=d2, quote=quote(item_category)))
        payload = orjson.loads(self.get_payload(cd_kwargs.get("item_id")))

        next_tasks.append(Task(url=NEXT_URL.format(d1=d1, d2=d2, quote=quote(item_category)),
                               headers=headers.copy(), callback=self.get_category_data,
                               string_data=payload))
        return next_tasks

    def get_category_data(self, response, headers, cookie, payload, cd_kwargs):
        logger.info(payload)
        logger.info(response)


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

    def __init__(self, *args, **kwargs):
        self.skus = kwargs.get("skus")
        self.mp = kwargs.get("mp")
        self.extract_data_classes = {
            ProductProperty.MP_WB: ParseSkuWB(),
            ProductProperty.MP_OZON: ParseSkuOzon()
        }
        self.extract_data_class = self.extract_data_classes.get(self.mp)

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
                # "payload": self.PAYLOADS.get(self.mp).format(sku=sku)
            })
        self.create_first_tasks()
        return {"status": "ok"}

    def finalize(self):
        return True
