from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_http_methods
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import Role, TwoFactorMethod, User
from authentication.serializers import PasswordChangeSerializer, ProfileSerializer, UserSerializer
from management.decorators import LOCKED_HEADMAN_MSG, reject_locked_headman
from authentication.two_factor import (
    generate_secret,
    get_pending_two_factor_methods,
    get_provisioning_uri,
    get_two_factor_method_label,
    get_user_notification_email,
    is_fully_two_factor_verified,
    issue_email_otp_to_user,
    mark_two_factor_method_verified,
    mask_email,
    qr_code_data_uri,
    reset_two_factor_verification,
    sync_two_factor_legacy_fields,
    verify_stored_email_otp,
    verify_token,
    verify_two_factor_token_for_method,
)
from authentication.email_change_context import (
    build_email_change_context,
    get_email_change_redirect_url,
    set_email_change_return,
)
from authentication.settings_context import build_settings_context
from management.models import Profile
from management.services.audit import profile_snapshot, record_audit, record_update_audit

from authentication.constants import (
    EMAIL_CHANGE_PENDING_NEW_KEY,
    EMAIL_OTP_SESSION_KEY,
    PENDING_TWO_FACTOR_SECRET_KEY,
    TWO_FACTOR_VERIFIED_SESSION_KEY,
)
from authentication.email_change import (
    apply_user_email_change,
    clear_email_change_session,
    get_current_user_email,
    is_old_email_verified,
    mark_old_email_verified,
    send_email_change_code,
    validate_new_email,
    verify_new_email_code,
    verify_old_email_code,
)


def role_sidebar_template(user) -> str:
    if user.is_admin:
        return 'management/admin/_sidebar.html'
    if user.is_headman:
        return 'management/headman/_sidebar.html'
    return 'management/member/_sidebar.html'


def _send_login_email_otp(request, user) -> tuple[bool, str]:
    return issue_email_otp_to_user(request.session, user, '登录验证')


def _prepare_login_two_factor(request, user):
    reset_two_factor_verification(request.session)
    pending = get_pending_two_factor_methods(user, request.session)
    if TwoFactorMethod.EMAIL in pending:
        ok, msg = _send_login_email_otp(request, user)
        if ok:
            messages.info(request, f'验证码已发送至 {msg}')
        else:
            messages.warning(request, msg)


class CustomLoginView(LoginView):
    template_name = 'authentication/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        if user.is_first_login:
            return HttpResponseRedirect(reverse_lazy('authentication:change_password'))
        if user.requires_two_factor_verification():
            _prepare_login_two_factor(self.request, user)
            return HttpResponseRedirect(reverse_lazy('authentication:two_factor_verify'))
        self.request.session[TWO_FACTOR_VERIFIED_SESSION_KEY] = True
        return response

    def get_success_url(self):
        return reverse_lazy('authentication:dashboard')


@login_required
@require_http_methods(['GET', 'POST'])
def change_password_view(request):
    if not request.user.is_first_login:
        blocked = reject_locked_headman(
            request,
            redirect_to='management:headman_profile' if request.user.is_headman else 'authentication:dashboard',
        )
        if blocked:
            return blocked
    template_name = (
        'authentication/change_password.html'
        if request.user.is_first_login
        else 'authentication/change_password_app.html'
    )
    context = {
        'force_change': request.user.is_first_login,
        'sidebar_template': role_sidebar_template(request.user),
    }
    if request.method == 'POST':
        serializer = PasswordChangeSerializer(
            data={
                'old_password': request.POST.get('old_password', ''),
                'new_password': request.POST.get('new_password', ''),
                'confirm_password': request.POST.get('confirm_password', ''),
            },
            context={'request': request},
        )
        if serializer.is_valid():
            user = serializer.save()
            update_session_auth_hash(request, user)
            record_audit(
                request,
                action='authentication:change_password',
                note='密码已更新。',
            )
            messages.success(request, '密码修改成功，欢迎使用系统。')
            if user.requires_two_factor_verification():
                _prepare_login_two_factor(request, user)
                return redirect('authentication:two_factor_verify')
            request.session[TWO_FACTOR_VERIFIED_SESSION_KEY] = True
            return redirect('authentication:dashboard')
        context['errors'] = serializer.errors
        return render(request, template_name, context)
    return render(request, template_name, context)


@login_required
def logout_view(request):
    from management.services.audit import record_audit

    record_audit(request, action='authentication:logout', status_code=302)
    logout(request)
    messages.info(request, '您已安全退出。')
    return redirect('authentication:login')


