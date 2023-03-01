from re import compile
from builtins import any, hasattr
from django.contrib import messages
from app.analytics import settings
from django.http import HttpResponseRedirect
from allauth.account.adapter import get_adapter


EXEMPT_URLS = [compile('/' + settings.LOGIN_URL.lstrip('/'))]
if hasattr(settings, 'LOGIN_EXEMPT_URLS'):
    EXEMPT_URLS += [compile(expr) for expr in settings.LOGIN_EXEMPT_URLS]


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        view_allowed = True
        if not request.user.is_authenticated:
            path = '/' + request.path_info.lstrip('/')
            if not any(m.match(path) for m in EXEMPT_URLS):
                view_allowed = False

        # проверяем у пользователя наличие прав на вход
        if request.user.is_authenticated and not request.user.has_perms(['permissions.login']):
            adapter = get_adapter(request)
            adapter.logout(request)
            storage = messages.get_messages(request)
            del storage._loaded_messages[0]
            messages.warning(request, 'У вас нет прав на вход в систему')
            response = HttpResponseRedirect(settings.LOGIN_URL)
        elif view_allowed:
            response = self.get_response(request)
        else:
            response = HttpResponseRedirect(settings.LOGIN_URL)
            # response = HttpResponse('not allowed')
        return response
