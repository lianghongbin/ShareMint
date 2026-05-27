from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

from authentication.constants import TWO_FACTOR_VERIFIED_SESSION_KEY
from authentication.two_factor import is_fully_two_factor_verified


class FirstLoginPasswordChangeMiddleware:
    """首次登录强制修改密码拦截器。"""

    ALLOWED_PATH_PREFIXES = (
        '/static/',
        '/admin/logout/',
    )

    def __init__(self, get_response):
        self.get_response = get_response
        self._allowed_paths = None

    def _allowed_path_set(self):
        if self._allowed_paths is None:
            self._allowed_paths = {
                reverse('authentication:change_password'),
                reverse('authentication:logout'),
                reverse('authentication:login'),
                reverse('authentication:two_factor_verify'),
            }
        return self._allowed_paths

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and user.is_first_login:
            if not self._is_allowed(request):
                change_password_url = reverse('authentication:change_password')
                if request.path.startswith('/auth/api/'):
                    return JsonResponse(
                        {
                            'detail': '首次登录请先修改密码。',
                            'redirect': change_password_url,
                        },
                        status=403,
                    )
                return redirect('authentication:change_password')
        return self.get_response(request)

    def _is_allowed(self, request) -> bool:
        if any(request.path.startswith(prefix) for prefix in self.ALLOWED_PATH_PREFIXES):
            return True
        if request.path.startswith('/auth/oauth/'):
            return True
        if request.path in self._allowed_path_set():
            return True
        resolver_match = request.resolver_match
        if resolver_match and resolver_match.view_name == 'authentication:oauth_provider':
            return True
        return False


class TwoFactorVerificationMiddleware:
    """已开启二次验证的用户，登录后须完成 OTP 校验。"""

    ALLOWED_PATH_PREFIXES = (
        '/static/',
        '/admin/logout/',
    )

    def __init__(self, get_response):
        self.get_response = get_response
        self._allowed_paths = None

    def _allowed_path_set(self):
        if self._allowed_paths is None:
            self._allowed_paths = {
                reverse('authentication:two_factor_verify'),
                reverse('authentication:logout'),
                reverse('authentication:login'),
                reverse('authentication:change_password'),
            }
        return self._allowed_paths

    def __call__(self, request):
        user = request.user
        if (
            user.is_authenticated
            and not user.is_first_login
            and user.requires_two_factor_verification()
            and not is_fully_two_factor_verified(user, request.session)
            and not self._is_allowed(request)
        ):
            verify_url = reverse('authentication:two_factor_verify')
            if request.path.startswith('/auth/api/'):
                return JsonResponse(
                    {
                        'detail': '请先完成登录二次验证。',
                        'redirect': verify_url,
                    },
                    status=403,
                )
            return redirect('authentication:two_factor_verify')
        return self.get_response(request)

    def _is_allowed(self, request) -> bool:
        if any(request.path.startswith(prefix) for prefix in self.ALLOWED_PATH_PREFIXES):
            return True
        if request.path.startswith('/auth/oauth/'):
            return True
        if request.path in self._allowed_path_set():
            return True
        return False
