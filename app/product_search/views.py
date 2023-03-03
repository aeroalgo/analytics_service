import datetime
from statistics import mean
from typing import List
from django import forms
from django.shortcuts import render
from django.http import HttpResponse, HttpRequest
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
import requests as r
from app.analytics.settings import env
from app.product_search.charts import LineChartData
from app.product_search.tasks.generate_reports import GenerateReport
from app.product_search.tasks.load_pruduct import GetSku
from app.product_search.models import Product, ProductProperty, Assembly, Last30DaysData, PeriodData, ProductPhoto
from app.product_search.form import AddSku, SelectMP, EditingPropertyProduct, ReadonlyPropertyProduct, \
    CreateAssemblyForm, SelectDeleteSku, EditingAssembly


class ProductUtils:
    default_structure = {
        "last_update": " ",
        "mp": " ",
        "competition": " ",
        "img": " ",
        "article": " ",
        "name": " ",
        "last_price": " ",
        "most_sales": " ",
        # "lost_profit": item.lost_profit,
        "revenue": " ",
        "final_price_average": " ",
        "ssp": " ",
        "price_ssp": " ",
        # Валовая прибыль нет в описании
        # "val_price": " ",
        "categories_pos": " ",
        "first_date": " ",
        "start_price": " ",
        "sales": " ",
        "rating": " ",
        "comments": " ",
    }

    def add_new_sku(self, new_skus: List, form_market: forms) -> bool:
        """
        Функция добавляет новые sku которых нет в базе
        :param new_skus: sku
        :param form_market: форма
        :return: Возвращает булевое значение если была произведена вставка
        """
        add_new_sku = []
        if new_skus:
            for sku in new_skus:
                if sku != '':
                    instance_sku = Product()
                    instance_sku.sku = sku
                    instance_sku.mp = form_market.cleaned_data['market']
                    add_new_sku.append(instance_sku)
            Product.objects.bulk_create(add_new_sku)
            return True

    def line_break_symbol(self, max_chars: int, text: str) -> str:
        """
        Разделяет текст на несколько строк (триггер max_chars)
        :param max_chars: Максимальное количество символов в строке
        :param text: Строка с вариантом ответа
        :return: Возвращает отформатированную строку варианта ответа
        """

        words_answers = text.replace("/", "").strip().split(' ')
        new_answer = ''
        chars_words = 0
        for idx, word in enumerate(words_answers):
            chars_words += len(word)
            new_answer += word + " "
            if chars_words >= max_chars:
                new_answer += "<br>"
                chars_words = 0
        return new_answer

    def get_table_data(self, id, skus_id: List, clothes: bool = False):
        pruduct_30_days = []
        prefetch_table = ["photo", "property", "days_data"]
        if clothes:
            prefetch_table.append("size")
        items_data = Product.objects.filter(id__in=skus_id).prefetch_related(*prefetch_table)
        for item in items_data:
            try:
                default = self.default_structure.copy()
                default["last_update"] = item.days_data.first().date_update
                default["mp"] = dict(Product.MARKETS).get(item.mp)
                default["competition"] = dict(ProductProperty.COMPETITIONS).get(
                    item.property.filter(assembly_id=id, sku_id=item.id).first().competition).replace(" ", "<br>")
                default["img"] = item.photo.first().photo if item.photo else None
                default["article"] = item.sku
                default["name"] = self.line_break_symbol(10, item.days_data.first().name)
                default["last_price"] = item.days_data.first().last_price
                default["most_sales"] = round(item.days_data.first().most_sales, 1)
                default["ssp"] = round(item.days_data.first().client_sale, 1)
                default["price_ssp"] = round(item.days_data.first().client_price, 1)
                default["categories_pos"] = round(item.days_data.first().categories_pos, 1)
                default["start_price"] = item.days_data.first().start_price
                # "lost_profit": item.lost_profit,
                default["revenue"] = round(item.days_data.first().revenue, 1)
                default["final_price_average"] = round(item.days_data.first().final_price_average, 1)
                # Валовая прибыль нет в описании
                # Средняя позиция в выдаче не понятно как считать
                default["first_date"] = item.days_data.first().first_date
                default["sales"] = item.days_data.first().sales
                default["rating"] = item.days_data.first().rating
                default["comments"] = item.days_data.first().comments
                sizes = item.size.all()
                if clothes:
                    if sizes:
                        for idx, size in enumerate(sizes):
                            if idx == 0:
                                default["size_title"] = size.title.replace(" ", "<br>")
                                default["size_sales"] = sum([x for x in size.sales if x != "NaN"])
                                default["size_balance"] = round(mean([x for x in size.balance if x != "NaN"]), 2)
                            else:
                                default = self.default_structure.copy()
                                default["article"] = item.sku
                                default["size_title"] = size.title.replace(" ", "<br>")
                                default["size_sales"] = sum([x for x in size.sales if x != "NaN"])
                                default["size_balance"] = round(mean([x for x in size.balance if x != "NaN"]), 2)
                            pruduct_30_days.append(default.copy())
                    else:
                        default["size_title"] = None
                        default["size_sales"] = None
                        default["size_balance"] = None
                        pruduct_30_days.append(default.copy())
                else:
                    pruduct_30_days.append(default.copy())
            except Exception as e:
                print(e)
                continue
        return pruduct_30_days


