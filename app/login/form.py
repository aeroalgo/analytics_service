from django import forms
from allauth.account.forms import LoginForm
from django import forms
from django.contrib.auth.forms import AuthenticationForm


class CustomAuthenticationForm(AuthenticationForm):
    """Кастомная форма авторизации """
    username = forms.CharField(max_length=254,
                               widget=forms.TextInput({
                                   "placeholder": "Адрес электронной почты / Логин",
                                   "type": "email",
                                   "class": "form-control form-control-lg",
                                   "name": "username",
                                   "equired id": "id_username"
                               }))
    password = forms.CharField(label="Password",
                               widget=forms.PasswordInput({
                                   "placeholder": "Пароль",
                                   "class": "form-control form-control-lg",
                                   "required id": "id_password",
                                   "name": "password",
                                   "type": "password",
                               }))

    error_messages = {
        "invalid_login": "Введите корректный Логин или Пароль",
        "inactive": "Этот аккаунт не активный",
    }
