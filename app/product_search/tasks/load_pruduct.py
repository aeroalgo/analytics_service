import datetime
import time

from app.analytics.settings import env
from app.common.logger.logg import logger
from app.product_search.models import ProductProperty
from app.product_search.tasks.maincrawler import Pool, ExtractData


class ParseSkuWB(ExtractData):
    def start_extract(self, response, headers, cookie):
        logger.info(response)


class ParseSkuOzon(ExtractData):
    def start_extract(self, response, headers, cookie):
        print(response)


class GetSku(Pool):
    GET_ITEM_SKU = {
        ProductProperty.MP_WB: "http://mpstats.io/api/wb/get/category?d1={d1}&d2={d2}&path=%D0%96%D0%B5%D0%BD%D1%89%D0%B8%D0%BD%D0%B0%D0%BC/%D0%9E%D0%B4%D0%B5%D0%B6%D0%B4%D0%B0"
    }
    HEADERS = {
        "X-Mpstats-TOKEN": f"{env('MP_STATS_TOKEN')}",
        "Content-Type": "application/json"
    }
    PAYLOADS = {
        ProductProperty.MP_WB: """{{"startRow":0,"endRow":100,"filterModel":{{"id":
        {{"filterType":"number","type":"equals","filter":{sku},"filterTo":null}},
        "sortModel":[{{"colId":"revenue","sort":"desc"}}]}}"""
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
            d1 = datetime.datetime.now() - datetime.timedelta(weeks=4)
            d1 = d1.date()
            d2 = datetime.datetime.now()
            d2 = d2.date()
            self.start_url.append({
                'url': self.GET_ITEM_SKU.get(self.mp).format(d1=d1, d2=d2),
                'headers': self.HEADERS,
                "payload": self.PAYLOADS.get(self.mp).format(sku=sku)
            })
        self.create_first_tasks()
        return True

    def get_item_sku(self):
        pass

    def finalize(self):
        return True