class SearchProduct(TemplateView, ProductUtils):
    template_name = "add_product.html"
    add_sku = AddSku()
    select_mp = SelectMP()
    redirect_url = '/product_search/view/{id}/'

    def get(self, request: HttpRequest, id: int) -> HttpResponse:
        try:
            exist_skus = Assembly.objects.get(id=id).skus.all()
            editing_form, read_only_form = self.get_formsets(id_assembly=id, editing=exist_skus)
            formset_context = {
                "add_sku_form": self.add_sku,
                "select_mp": self.select_mp,
                "read_only_form": editing_form or read_only_form,
            }

            return render(request, self.template_name, context=formset_context)
        except Exception as e:
            print(e)
            return render(request, self.template_name, context={
                "add_sku_form": self.add_sku,
                "select_mp": self.select_mp
            })

    def post(self, request: HttpRequest, id: int) -> HttpResponse:
        form_sku = AddSku(request.POST, prefix='sku')
        form_market = SelectMP(request.POST, prefix='mp')
        if form_sku.is_valid() and form_market.is_valid():
            skus = form_sku.cleaned_data['sku'].split(", ")
            exist_products = Product.objects.filter(sku__in=skus).values_list('sku', flat=True)
            new_skus = [sku for sku in skus if sku not in exist_products and sku != '']
            if self.add_new_sku(new_skus=new_skus, form_market=form_market):
                x = GetSku(skus=new_skus, mp=form_market.cleaned_data['market'])
                x.publish()
            read_only_skus = []

            if request.POST.get('editing-0-sku') or request.POST.get('readonly-0-sku'):
                idx = 0
                assembly = Assembly.objects.get(id=id)
                while True:
                    form_editing = EditingPropertyProduct(request.POST, prefix="editing-{idx}".format(idx=idx))
                    read_only_form = ReadonlyPropertyProduct(request.POST, prefix="readonly-{idx}".format(
                        idx=idx))
                    if form_editing.is_valid():
                        product = Product.objects.get(sku=form_editing.cleaned_data['sku'])
                        obj, _ = ProductProperty.objects.get_or_create(
                            sku=product,
                            competition=form_editing.cleaned_data['competition'], assembly=assembly)
                        read_only_skus.append(form_editing.cleaned_data['sku'])
                    if read_only_form.is_valid():
                        read_only_skus.append(read_only_form.cleaned_data['sku'])
                    if not form_editing.is_valid() and not read_only_form.is_valid():
                        break
                    idx += 1
            new_skus = list(Product.objects.filter(sku__in=skus).prefetch_related("property").order_by(
                '-id'))
            read_only_skus = list(Product.objects.filter(sku__in=read_only_skus).prefetch_related("property").order_by(
                '-id'))
            # Связываем сборку с товарами
            for sku in read_only_skus:
                Assembly.objects.get(id=id).skus.add(sku)
            if 'add_sku_in_assembly' in request.POST:
                return HttpResponseRedirect(self.redirect_url.format(id=id))
            formset_context = {
                "add_sku_form": self.add_sku,
                "select_mp": self.select_mp,
            }
            editing_form, read_only_form = self.get_formsets(id_assembly=id, editing=new_skus,
                                                             read_only=read_only_skus)
            formset_context.update({
                "editing_form": editing_form,
                "read_only_form": read_only_form
            })
            return render(request, self.template_name, context=formset_context)

        else:
            return render(request, self.template_name, context={
                "add_sku_form": form_sku,
                "select_mp": form_market
            })

    def get_formsets(self, id_assembly: int, editing: List, read_only: List = []):
        """
        Формирование наборов форм для частичного редактирования
        и read_only форм после окончания редактирования
        """
        editing_form = []
        read_only = read_only.copy()
        for idx, sku in enumerate(editing):
            if [property.competition for property in sku.property.filter(assembly=id_assembly)]:
                read_only.append(sku)
                continue
            editing_form.append(EditingPropertyProduct(prefix=f"editing-{idx}", initial={
                'sku': sku.sku,
                "market": dict(Product.MARKETS).get(sku.mp)
            }))
        read_only_form = []
        duplicate_sku = []

        for idx, sku in enumerate(read_only):
            if sku.sku not in duplicate_sku:
                duplicate_sku.append(sku.sku)
                read_only_form.append(ReadonlyPropertyProduct(prefix=f"readonly-{idx}", initial={
                    'sku': sku.sku,
                    "market": dict(Product.MARKETS).get(sku.mp),
                    "competition": "".join(
                        [dict(ProductProperty.COMPETITIONS).get(mp.competition)
                         for mp in sku.property.filter(assembly=id_assembly)]
                    )
                }))
        return editing_form, read_only_form


