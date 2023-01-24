import traceback

from django.core.cache import cache

from app.common.async_task_interface.tasks import AsyncTask


class GeneratePollReport(AsyncTask):
    """
    Фоновая задача для генерирования отчета
    """

    task_data_props = [
        "poll_id",
        "task_id",
        "report_settings",
        "report_type",
        "report_format",
        "user_id",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = kwargs.get("user_id")
        self.poll_id = kwargs.get("poll_id")
        self.report_settings = kwargs.get("report_settings")
        self.report_type = kwargs.get("report_type", "XLS")
        self.report_format = kwargs.get("report_format", 1)

    def process(self):
        for i in range(100000):
            print(i)

    def finalize(self):
        return True
