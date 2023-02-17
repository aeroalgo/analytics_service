from django import forms
from django.forms import formset_factory

from app.product_search.models import ProductProperty, Product


class AddSku(forms.Form):
    prefix = 'sku'
    my_default_errors = {
        'required': "Это поле обязательно",
        'invalid': "Введите корректный/корректные sku"
    }
    sku = forms.CharField(
        label='', widget=forms.TextInput({
            "placeholder": "sku",
            "type": "text",
            "class": "form-control form-control-lg",
            "equired id": "add_sku"
        }),
        error_messages=my_default_errors, required=False
    )


class SelectDeleteSku(forms.Form):
    prefix = 'del_sku'
    skus = forms.JSONField(
        label='', widget=forms.SelectMultiple({
            "class": "js-example-basic-multiple w-100",
        }), required=False
    )


class SelectMP(forms.Form):
    prefix = 'mp'
    market = forms.IntegerField(
        label='', widget=forms.Select({
            "placeholder": "MP",
            "class": "form-control form-control-lg",
            "id": "exampleFormControlSelect1"
        }, choices=Product.MARKETS)
    )


class EditingPropertyProduct(forms.Form):
    prefix = 'editing'
    my_default_errors = {
        'required': "Это поле обязательно",
        'invalid': "Введите корректный/корректные sku"
    }
    sku = forms.CharField(
        label='', widget=forms.TextInput({
            "placeholder": "sku",
            "type": "text",
            "class": "form-control form-control-lg",
            "equired id": "editing_sku",
            'readonly': 'readonly'
        }, ),
        error_messages=my_default_errors
    )
    market = forms.CharField(
        label='', widget=forms.TextInput({
            "placeholder": "MP",
            "type": "text",
            "class": "form-control form-control-lg",
            "id": "exampleFormControlSelect1",
            'readonly': 'readonly'
        })
    )

    competition = forms.IntegerField(
        label='', widget=forms.Select({
            "placeholder": "Тип конкуренции",
            "class": "form-control form-control-lg",
            "id": "exampleFormControlSelect1"
        }, choices=ProductProperty.COMPETITIONS)
    )


class ReadonlyPropertyProduct(forms.Form):
    prefix = 'read_only'
    my_default_errors = {
        'required': "Это поле обязательно",
        'invalid': "Введите корректный/корректные sku"
    }
    sku = forms.CharField(
        label='', widget=forms.TextInput({
            "placeholder": "sku",
            "type": "text",
            "class": "form-control form-control-lg",
            "equired id": "editing_sku",
            'readonly': 'readonly'
        }, ),
        error_messages=my_default_errors
    )
    market = forms.CharField(
        label='', widget=forms.TextInput({
            "placeholder": "MP",
            "type": "text",
            "class": "form-control form-control-lg",
            "id": "exampleFormControlSelect1",
            'readonly': 'readonly'
        })
    )

    competition = forms.CharField(
        label='', widget=forms.TextInput({
            "placeholder": "Тип конкуренции",
            "class": "form-control form-control-lg",
            "id": "exampleFormControlSelect1",
            'readonly': 'readonly'
        })
    )


class CreateAssemblyForm(forms.Form):
    prefix = "assembly"
    name = forms.CharField(
        label='', widget=forms.TextInput({
            "placeholder": "Название сборки",
            "class": "form-control form-control-lg",
            "id": "exampleFormControlSelect1",
        })
    )


class EditingAssembly(forms.Form):
    prefix = 'edit_assembly'
    my_default_errors = {
        'required': "Это поле обязательно",
        'invalid': "Введите корректный/корректные sku"
    }
    sku = forms.CharField(
        label='', widget=forms.TextInput({
            "placeholder": "sku",
            "type": "text",
            "class": "form-control form-control-lg",
            "equired id": "editing_sku",
            'readonly': 'readonly'
        }, ),
        error_messages=my_default_errors
    )
    market = forms.CharField(
        label='', widget=forms.Select({
            "placeholder": "MP",
            "type": "text",
            "class": "form-control form-control-lg",
            "id": "exampleFormControlSelect1",
        }, choices=Product.MARKETS)
    )

    competition = forms.IntegerField(
        label='', widget=forms.Select({
            "placeholder": "Тип конкуренции",
            "class": "form-control form-control-lg",
            "id": "exampleFormControlSelect1"
        }, choices=ProductProperty.COMPETITIONS)
    )