class CreateAssembly(TemplateView):
    template_name = "create_assembly.html"
    redirect_url = '/product_search/create/{id}/'
    assembly = CreateAssemblyForm()
    def get(self, request: HttpRequest):
        url = 'http://mpstats.io/api/user/report_api_limit'
        x = r.get(url=url, headers=GetSku.HEADERS)
        api_limit = x.json()
        return render(request, self.template_name, context={
            "create_assembly": self.assembly, "api_limit": api_limit
        })

    def post(self, request: HttpRequest) -> HttpResponse:
        assembly_data = CreateAssemblyForm(request.POST, prefix="assembly")
        if assembly_data.is_valid():
            # Добавить вариант перехода на уже существующую сборку при вводе существующего имени
            try:
                exist_assembly = Assembly.objects.get(name=assembly_data.cleaned_data['name'])
                return HttpResponseRedirect(self.redirect_url.format(id=exist_assembly.id))
            except:
                id_assembly = self.add_new_assembly(assembly_data=assembly_data)
                return HttpResponseRedirect(self.redirect_url.format(id=id_assembly))
        return render(request, self.template_name, context={
            "create_assembly": self.assembly,
        })

    def add_new_assembly(self, assembly_data):
        if assembly_data.cleaned_data['name'] not in (None, ""):
            instance_assembly = Assembly()
            instance_assembly.name = assembly_data.cleaned_data['name']
            instance_assembly.type = assembly_data.cleaned_data['type']
            instance_assembly.save()
            return instance_assembly.id


class ViewTableSkus(TemplateView, ProductUtils):
    template_name = "view_table_skus.html"

    def get(self, request: HttpRequest, id: int) -> HttpResponse:
        url = 'http://mpstats.io/api/user/report_api_limit'
        x = r.get(url=url, headers=GetSku.HEADERS)
        api_limit = x.json()
        quarter = {
            1: [],
            2: [],
            3: [],
            4: []
        }
        clothes = False
        exist_assembly = Assembly.objects.get(id=id)
        if exist_assembly.type == Assembly.TYPE_CLOTHES:
            clothes = True
        skus = exist_assembly.skus.all()
        skus_ids = []
        add_default_start = {
            1: 0, 2: 1, 3: 2, 4: 0, 5: 1, 6: 2, 7: 0, 8: 1, 9: 2, 10: 0, 11: 1, 12: 2,
        }
        add_default_end = {
            1: 2, 2: 1, 3: 0, 4: 2, 5: 1, 6: 0, 7: 2, 8: 1, 9: 0, 10: 2, 11: 1, 12: 0,
        }
        for idx_sku, sku in enumerate(skus):
            sku_id = sku.id
            period_items_data = PeriodData.objects.filter(sku_id=sku_id).select_related("sku").order_by("date_start")
            property = sku.property.filter(assembly=id)

            insert_idx = idx_sku
            for idx_item, item in enumerate(period_items_data):
                try:
                    item_data_default = {
                        "revenue": None,
                        "lost_profit": None,
                        "sales": None,
                        "final_price_average": None,
                        # Валовая прибыль нет в описании
                        # Средняя позиция в выдаче не понятно как считать

                    }
                    if idx_item != 0 and item.date_start.month == 1:
                        insert_idx += 1
                    data = []
                    start_items_data = {
                        "year": str(item.date_start.year),
                        "mp": dict(Product.MARKETS).get(item.sku.mp),
                        "competition": dict(ProductProperty.COMPETITIONS).get(property[0].competition),
                        "article": item.sku.sku,

                    }
                    item_data = {
                        "revenue": round(item.revenue, 1),
                        "lost_profit": item.lost_profit,
                        "sales": item.sales,
                        "final_price_average": round(item.final_price_average, 1),
                        # Валовая прибыль нет в описании
                        # Средняя позиция в выдаче не понятно как считать

                    }
                    if idx_item == 0 or item.date_start.month in (1, 4, 7, 10):
                        data.append(start_items_data.copy())
                        if idx_item == 0:
                            for i in range(add_default_start.get(item.date_start.month)):
                                data.append(item_data_default.copy())
                        data.append(item_data.copy())
                    if idx_item == len(period_items_data) - 1:
                        for i in range(add_default_end.get(item.date_start.month)):
                            data.append(item_data_default.copy())
                    if data:
                        quarter.get(PeriodData.MONTH_QUARTER.get(item.date_start.month)).append(data.copy())
                    else:
                        len_data = len(quarter.get(PeriodData.MONTH_QUARTER.get(item.date_start.month)))
                        if len_data - 1 > insert_idx or len_data - 1 < insert_idx:
                            insert_idx = len(quarter.get(PeriodData.MONTH_QUARTER.get(item.date_start.month))) - 1
                        quarter.get(PeriodData.MONTH_QUARTER.get(item.date_start.month))[insert_idx].append(
                            item_data.copy())
                        insert_idx = idx_sku
                except Exception as e:
                    print(e)
                    continue

            skus_ids.append(sku_id)

        pruduct_30_days = self.get_table_data(id=id, skus_id=skus_ids, clothes=clothes)
        return render(request, self.template_name, context={
            "table_30days": pruduct_30_days, "quarter_data": quarter, "clothes": clothes,
            "api_limit": api_limit
        })


