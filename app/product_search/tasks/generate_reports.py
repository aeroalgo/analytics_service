from app.common.async_task_interface.tasks import AsyncTask
from app.product_search.reports.report import Report


class GenerateReport(AsyncTask):
    """
    Фоновая задача для генерирования отчета
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.assembly_id = kwargs.get("assembly_id")
        self.report_type = kwargs.get("report_type", "xls")

    def process(self):
        report = Report(assembly_id=self.assembly_id, extension="xlsx")
        report.generate_report_xls()