@login_required
def dashboard_view(request):
    from management.views import role_dashboard_redirect
    return role_dashboard_redirect(request)


@login_required
def settings_center_view(request):
    user = request.user
    if user.is_headman:
        return redirect('management:headman_profile')
    if user.is_member:
        return redirect('management:member_profile')
    if user.is_admin:
        return redirect('management:admin_profile')

    return render(
        request,
        'authentication/settings/index.html',
        {
            'sidebar_template': role_sidebar_template(user),
            **build_settings_context(user),
        },
    )


@login_required
@require_http_methods(['GET', 'POST'])
def settings_change_email_view(request):
    blocked = reject_locked_headman(
        request,
        redirect_to='management:headman_profile' if request.user.is_headman else 'authentication:dashboard',
    )
    if blocked:
        return blocked
    user = request.user
    return_to = request.POST.get('return_to') or request.GET.get('return_to')
    if return_to:
        set_email_change_return(request, return_to)

    current_email = get_current_user_email(user)
    has_current_email = bool(current_email)
    email_ctx = build_email_change_context(request)
    step = email_ctx['step']

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'send_old_code':
            if not has_current_email:
                messages.error(request, '当前未绑定邮箱。')
                return redirect(get_email_change_redirect_url(request, ongoing=True))
            ok, msg = send_email_change_code(
                request.session,
                current_email,
                '更换邮箱 · 原邮箱验证',
                'old',
            )
            if ok:
                messages.success(request, f'验证码已发送至 {msg}')
            else:
                messages.error(request, msg)
            return redirect(get_email_change_redirect_url(request, ongoing=True))

        if action == 'verify_old_code':
            if not has_current_email:
                messages.error(request, '当前未绑定邮箱。')
                return redirect(get_email_change_redirect_url(request, ongoing=True))
            token = request.POST.get('token', '').strip()
            if not token:
                messages.error(request, '请输入验证码。')
            elif verify_old_email_code(request.session, token):
                mark_old_email_verified(request.session)
                messages.success(request, '原邮箱验证通过，请填写新邮箱。')
                return redirect(get_email_change_redirect_url(request, ongoing=True))
            else:
                messages.error(request, '验证码不正确或已过期，请重试。')
            return redirect(get_email_change_redirect_url(request, ongoing=True))

        if action == 'send_new_code':
            if has_current_email and not is_old_email_verified(request.session):
                messages.error(request, '请先完成原邮箱验证。')
                return redirect(get_email_change_redirect_url(request, ongoing=True))

            new_email = request.POST.get('new_email', '').strip()
            confirm_email = request.POST.get('confirm_email', '').strip()
            if new_email != confirm_email:
                messages.error(request, '两次输入的新邮箱不一致。')
                return redirect(get_email_change_redirect_url(request, ongoing=True))

            error = validate_new_email(user, new_email)
            if error:
                messages.error(request, error)
                return redirect(get_email_change_redirect_url(request, ongoing=True))

            request.session[EMAIL_CHANGE_PENDING_NEW_KEY] = new_email
            ok, msg = send_email_change_code(
                request.session,
                new_email,
                '更换邮箱 · 新邮箱验证',
                'new',
            )
            if ok:
                messages.success(request, f'验证码已发送至 {msg}')
            else:
                messages.error(request, msg)
            return redirect(get_email_change_redirect_url(request, ongoing=True))

        if action == 'confirm_new_email':
            if has_current_email and not is_old_email_verified(request.session):
                messages.error(request, '请先完成原邮箱验证。')
                return redirect(get_email_change_redirect_url(request, ongoing=True))

            pending_new = request.session.get(EMAIL_CHANGE_PENDING_NEW_KEY, '').strip()
            if not pending_new:
                messages.error(request, '请先填写新邮箱并发送验证码。')
                return redirect(get_email_change_redirect_url(request, ongoing=True))

            token = request.POST.get('token', '').strip()
            if not token:
                messages.error(request, '请输入新邮箱验证码。')
            elif not verify_new_email_code(request.session, token):
                messages.error(request, '验证码不正确或已过期，请重试。')
            else:
                error = validate_new_email(user, pending_new)
                if error:
                    messages.error(request, error)
                else:
                    profile, _ = Profile.objects.get_or_create(
                        user=user,
                        defaults={'name': user.username},
                    )
                    before = profile_snapshot(profile)
                    try:
                        apply_user_email_change(user, pending_new)
                    except ValueError as exc:
                        messages.error(request, str(exc))
                        return redirect(get_email_change_redirect_url(request, ongoing=True))
                    profile.refresh_from_db()
                    record_update_audit(
                        request,
                        before=before,
                        after=profile_snapshot(profile),
                        action='authentication:settings_change_email',
                    )
                    clear_email_change_session(request.session)
                    messages.success(request, f'邮箱已更新为 {mask_email(pending_new)}。')
                    return redirect(get_email_change_redirect_url(request, ongoing=False))
            return redirect(get_email_change_redirect_url(request, ongoing=True))

    return render(
        request,
        'authentication/settings/change_email.html',
        {
            'sidebar_template': role_sidebar_template(user),
            **email_ctx,
        },
    )