class UpdateTable(TemplateView):
    redirect_url = '/product_search/view/{id}/'
    template_name = "view_table_skus.html"

    def get(self, request: HttpRequest, id: int) -> HttpResponse:
        exist_assembly = Assembly.objects.filter(id=id).prefetch_related("skus")
        skus = exist_assembly[0].skus.all()
        skus_mp = {
            Product.MP_WB: [],
            Product.MP_OZON: [],
        }
        for sku in skus:
            skus_mp.get(sku.mp).append(sku.sku)

        for mp, skus in skus_mp.items():
            x = GetSku(skus=skus, mp=mp)
            x.publish()
        return HttpResponseRedirect(self.redirect_url.format(id=id))


class EditTable(TemplateView, ProductUtils):
    redirect_url = '/product_search/view/{id}/'
    template_name = "edit_table.html"
    add_sku = AddSku()
    select_mp = SelectMP()

    def get_delete_form(self, id):
        exist_skus = Assembly.objects.get(id=id).skus.all()
        del_sku_form = SelectDeleteSku()
        del_sku_form.fields['skus'].widget.choices = [(sku.id, sku.sku) for sku in exist_skus]
        return del_sku_form, exist_skus

    def get(self, request: HttpRequest, id: int) -> HttpResponse:
        try:
            del_sku_form, exist_skus = self.get_delete_form(id)
            editing_form = self.get_formsets(id_assembly=id, editing=exist_skus)
            formset_context = {
                "add_sku_form": self.add_sku,
                "select_mp": self.select_mp,
                "editing_form": editing_form,
                "del_sku": del_sku_form
            }

            return render(request, self.template_name, context=formset_context)
        except Exception as e:
            print(e)
            return render(request, self.template_name, context={
                "add_sku_form": self.add_sku,
                "select_mp": self.select_mp
            })

    def post(self, request: HttpRequest, id: int) -> HttpResponse:
        form_sku = AddSku(request.POST, prefix='sku')
        form_market = SelectMP(request.POST, prefix='mp')
        if form_sku.is_valid() and form_market.is_valid():
            skus = form_sku.cleaned_data['sku'].split(", ")
            exist_products = Product.objects.filter(sku__in=skus).values_list('sku', flat=True)
            new_skus = [sku for sku in skus if sku not in exist_products and sku != '']
            if self.add_new_sku(new_skus=new_skus, form_market=form_market):
                x = GetSku(skus=new_skus, mp=form_market.cleaned_data['market'])
                x.publish()
            read_only_skus = []
            if request.POST.get('edit_assembly-0-sku'):
                idx = 0
                assembly = Assembly.objects.get(id=id)
                while True:
                    form_editing = EditingAssembly(request.POST, prefix="edit_assembly-{idx}".format(idx=idx))
                    if form_editing.is_valid():
                        product = Product.objects.get(sku=form_editing.cleaned_data['sku'])
                        product.mp = form_editing.cleaned_data['market']
                        product.save()
                        product_prop = ProductProperty.objects.filter(
                            sku=product, assembly=assembly).first()
                        if product_prop:
                            product_prop.competition = form_editing.cleaned_data['competition']
                            product_prop.save()
                        else:
                            ProductProperty.objects.create(
                                sku=product, competition=form_editing.cleaned_data['competition'], assembly=assembly
                            )
                        read_only_skus.append(form_editing.cleaned_data['sku'])
                    if not form_editing.is_valid():
                        break
                    idx += 1

            new_skus = list(Product.objects.filter(sku__in=skus).prefetch_related("property").order_by(
                '-id'))
            old_skus = list(Product.objects.filter(sku__in=read_only_skus).prefetch_related("property").order_by(
                '-id'))
            new_skus.extend(old_skus)

            # Связываем сборку с товарами
            for sku in new_skus:
                Assembly.objects.get(id=id).skus.add(sku)

            formset_context = {
                "add_sku_form": self.add_sku,
                "select_mp": self.select_mp,
            }
            del_sku_form, exist_skus = self.get_delete_form(id)
            editing_form = self.get_formsets(id_assembly=id, editing=new_skus)
            formset_context.update({
                "editing_form": editing_form,
                "del_sku": del_sku_form
            })
            if 'edit_table' in request.POST:
                del_sku_form = SelectDeleteSku(request.POST, prefix='del_sku')
                if del_sku_form.is_valid():
                    try:
                        ProductProperty.objects.filter(assembly=id, sku__in=del_sku_form.cleaned_data["skus"]).delete()
                        assembly = Assembly.objects.get(id=id)
                        product_skus = Product.objects.filter(id__in=del_sku_form.cleaned_data["skus"])
                        for sku in product_skus:
                            assembly.skus.remove(sku)
                    except:
                        pass
                    return HttpResponseRedirect(self.redirect_url.format(id=id))
            return render(request, self.template_name, context=formset_context)

    def get_formsets(self, id_assembly: int, editing: List):
        """Формирование наборов форм для частичного редактирования и read_only форм после окончания редактирования"""
        editing_forms = []
        for idx, sku in enumerate(editing):
            competition = sku.property.filter(assembly=id_assembly).first()
            editing_form = EditingAssembly(prefix=f"edit_assembly-{idx}", initial={
                "sku": sku.sku,
                "market": sku.mp,
                "competition": competition.competition if competition else ProductProperty.COMPETITION_ANALYZE
            })
            editing_forms.append(editing_form)
        return editing_forms


