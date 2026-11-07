from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """Require authenticated user with one of the given roles (or admin)."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if user.is_superuser or user.role == user.Role.ADMIN:
                return view_func(request, *args, **kwargs)
            if user.role in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        return _wrapped

    return decorator


waiter_required = role_required("waiter")
cook_required = role_required("cook")
admin_required = role_required("admin")
staff_required = role_required("waiter", "cook", "admin")
