from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from authentication.models import Role


def role_required(*roles):
    """限制仅指定角色可访问。"""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('authentication:login')
            if request.user.role not in roles:
                messages.error(request, '您没有权限访问该页面。')
                return redirect('authentication:dashboard')
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def admin_required(view_func):
    return role_required(Role.ADMIN)(view_func)


def headman_required(view_func):
    return role_required(Role.HEADMAN)(view_func)


def member_required(view_func):
    return role_required(Role.MEMBER)(view_func)
