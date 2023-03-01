from functools import wraps

from django.core.exceptions import PermissionDenied


def permission_required(perm, raise_exception=True):
    def check_perms(user):
        if isinstance(perm, str):
            perms = (perm,)
        else:
            perms = perm

        if user.has_perms(perms):
            return True
        if raise_exception:
            raise PermissionDenied
        return False

    def decorator(view_func):
        view_func.permissions = [perm]

        @wraps(view_func)
        def _wrapped_view(cls, request, *args, **kwargs):
            if not check_perms(request.user):
                raise PermissionDenied
            else:
                return view_func(cls, request, *args, **kwargs)

        return _wrapped_view

    return decorator
