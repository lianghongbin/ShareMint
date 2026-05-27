from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

from authentication.models import Role
from management.decorators import LOCKED_HEADMAN_MSG


class AuditMiddleware:
    """记录所有写操作与 API 变更到审计日志。"""

    MUTATING_METHODS = frozenset({'POST', 'PUT', 'PATCH', 'DELETE'})
    SKIP_PREFIXES = ('/static/', '/admin/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.method not in self.MUTATING_METHODS:
            return response
        if any(request.path.startswith(prefix) for prefix in self.SKIP_PREFIXES):
            return response

        view_name = ''
        if request.resolver_match:
            view_name = request.resolver_match.view_name or ''
        if view_name in (
            'management:admin_settings_audit',
            'management:admin_settings_audit_detail',
        ):
            return response

        from management.services.audit import EXPLICIT_AUDIT_VIEWS, record_audit

        try:
            if view_name in EXPLICIT_AUDIT_VIEWS:
                return response
            if not getattr(request, '_audit_logged', False) and response.status_code < 400:
                record_audit(request, action=view_name, status_code=response.status_code)
        except Exception:
            pass
        return response


class HeadmanLockMiddleware:
    """锁定团长禁止 POST/PUT/PATCH/DELETE 写操作。"""

    SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')
    ALLOWED_URL_NAMES = (
        'authentication:logout',
        'authentication:login',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if (
            user.is_authenticated
            and user.role == Role.HEADMAN
            and user.is_locked
            and request.method not in self.SAFE_METHODS
        ):
            resolver_match = request.resolver_match
            if not resolver_match or resolver_match.view_name not in self.ALLOWED_URL_NAMES:
                msg = LOCKED_HEADMAN_MSG
                if request.path.startswith('/api/'):
                    return JsonResponse({'detail': msg}, status=403)
                messages.error(request, msg)
                return redirect('management:headman_dashboard')
        return self.get_response(request)
