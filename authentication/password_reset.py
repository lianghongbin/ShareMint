from django.contrib.auth.tokens import default_token_generator
from django.db.models import Q
from django.http import HttpRequest
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from authentication.models import User
from authentication.two_factor import mask_email
from management.services.email_config import is_smtp_enabled, send_system_email


def find_user_by_identifier(identifier: str) -> User | None:
    value = identifier.strip()
    if not value:
        return None
    qs = User.objects.select_related('profile').filter(is_active=True)
    if '@' in value:
        return qs.filter(
            Q(email__iexact=value) | Q(profile__email__iexact=value),
        ).first()
    return qs.filter(username__iexact=value).first()


def build_password_reset_url(request: HttpRequest, user: User) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse('authentication:reset_password', kwargs={'uidb64': uid, 'token': token})
    return request.build_absolute_uri(path)


def validate_password_reset_token(user: User, token: str) -> bool:
    return bool(user and token and default_token_generator.check_token(user, token))


def decode_user_from_uid(uidb64: str) -> User | None:
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.select_related('profile').get(pk=uid, is_active=True)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


def get_user_reset_email(user: User) -> str:
    return user.get_notification_email()


def send_password_reset_email(request: HttpRequest, user: User) -> str:
    if not is_smtp_enabled():
        raise ValueError('当前未启用 SMTP 邮件，无法发送重置链接。请先在系统设置中配置并启用 SMTP。')

    recipient = get_user_reset_email(user)
    if not recipient:
        raise ValueError('该账号未绑定邮箱，无法发送重置邮件。请先在资料中填写邮箱。')

    reset_url = build_password_reset_url(request, user)
    send_system_email(
        subject='ShareMint 密码重置',
        message=(
            f'您好 {user.username}，\n\n'
            '我们收到了您的密码重置请求。请点击以下链接设置新密码：\n\n'
            f'{reset_url}\n\n'
            '该链接 1 小时内有效。若您未申请重置，请忽略此邮件。\n\n'
            'ShareMint'
        ),
        recipient_list=[recipient],
    )
    return mask_email(recipient)