@login_required
def settings_two_factor_setup_view(request):
    return redirect('authentication:settings')


def _reject_locked_headman_settings(request):
    if not request.user.is_headman:
        return None
    return reject_locked_headman(request, redirect_to='management:headman_profile')


@login_required
@require_http_methods(['GET', 'POST'])
def settings_two_factor_setup_totp_view(request):
    blocked = _reject_locked_headman_settings(request)
    if blocked:
        return blocked
    user = request.user
    if user.two_factor_totp_enabled:
        messages.info(request, '验证器 App 二次验证已开启。')
        return redirect('authentication:settings')

    if request.method == 'POST':
        action = request.POST.get('action', 'verify')
        pending_secret = request.session.get(PENDING_TWO_FACTOR_SECRET_KEY, '')

        if action == 'regenerate' or not pending_secret:
            pending_secret = generate_secret()
            request.session[PENDING_TWO_FACTOR_SECRET_KEY] = pending_secret
        elif action == 'verify':
            token = request.POST.get('token', '')
            if not pending_secret:
                messages.error(request, '验证会话已过期，请重新获取密钥。')
                return redirect('authentication:settings_two_factor_setup_totp')

            if verify_token(pending_secret, token):
                user.two_factor_secret = pending_secret
                user.two_factor_totp_enabled = True
                sync_two_factor_legacy_fields(user)
                user.save(update_fields=[
                    'two_factor_secret',
                    'two_factor_totp_enabled',
                    'two_factor_enabled',
                    'two_factor_method',
                ])
                request.session.pop(PENDING_TWO_FACTOR_SECRET_KEY, None)
                request.session[TWO_FACTOR_VERIFIED_SESSION_KEY] = True
                from management.services.audit import record_update_audit

                record_update_audit(
                    request,
                    before={'二次验证': '未开启'},
                    after={'二次验证': '已开启', '方式': '验证器 App'},
                    action='authentication:settings_two_factor_setup_totp',
                )
                messages.success(request, '验证器 App 二次验证已开启。')
                return redirect('authentication:settings')

            messages.error(request, '验证码不正确，请重试。')

    pending_secret = request.session.get(PENDING_TWO_FACTOR_SECRET_KEY)
    if not pending_secret:
        pending_secret = generate_secret()
        request.session[PENDING_TWO_FACTOR_SECRET_KEY] = pending_secret

    provisioning_uri = get_provisioning_uri(user, pending_secret)
    return render(
        request,
        'authentication/settings/two_factor_setup.html',
        {
            'sidebar_template': role_sidebar_template(user),
            'secret': pending_secret,
            'provisioning_uri': provisioning_uri,
            'qr_code_data_uri': qr_code_data_uri(provisioning_uri),
        },
    )


@login_required
@require_http_methods(['GET', 'POST'])
def settings_two_factor_setup_email_view(request):
    blocked = _reject_locked_headman_settings(request)
    if blocked:
        return blocked
    user = request.user
    if user.two_factor_email_enabled:
        messages.info(request, '邮件二次验证已开启。')
        return redirect('authentication:settings')

    notification_email = get_user_notification_email(user)
    if not notification_email:
        messages.error(request, '请先在设置中心绑定邮箱，再开启邮件验证。')
        return redirect('authentication:settings')

    if request.method == 'POST':
        action = request.POST.get('action', 'verify')
        if action == 'send':
            ok, msg = issue_email_otp_to_user(request.session, user, '开启二次验证')
            if ok:
                messages.success(request, f'验证码已发送至 {msg}')
            else:
                messages.error(request, msg)
        elif action == 'verify':
            token = request.POST.get('token', '').strip()
            if not token:
                messages.error(request, '请输入邮箱验证码。')
            elif verify_stored_email_otp(request.session, token):
                user.two_factor_email_enabled = True
                sync_two_factor_legacy_fields(user)
                user.save(update_fields=[
                    'two_factor_email_enabled',
                    'two_factor_enabled',
                    'two_factor_method',
                ])
                request.session[TWO_FACTOR_VERIFIED_SESSION_KEY] = True
                from management.services.audit import record_update_audit

                record_update_audit(
                    request,
                    before={'二次验证': '未开启'},
                    after={'二次验证': '已开启', '方式': '邮件验证'},
                    action='authentication:settings_two_factor_setup_email',
                )
                messages.success(request, '邮件二次验证已开启。')
                return redirect('authentication:settings')
            messages.error(request, '验证码不正确或已过期，请重试。')

    return render(
        request,
        'authentication/settings/two_factor_setup_email.html',
        {
            'sidebar_template': role_sidebar_template(user),
            'masked_email': mask_email(notification_email),
        },
    )


