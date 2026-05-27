import base64
import io
import secrets
import time

import pyotp
import qrcode
from django.core import signing

from authentication.constants import (
    EMAIL_OTP_SENT_AT_KEY,
    EMAIL_OTP_SESSION_KEY,
    TWO_FACTOR_VERIFIED_METHODS_KEY,
    TWO_FACTOR_VERIFIED_SESSION_KEY,
)

EMAIL_OTP_SALT = 'sharemint-2fa-email'
EMAIL_OTP_MAX_AGE = 600
EMAIL_OTP_RESEND_COOLDOWN = 60


def generate_secret() -> str:
    return pyotp.random_base32()


def get_totp(secret: str) -> pyotp.TOTP:
    return pyotp.TOTP(secret)


def verify_token(secret: str, token: str) -> bool:
    if not secret or not token:
        return False
    try:
        return get_totp(secret).verify(str(token).strip(), valid_window=1)
    except (TypeError, ValueError):
        return False


def get_provisioning_uri(user, secret: str) -> str:
    return get_totp(secret).provisioning_uri(
        name=user.username,
        issuer_name='ShareMint',
    )


def qr_code_data_uri(provisioning_uri: str) -> str:
    img = qrcode.make(provisioning_uri)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f'data:image/png;base64,{encoded}'


def generate_email_otp() -> str:
    return f'{secrets.randbelow(1000000):06d}'


def mask_email(email: str) -> str:
    if not email or '@' not in email:
        return email or ''
    local, domain = email.split('@', 1)
    if len(local) <= 1:
        masked_local = '*'
    else:
        masked_local = f'{local[0]}***'
    return f'{masked_local}@{domain}'


def get_user_notification_email(user) -> str:
    if user.email:
        return user.email.strip()
    profile = getattr(user, 'profile', None)
    if profile and profile.email:
        return profile.email.strip()
    return ''


def store_email_otp(session, code: str) -> None:
    signer = signing.TimestampSigner(salt=EMAIL_OTP_SALT)
    session[EMAIL_OTP_SESSION_KEY] = signer.sign(code)
    session[EMAIL_OTP_SENT_AT_KEY] = time.time()


def clear_email_otp(session) -> None:
    session.pop(EMAIL_OTP_SESSION_KEY, None)


def verify_stored_email_otp(session, token: str) -> bool:
    signed = session.get(EMAIL_OTP_SESSION_KEY)
    if not signed:
        return False
    try:
        signer = signing.TimestampSigner(salt=EMAIL_OTP_SALT)
        code = signer.unsign(signed, max_age=EMAIL_OTP_MAX_AGE)
        if code == str(token).strip():
            clear_email_otp(session)
            return True
    except (signing.BadSignature, signing.SignatureExpired):
        return False
    return False


def can_resend_email_otp(session, cooldown: int = EMAIL_OTP_RESEND_COOLDOWN) -> bool:
    last_sent = session.get(EMAIL_OTP_SENT_AT_KEY, 0)
    return time.time() - last_sent >= cooldown


def send_two_factor_email(user, code: str, purpose: str) -> None:
    from management.services.email_config import is_smtp_enabled, send_system_email

    if not is_smtp_enabled():
        raise ValueError(
            '当前未启用 SMTP 邮件，无法发送验证码。'
            '请管理员在「系统设置 → SMTP 邮件」中启用 SMTP。'
        )
    email = get_user_notification_email(user)
    if not email:
        raise ValueError('未绑定邮箱，请先在设置中心绑定邮箱。')
    subject = f'ShareMint 验证码 · {purpose}'
    message = (
        f'您好 {user.username}，\n\n'
        f'您的 ShareMint 二次验证码为：{code}\n\n'
        f'验证码 10 分钟内有效，请勿泄露给他人。\n'
        f'如非本人操作，请忽略此邮件。'
    )
    send_system_email(subject, message, [email])


def issue_email_otp_to_user(session, user, purpose: str) -> tuple[bool, str]:
    if not can_resend_email_otp(session):
        return False, '发送过于频繁，请 60 秒后再试。'
    email = get_user_notification_email(user)
    if not email:
        return False, '未绑定邮箱，请先在设置中心绑定邮箱。'
    code = generate_email_otp()
    try:
        send_two_factor_email(user, code, purpose)
    except Exception as exc:
        return False, f'发送失败：{exc}'
    store_email_otp(session, code)
    return True, mask_email(email)


def get_active_two_factor_methods(user) -> list[str]:
    return user.get_active_two_factor_methods()


def get_pending_two_factor_methods(user, session) -> list[str]:
    verified = session.get(TWO_FACTOR_VERIFIED_METHODS_KEY, [])
    return [method for method in get_active_two_factor_methods(user) if method not in verified]


def mark_two_factor_method_verified(session, method: str) -> None:
    verified = list(session.get(TWO_FACTOR_VERIFIED_METHODS_KEY, []))
    if method not in verified:
        verified.append(method)
    session[TWO_FACTOR_VERIFIED_METHODS_KEY] = verified


def is_fully_two_factor_verified(user, session) -> bool:
    return not get_pending_two_factor_methods(user, session)


def reset_two_factor_verification(session) -> None:
    session.pop(TWO_FACTOR_VERIFIED_METHODS_KEY, None)
    session[TWO_FACTOR_VERIFIED_SESSION_KEY] = False


def sync_two_factor_legacy_fields(user) -> None:
    from authentication.models import TwoFactorMethod

    user.two_factor_enabled = bool(get_active_two_factor_methods(user))
    methods = get_active_two_factor_methods(user)
    if TwoFactorMethod.TOTP in methods:
        user.two_factor_method = TwoFactorMethod.TOTP
    elif TwoFactorMethod.EMAIL in methods:
        user.two_factor_method = TwoFactorMethod.EMAIL
    else:
        user.two_factor_method = ''


def verify_two_factor_token_for_method(user, session, token: str, method: str) -> bool:
    from authentication.models import TwoFactorMethod

    if method == TwoFactorMethod.EMAIL:
        return verify_stored_email_otp(session, token)
    return verify_token(user.two_factor_secret, token)


def get_two_factor_method_label(method: str) -> str:
    from authentication.models import TwoFactorMethod

    if method == TwoFactorMethod.EMAIL:
        return '邮件验证'
    return '验证器 App'
