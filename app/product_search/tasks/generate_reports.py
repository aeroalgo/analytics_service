from app.common.async_task_interface.tasks import AsyncTask


class GeneratePollReport(AsyncTask):
    """
    Фоновая задача для генерирования отчета
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.assembly_id = kwargs.get("assembly_id")
        self.report_type = kwargs.get("report_type", "XLS")

    def process(self):
        pass