@login_required
@require_http_methods(['POST'])
def settings_two_factor_send_code_view(request):
    blocked = _reject_locked_headman_settings(request)
    if blocked:
        return blocked
    user = request.user
    purpose = request.POST.get('purpose', '关闭二次验证')
    if not user.two_factor_email_enabled:
        messages.info(request, '当前未开启邮件二次验证。')
        return redirect('authentication:settings')

    ok, msg = issue_email_otp_to_user(request.session, user, purpose)
    if ok:
        messages.success(request, f'验证码已发送至 {msg}')
    else:
        messages.error(request, msg)
    return redirect('authentication:settings')


@login_required
@require_http_methods(['POST'])
def settings_two_factor_disable_view(request):
    blocked = _reject_locked_headman_settings(request)
    if blocked:
        return blocked
    user = request.user
    method = request.POST.get('method', '').strip()
    password = request.POST.get('password', '')
    token = request.POST.get('token', '').strip()

    if method == TwoFactorMethod.TOTP:
        if not user.two_factor_totp_enabled:
            messages.info(request, '验证器 App 二次验证未开启。')
            return redirect('authentication:settings')
        method_label = '验证器 App'
    elif method == TwoFactorMethod.EMAIL:
        if not user.two_factor_email_enabled:
            messages.info(request, '邮件二次验证未开启。')
            return redirect('authentication:settings')
        method_label = '邮件验证'
    else:
        messages.error(request, '无效的二次验证方式。')
        return redirect('authentication:settings')

    if not user.check_password(password):
        messages.error(request, '密码不正确，无法关闭二次验证。')
        return redirect('authentication:settings')

    if not verify_two_factor_token_for_method(user, request.session, token, method):
        messages.error(request, '验证码不正确，无法关闭二次验证。')
        return redirect('authentication:settings')

    if method == TwoFactorMethod.TOTP:
        user.two_factor_totp_enabled = False
        user.two_factor_secret = ''
    else:
        user.two_factor_email_enabled = False

    sync_two_factor_legacy_fields(user)
    user.save(update_fields=[
        'two_factor_totp_enabled',
        'two_factor_email_enabled',
        'two_factor_secret',
        'two_factor_enabled',
        'two_factor_method',
    ])
    request.session[TWO_FACTOR_VERIFIED_SESSION_KEY] = True
    request.session.pop(PENDING_TWO_FACTOR_SECRET_KEY, None)
    from management.services.audit import record_update_audit

    record_update_audit(
        request,
        before={'二次验证': '已开启', '方式': method_label},
        after={'二次验证': f'{method_label} 已关闭'},
        action='authentication:settings_two_factor_disable',
    )
    messages.success(request, f'{method_label} 二次验证已关闭。')
    return redirect('authentication:settings')


