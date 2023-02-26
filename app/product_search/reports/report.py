import datetime
import xlsxwriter
from app.analytics import settings
from app.product_search.reports.report_fields import REPORT_FIELDS_SKELETONS


class Report:
    def __init__(self, assembly_id, extension):
        self.assembly_id = assembly_id
        self.extension = extension
        self.worksheet_main = None
        self.workbook = None

    def get_fields(self, assembly):
        fields = REPORT_FIELDS_SKELETONS.get("main", []).copy()
        fields += REPORT_FIELDS_SKELETONS.get("advanced", []).copy()
        return fields

    @staticmethod
    def get_report_path(assembly_id, extension):
        """Генерация пути до отчета."""
        file_path = datetime.datetime.now().strftime(
            "reports/%%Y-%%m/assembly_{assembly_id}.{extension}".format(assembly_id=assembly_id,
                                                                    extension=extension)
        )
        full_path = settings.MEDIA_ROOT + "/" + file_path

        if not os.path.exists(os.path.dirname(full_path)):
            os.makedirs(os.path.dirname(full_path))

        return file_path, full_path

    def generate_report_xls(self):
        file_path, full_path = self.get_report_path(
            assembly_id=self.assembly_id, extension=self.extension
        )
        self.workbook = xlsxwriter.Workbook(full_path, {"remove_timezone": True})
