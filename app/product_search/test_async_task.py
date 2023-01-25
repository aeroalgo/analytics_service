import time
import traceback

from django.core.cache import cache

from app.common.async_task_interface.tasks import AsyncTask


class GeneratePollReport(AsyncTask):
    """
    Фоновая задача для генерирования отчета
    """

    def __init__(self, *args, **kwargs):
        self.report_type = kwargs.get("report_type", "XLS")
        self.report_format = kwargs.get("report_format", 1)
        super().__init__(param={
            "report_type": self.report_type,
            "report_format": self.report_format
        })

    def process(self):
        for i in range(100):
            time.sleep(5)
            print(i)

    def finalize(self):
        return True