class Charts(TemplateView):
    redirect_url = '/product_search/view/{id}/'
    template_name = "charts.html"

    def get(self, request: HttpRequest, id: int) -> HttpResponse:
        price_chart_data = []
        sales_chart_data = []
        balance_chart_data = []
        skus = Assembly.objects.get(id=id).skus.all()
        last_datas = Last30DaysData.objects.filter(sku__in=skus).select_related("sku")
        all_date = self.get_all_date(last_date=last_datas[0].date_update)
        for idx, data in enumerate(last_datas):
            price_data = LineChartData(label=data.sku.sku, data=data.price_graph)
            sales_data = LineChartData(label=data.sku.sku, data=data.graph)
            balance_data = LineChartData(label=data.sku.sku, data=data.balance)
            price_data.set_color(idx)
            sales_data.set_color(idx)
            balance_data.set_color(idx)
            price_chart_data.append(price_data.dict())
            sales_chart_data.append(sales_data.dict())
            balance_chart_data.append(balance_data.dict())
        return render(request, self.template_name, context={
            "labels": all_date,
            "price_data": price_chart_data,
            "sales_data": sales_chart_data,
            "balance_data": balance_chart_data,
        })

    def get_all_date(self, last_date):
        dates = []
        d1 = last_date - datetime.timedelta(days=30)  # начальная дата
        d2 = last_date  # конечная дата
        delta = d2 - d1  # timedelta
        if delta.days <= 0:
            print("Ругаемся и выходим")
        for i in range(delta.days + 1):
            dates.append(str(d1 + datetime.timedelta(days=i)))
        return dates


class DownloadReport(TemplateView):
    redirect_url = '/media/'

    def get(self, request: HttpRequest, id: int) -> HttpResponse:
        x = GenerateReport(assembly_id=id)
        return HttpResponseRedirect(self.redirect_url+x.process())
