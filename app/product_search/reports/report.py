import collections
import json
import os
import datetime
import xlsxwriter
from PIL import Image
from decimal import Decimal
from app.analytics import settings
from app.common.utils import clean_html
from app.product_search.models import Assembly, Product
from app.product_search.reports.report_fields import REPORT_FIELDS_SKELETONS


class Report:
    def __init__(self, assembly_id, extension):
        self.assembly_id = assembly_id
        self.extension = extension
        self.worksheet_main = None
        self.cached_questions = {}
        self.formats = {}
        self.workbook = None

    def get_fields(self, assembly):
        fields = REPORT_FIELDS_SKELETONS.get("main", []).copy()
        if assembly.type == Assembly.TYPE_CLOTHES:
            fields += REPORT_FIELDS_SKELETONS.get("advanced", []).copy()
        return fields

    @staticmethod
    def get_report_path(assembly_name, extension):
        """Генерация пути до отчета."""
        file_path = datetime.datetime.now().strftime(
            "reports/%Y-%m/assembly_{assembly_name}.{extension}"
        ).format(assembly_name=assembly_name, extension=extension)
        full_path = settings.MEDIA_ROOT + "/" + file_path

        if not os.path.exists(os.path.dirname(full_path)):
            os.makedirs(os.path.dirname(full_path))

        return file_path, full_path

    def joinable(self, arr):
        result = []
        for item in arr:
            val = item
            if isinstance(item, Decimal):
                val = round(item, 2)
            val = str(val)
            result.append(val)
        return result

    def clean_html(self, html):
        return clean_html(html)

    def write_value(self, row, offset, value, worksheet, style={}):
        """Запись значения в ячейку."""
        row_style = style

        cell_value = value
        if isinstance(value, list):
            if len(value) > 1:
                cell_value = "– " + ("\n– ".join(self.joinable(value)))
            else:
                cell_value = value[0]

        if isinstance(cell_value, datetime.datetime):
            row_style["num_format"] = "dd.mm.yyyy hh:mm"
        elif isinstance(cell_value, datetime.date):
            row_style["num_format"] = "dd.mm.yyyy"
        elif isinstance(cell_value, datetime.time):
            row_style["num_format"] = "hh:mm"
        elif isinstance(cell_value, int) or (
              isinstance(cell_value, str) and cell_value.isdigit()
        ):
            cell_value = int(cell_value)
            row_style["num_format"] = "0"
        elif isinstance(cell_value, float):
            row_style["num_format"] = "#,##0.00"
            if float(cell_value) == int(cell_value):
                row_style["num_format"] = "0"
                cell_value = int(cell_value)
        elif cell_value is None:
            cell_value = ""
        else:
            cell_value_clean = self.cached_questions.get(cell_value)
            if cell_value_clean is None:
                try:
                    self.cached_questions[cell_value] = self.clean_html(cell_value)
                except Exception as e:
                    print(e)
            cell_value = self.cached_questions.get(cell_value)
            row_style["num_format"] = "0"
        if cell_value and isinstance(cell_value, str):
            row_style["num_format"] = "@"
            cell_value = cell_value[1:] if cell_value[0] == "=" else cell_value

        worksheet.write(row, offset, cell_value, self.get_or_create_style(row_style))

    def get_or_create_style(self, attributes={}):
        """Работа со стилями для отчета."""
        default_format = {
            "num_format": "@",
            "align": "center",
            "valign": "vcenter",
            "border": 4,
            # "text_wrap": True,
            "font_size": 12
        }
        format_attibutes = {**default_format, **attributes}

        if "background" in format_attibutes:
            background_colors = {
                "@answer_odd": "#f2f4ff",
                "@answer_even": "#f7fff7",
                "@unit": "#fffde1",
                "@default_even": "#efefee",
            }
            if format_attibutes["background"] in background_colors:
                format_attibutes["bg_color"] = background_colors[
                    format_attibutes["background"]
                ]
            del format_attibutes["background"]

        format_cache_key = json.dumps(
            collections.OrderedDict(sorted(format_attibutes.items()))
        )
        if format_cache_key not in self.formats:
            self.formats[format_cache_key] = self.workbook.add_format(format_attibutes)
        return self.formats[format_cache_key]

    def size_cell(self, value):
        q_symbol = len(str(value))
        width_col = 7 if q_symbol < 6 else q_symbol * 1.2
        return width_col

    def generate_report_xls(self):
        assembly = Assembly.objects.get(id=self.assembly_id)
        file_path, full_path = self.get_report_path(
            assembly_name=assembly.name, extension=self.extension
        )
        print(file_path, full_path)
        self.workbook = xlsxwriter.Workbook(full_path, {"remove_timezone": True})
        self.worksheet_main = self.workbook.add_worksheet("Данные")

        fields = self.get_fields(assembly=assembly)
        skus = assembly.skus.all()
        skus = Product.objects.filter(id__in=skus).prefetch_related("days_data", "photo", "size", "property")
        start_col = 0
        start_row = 1
        size_column = {}
        advanced_title = [x.get("title") for x in REPORT_FIELDS_SKELETONS.get("advanced", [])]

        for idx_sku, sku in enumerate(skus):
            sizes = sku.size.all()
            for idx_field, field in enumerate(fields):
                if idx_sku == 0:
                    self.write_value(idx_sku, idx_field, field.get("title"), self.worksheet_main)
                    size = self.size_cell(field.get("title"))
                    size_column[field.get("title")] = size
                    self.worksheet_main.set_column(idx_field, idx_field, size_column[field.get("title")])
                    self.worksheet_main.set_row(idx_sku, 41)
                if not isinstance(field.get("value"), str):
                    if field.get("title") not in advanced_title:
                        value = field.get("value")(sku)
                        image = None
                        path = None
                        if field.get("title") == "Фото":
                            image = Image.open(settings.MEDIA_ROOT + "/" + str(value))
                            image = image.resize((40, 40), Image.ANTIALIAS)
                            path = settings.MEDIA_ROOT + "resize/" + str(value)
                            if not os.path.exists(os.path.dirname(path)):
                                os.makedirs(os.path.dirname(path))
                            image.save(path)
                        size = self.size_cell(value)
                        if size_column[field.get("title")] < size:
                            size_column[field.get("title")] = size
                        self.worksheet_main.set_column(idx_field, idx_field, size_column[field.get("title")])
                        if image and path:
                            self.worksheet_main.insert_image(f'B{idx_sku + start_row + 1}', path)
                            self.worksheet_main.set_row(idx_sku + start_row, 41)
                            self.worksheet_main.set_column(idx_field, idx_field, 6)
                        else:
                            self.write_value(idx_sku + start_row, idx_field, value, self.worksheet_main)
                    else:
                        for size in sizes:
                            value = field.get("value")(size)
                            self.write_value(idx_sku + start_row, idx_field, value, self.worksheet_main)
                            size = self.size_cell(value)
                            if size_column[field.get("title")] < size:
                                size_column[field.get("title")] = size
                            self.worksheet_main.set_column(idx_field, idx_field, size_column[field.get("title")])
                            start_row += 1
                        start_row -= len(sizes)
            start_row += len(sizes)
        self.workbook.close()
        return file_path