@login_required
@require_http_methods(['GET', 'POST'])
def two_factor_verify_view(request):
    user = request.user
    if not user.requires_two_factor_verification():
        request.session[TWO_FACTOR_VERIFIED_SESSION_KEY] = True
        return redirect('authentication:dashboard')

    if is_fully_two_factor_verified(user, request.session):
        request.session[TWO_FACTOR_VERIFIED_SESSION_KEY] = True
        return redirect('authentication:dashboard')

    pending = get_pending_two_factor_methods(user, request.session)
    current_method = pending[0]
    is_email_method = current_method == TwoFactorMethod.EMAIL
    masked_email = mask_email(get_user_notification_email(user)) if is_email_method else ''
    remaining_count = len(pending)

    if request.method == 'POST':
        action = request.POST.get('action', 'verify')
        if action == 'resend' and is_email_method:
            ok, msg = _send_login_email_otp(request, user)
            if ok:
                messages.success(request, f'验证码已重新发送至 {msg}')
            else:
                messages.error(request, msg)
        else:
            token = request.POST.get('token', '').strip()
            if verify_two_factor_token_for_method(user, request.session, token, current_method):
                mark_two_factor_method_verified(request.session, current_method)
                if is_fully_two_factor_verified(user, request.session):
                    request.session[TWO_FACTOR_VERIFIED_SESSION_KEY] = True
                    messages.success(request, '二次验证通过，欢迎回来。')
                    return redirect('authentication:dashboard')
                next_pending = get_pending_two_factor_methods(user, request.session)
                next_label = get_two_factor_method_label(next_pending[0])
                messages.success(request, f'验证通过，请继续完成{next_label}。')
                return redirect('authentication:two_factor_verify')
            messages.error(request, '验证码不正确，请重试。')
    elif is_email_method and not request.session.get(EMAIL_OTP_SESSION_KEY):
        ok, msg = _send_login_email_otp(request, user)
        if ok:
            messages.info(request, f'验证码已发送至 {msg}')

    return render(
        request,
        'authentication/two_factor_verify.html',
        {
            'is_email_method': is_email_method,
            'masked_email': masked_email,
            'current_method_label': get_two_factor_method_label(current_method),
            'remaining_count': remaining_count,
        },
    )


class CurrentUserAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ProfileAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(
            user=request.user,
            defaults={'name': request.user.username},
        )
        return Response(ProfileSerializer(profile, context={'request': request}).data)

    def patch(self, request):
        if request.user.is_headman and request.user.is_locked:
            return Response({'detail': LOCKED_HEADMAN_MSG}, status=status.HTTP_403_FORBIDDEN)
        profile, _ = Profile.objects.get_or_create(
            user=request.user,
            defaults={'name': request.user.username},
        )
        from management.services.audit import profile_snapshot, record_update_audit

        before = profile_snapshot(profile)
        serializer = ProfileSerializer(
            profile,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record_update_audit(
            request,
            before=before,
            after=profile_snapshot(profile),
            action='authentication:api_profile',
        )
        return Response(serializer.data)


class PasswordChangeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.is_headman and request.user.is_locked:
            return Response({'detail': LOCKED_HEADMAN_MSG}, status=status.HTTP_403_FORBIDDEN)
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': '密码修改成功。'}, status=status.HTTP_200_OK)


@require_http_methods(['GET', 'POST'])
def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect('authentication:dashboard')

    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        from authentication.password_reset import find_user_by_identifier, send_password_reset_email
        from management.services.audit import record_audit

        user = find_user_by_identifier(identifier)
        if user:
            try:
                masked = send_password_reset_email(request, user)
                record_audit(
                    request,
                    action='authentication:forgot_password',
                    summary='申请重置密码',
                    after={'账号': user.username, '邮箱': masked},
                    user=user,
                )
            except ValueError as exc:
                messages.error(request, str(exc))
                return render(request, 'authentication/forgot_password.html', {
                    'identifier': identifier,
                })
            except Exception as exc:
                messages.error(request, f'发送失败：{exc}')
                return render(request, 'authentication/forgot_password.html', {
                    'identifier': identifier,
                })
        messages.success(
            request,
            '如果该账号存在且已绑定邮箱，重置链接已发送，请查收邮件（含垃圾邮件箱）。',
        )
        return redirect('authentication:login')

    return render(request, 'authentication/forgot_password.html')


@require_http_methods(['GET', 'POST'])
def reset_password_view(request, uidb64, token):
    if request.user.is_authenticated:
        logout(request)

    from authentication.password_reset import decode_user_from_uid, validate_password_reset_token
    from authentication.password_history import change_user_password
    from management.services.audit import record_audit

    user = decode_user_from_uid(uidb64)
    if not user or not validate_password_reset_token(user, token):
        return render(request, 'authentication/reset_password.html', {
            'invalid': True,
        })

    errors = {}
    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        if len(new_password) < 8:
            errors['new_password'] = '新密码至少 8 位。'
        elif new_password != confirm_password:
            errors['confirm_password'] = '两次输入的新密码不一致。'
        else:
            try:
                change_user_password(user, new_password)
            except ValueError as exc:
                errors['new_password'] = str(exc)
            else:
                record_audit(
                    request,
                    action='authentication:reset_password',
                    summary='通过邮件重置密码',
                    user=user,
                )
                messages.success(request, '密码已重置，请使用新密码登录。')
                return redirect('authentication:login')

    return render(request, 'authentication/reset_password.html', {
        'invalid': False,
        'errors': errors,
        'uidb64': uidb64,
        'token': token,
    })
