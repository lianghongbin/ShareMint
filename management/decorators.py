from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from authentication.models import Role

LOCKED_HEADMAN_MSG = '您的账号已被锁定，仅可查看数据，无法进行业务操作。'


def reject_locked_headman(request, redirect_to='management:headman_dashboard'):
    user = request.user
    if user.is_authenticated and user.is_headman and user.is_locked:
        messages.error(request, LOCKED_HEADMAN_MSG)
        return redirect(redirect_to)
    return None


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
