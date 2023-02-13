from typing import List
from dateutil.rrule import rrule, MONTHLY
import datetime
from django.shortcuts import render
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
from app.product_search.tasks.load_pruduct import GetSku
from app.product_search.test_async_task import GeneratePollReport
from app.product_search.models import Product, ProductProperty, Assembly, Last30DaysData, PeriodData
from app.product_search.form import AddSku, SelectMP, EditingPropertyProduct, ReadonlyPropertyProduct, \
    CreateAssemblyForm, SelectDeleteSku, EditingAssembly


class SearchProduct(TemplateView):
    template_name = "add_product.html"
    add_sku = AddSku()
    select_mp = SelectMP()
    redirect_url = '/product_search/view/{id}/'

    def get(self, request, id):
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

    def post(self, request, id):
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
                        x, c = ProductProperty.objects.get_or_create(
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
            # Связываем сборку с товарами при нажатии на кнопку сохранить
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

    def get_formsets(self, id_assembly: int, editing: List, read_only: List = [], ):
        """Формирование наборов форм для частичного редактирования и read_only форм после окончания редактирования"""
        editing_form = []
        read_only = read_only.copy()
        for idx, sku in enumerate(editing):
            print(sku)
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

    def add_new_sku(self, new_skus, form_market):
        """Функция добавляет новые sku которых нет в базе"""
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


class CreateAssembly(TemplateView):
    template_name = "create_assembly.html"
    redirect_url = '/product_search/create/{id}/'
    assembly = CreateAssemblyForm()

    def get(self, request):
        return render(request, self.template_name, context={
            "create_assembly": self.assembly,
        })

    def post(self, request):
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
            instance_assembly.save()
            return instance_assembly.id


class ViewTableSkus(TemplateView):
    template_name = "view_table_skus.html"

    def get(self, request, id):
        quarter = {
            1: [],
            2: [],
            3: [],
            4: []
        }
        pruduct_30_days = []
        exist_assembly = Assembly.objects.get(id=id)
        skus = exist_assembly.skus.all()
        skus_id = []
        add_default_start = {
            1: 0,
            2: 1,
            3: 2,
            4: 0,
            5: 1,
            6: 2,
            7: 0,
            8: 1,
            9: 2,
            10: 0,
            11: 1,
            12: 2,
        }
        add_default_end = {
            1: 2,
            2: 1,
            3: 0,
            4: 2,
            5: 1,
            6: 0,
            7: 2,
            8: 1,
            9: 0,
            10: 2,
            11: 1,
            12: 0,
        }
        for idx_sku, sku in enumerate(skus):
            sku_id = sku.id
            period_items_data = PeriodData.objects.filter(sku_id=sku_id).select_related("sku").order_by("date_start")
            property = sku.property.filter(assembly=id)

            insert_idx = 0 + idx_sku
            for idx_item, item in enumerate(period_items_data):
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
                    quarter.get(PeriodData.MONTH_QUARTER.get(item.date_start.month))[insert_idx].append(
                        item_data.copy())

            skus_id.append(sku_id)

        items_data = Last30DaysData.objects.filter(sku_id__in=skus_id).select_related("sku")
        for item in items_data:
            property = item.sku.property.filter(assembly=id)
            pruduct_30_days.append({
                "last_update": item.date_update,
                "mp": dict(Product.MARKETS).get(item.sku.mp),
                "competition": dict(ProductProperty.COMPETITIONS).get(property[0].competition),
                "article": item.sku.sku,
                "name": item.name.replace("/", "<br>"),
                "last_price": item.last_price,
                "most_sales": round(item.most_sales, 1),
                # "lost_profit": item.lost_profit,
                "revenue": round(item.revenue, 1),
                "final_price_average": round(item.final_price_average, 1),
                # Валовая прибыль нет в описании
                "val_price": None,
                # Средняя позиция в выдаче не понятно как считать
                "categories_pos": None,
                "first_date": item.first_date,
                "start_price": None,
                "sales": item.sales,
                "rating": item.rating,
                "comments": item.comments,
            })
        return render(request, self.template_name, context={
            "table_30days": pruduct_30_days, "quarter_data": quarter
        })


class UpdateTable(TemplateView):
    redirect_url = '/product_search/view/{id}/'
    template_name = "view_table_skus.html"

    def get(self, request, id):
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


class EditTable(TemplateView):
    redirect_url = '/product_search/view/{id}/edit'
    template_name = "edit_table.html"
    add_sku = AddSku()
    select_mp = SelectMP()

    def get(self, request, id):
        try:
            del_sku_form = SelectDeleteSku()
            exist_skus = Assembly.objects.get(id=id).skus.all()
            del_sku_form.fields['skus'].widget.choices = [(sku.id, sku.sku) for sku in exist_skus]
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

    def post(self, request, id):
        print(request.POST)

    def get_formsets(self, id_assembly: int, editing: List):
        """Формирование наборов форм для частичного редактирования и read_only форм после окончания редактирования"""
        editing_forms = []
        for idx, sku in enumerate(editing):
            competition = sku.property.filter(assembly=id_assembly).first()
            editing_form = EditingAssembly(prefix=f"editing-{idx}", initial={
                "sku": sku.sku,
                "market": sku.mp,
                "competition": competition.competition
            })
            editing_forms.append(editing_form)
        return editing_forms
