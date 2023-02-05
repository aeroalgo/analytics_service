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
    CreateAssemblyForm


class SearchProduct(TemplateView):
    template_name = "add_product.html"
    add_sku = AddSku()
    select_mp = SelectMP()
    redirect_url = '/product_search/view/{id}/'

    def get(self, request, id):
        try:
            exist_skus = Assembly.objects.get(id=id).skus.all()
            editing_form, read_only_form = self.get_formsets(editing=exist_skus)
            formset_context = {
                "add_sku_form": self.add_sku,
                "select_mp": self.select_mp,
                "read_only_form": editing_form or read_only_form,
            }

            return render(request, self.template_name, context=formset_context)
        except:
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
                x = GetSku(skus=skus, mp=form_market.cleaned_data['market'])
                x.publish()
            read_only_skus = []
            if request.POST.get('editing-0-sku') or request.POST.get('readonly-0-sku'):
                idx = 0
                while True:
                    form_editing = EditingPropertyProduct(request.POST, prefix="editing-{idx}".format(idx=idx))
                    read_only_form = ReadonlyPropertyProduct(request.POST, prefix="readonly-{idx}".format(
                        idx=idx))
                    if form_editing.is_valid():
                        ProductProperty.objects.filter(
                            sku__sku=form_editing.cleaned_data['sku']).update(
                            competition=form_editing.cleaned_data['competition'])
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
            if 'add_sku_in_assembly' in request.POST:
                for sku in read_only_skus:
                    Assembly.objects.get(id=id).skus.add(sku)
                return HttpResponseRedirect(self.redirect_url.format(id=id))
            formset_context = {
                "add_sku_form": self.add_sku,
                "select_mp": self.select_mp,
            }
            editing_form, read_only_form = self.get_formsets(editing=new_skus, read_only=read_only_skus)
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

    def get_formsets(self, editing: List, read_only: List = []):
        """Формирование наборов форм для частичного редактирования и read_only форм после окончания редактирования"""
        editing_form = []
        read_only = read_only.copy()
        for idx, sku in enumerate(editing):
            if None not in [mp.competition for mp in sku.property.all()]:
                read_only.append(sku)
                continue
            editing_form.append(EditingPropertyProduct(prefix=f"editing-{idx}", initial={
                'sku': sku.sku,
                "market": "".join([dict(ProductProperty.MARKETS).get(mp.mp) for mp in sku.property.all()])
            }))
        read_only_form = []
        duplicate_sku = []

        for idx, sku in enumerate(read_only):
            if sku.sku not in duplicate_sku:
                duplicate_sku.append(sku.sku)
                read_only_form.append(ReadonlyPropertyProduct(prefix=f"readonly-{idx}", initial={
                    'sku': sku.sku,
                    "market": "".join([
                        dict(ProductProperty.MARKETS).get(mp.mp) for mp in sku.property.all()
                    ]),
                    "competition": "".join([
                        dict(ProductProperty.COMPETITIONS).get(mp.competition) for mp in sku.property.all()
                    ])
                }))
        return editing_form, read_only_form

    def add_new_sku(self, new_skus, form_market):
        """Функция добавляет новые sku которых нет в базе"""
        add_new_sku = []
        add_new_prop_sku = []
        if new_skus:
            for sku in new_skus:
                if sku != '':
                    instance_sku = Product()
                    instance_sku.sku = sku
                    add_new_sku.append(instance_sku)
                    instance_product_prop = ProductProperty()
                    instance_product_prop.sku = instance_sku
                    instance_product_prop.mp = form_market.cleaned_data['market']
                    add_new_prop_sku.append(instance_product_prop)
            Product.objects.bulk_create(add_new_sku)
            ProductProperty.objects.bulk_create(add_new_prop_sku)
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
        for sku in skus:
            skus_id.append(sku.id)
        items_data = Last30DaysData.objects.filter(sku_id__in=skus_id).select_related("sku")
        for item in items_data:
            property = item.sku.property.first()
            pruduct_30_days.append({
                "mp": dict(ProductProperty.MARKETS).get(property.mp),
                "competition": dict(ProductProperty.COMPETITIONS).get(property.competition),
                "article": item.sku.sku,
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
        period_items_data = PeriodData.objects.filter(sku_id__in=skus_id).select_related("sku").order_by("sku",
                                                                                                         "date_start")
        visited_q1 = []
        visited_q2 = []
        visited_q3 = []
        visited_q4 = []

        q1 = []
        q2 = []
        q3 = []
        q4 = []

        visited = []
        for item in period_items_data:
            if item.sku.sku not in visited and visited:
                if q1:
                    quarter.get(1).append(q1.copy())
                if q2:
                    quarter.get(2).append(q2.copy())
                if q3:
                    quarter.get(3).append(q3.copy())
                if q4:
                    quarter.get(4).append(q4.copy())
                q1.clear()
                q2.clear()
                q3.clear()
                q4.clear()
                visited.clear()
            visited.append(item.sku.sku)
            property = item.sku.property.first()
            item_data = {
                "revenue": round(item.revenue, 1),
                # "lost_profit": item.lost_profit,
                "lost_profit": item.lost_profit,
                "sales": item.sales,
                "final_price_average": round(item.final_price_average, 1),
                # Валовая прибыль нет в описании
                # Средняя позиция в выдаче не понятно как считать

            }
            start_items_data = {
                "mp": dict(ProductProperty.MARKETS).get(property.mp),
                "competition": dict(ProductProperty.COMPETITIONS).get(property.competition),
                "article": item.sku.sku,
                **item_data
            }

            if item.date_start.month <= 3:
                if item.sku.sku not in visited_q1:
                    visited_q1.append(item.sku.sku)
                    q1.append(start_items_data)
                else:
                    q1.append(item_data)
            elif 3 < item.date_start.month <= 6:
                if item.sku.sku not in visited_q2:
                    visited_q2.append(item.sku.sku)
                    q2.append(start_items_data)
                else:
                    q2.append(item_data)
            elif 6 < item.date_start.month <= 9:
                if item.sku.sku not in visited_q3:
                    visited_q3.append(item.sku.sku)
                    q3.append(start_items_data)
                else:
                    q3.append(item_data)
            elif 9 < item.date_start.month <= 12:
                if item.sku.sku not in visited_q4:
                    visited_q4.append(item.sku.sku)
                    q4.append(start_items_data)
                else:
                    q4.append(item_data)
        if len(set(visited)) == 1:
            quarter.get(1).append(q1)
            quarter.get(2).append(q2)
            quarter.get(3).append(q3)
            quarter.get(4).append(q4)
        print(quarter)
        return render(request, self.template_name, context={
            "table_30days": pruduct_30_days, "quarter_data": quarter
        })
