import time

from django.core import signing
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from authentication.constants import (
    EMAIL_CHANGE_OLD_VERIFIED_AT_KEY,
    EMAIL_CHANGE_OTP_NEW_KEY,
    EMAIL_CHANGE_OTP_NEW_SENT_AT_KEY,
    EMAIL_CHANGE_OTP_OLD_KEY,
    EMAIL_CHANGE_OTP_OLD_SENT_AT_KEY,
    EMAIL_CHANGE_PENDING_NEW_KEY,
)
from authentication.models import User
from authentication.two_factor import (
    EMAIL_OTP_MAX_AGE,
    EMAIL_OTP_RESEND_COOLDOWN,
    generate_email_otp,
    mask_email,
)
from management.models import Profile
from management.services.email_config import is_smtp_enabled, send_system_email

EMAIL_CHANGE_OLD_VERIFIED_MAX_AGE = 900
EMAIL_CHANGE_OTP_OLD_SALT = 'sharemint-email-change-old'
EMAIL_CHANGE_OTP_NEW_SALT = 'sharemint-email-change-new'


def get_current_user_email(user) -> str:
    return user.get_notification_email()


def clear_email_change_session(session) -> None:
    for key in (
        EMAIL_CHANGE_OLD_VERIFIED_AT_KEY,
        EMAIL_CHANGE_PENDING_NEW_KEY,
        EMAIL_CHANGE_OTP_OLD_KEY,
        EMAIL_CHANGE_OTP_OLD_SENT_AT_KEY,
        EMAIL_CHANGE_OTP_NEW_KEY,
        EMAIL_CHANGE_OTP_NEW_SENT_AT_KEY,
    ):
        session.pop(key, None)


def is_old_email_verified(session) -> bool:
    verified_at = session.get(EMAIL_CHANGE_OLD_VERIFIED_AT_KEY)
    if not verified_at:
        return False
    return time.time() - verified_at <= EMAIL_CHANGE_OLD_VERIFIED_MAX_AGE


def mark_old_email_verified(session) -> None:
    session[EMAIL_CHANGE_OLD_VERIFIED_AT_KEY] = time.time()


def _otp_session_keys(target: str) -> tuple[str, str, str]:
    if target == 'new':
        return (
            EMAIL_CHANGE_OTP_NEW_KEY,
            EMAIL_CHANGE_OTP_NEW_SENT_AT_KEY,
            EMAIL_CHANGE_OTP_NEW_SALT,
        )
    return (
        EMAIL_CHANGE_OTP_OLD_KEY,
        EMAIL_CHANGE_OTP_OLD_SENT_AT_KEY,
        EMAIL_CHANGE_OTP_OLD_SALT,
    )


def _can_resend_otp(session, sent_at_key: str) -> bool:
    last_sent = session.get(sent_at_key, 0)
    return time.time() - last_sent >= EMAIL_OTP_RESEND_COOLDOWN


def _store_otp(session, otp_key: str, sent_at_key: str, salt: str, code: str) -> None:
    signer = signing.TimestampSigner(salt=salt)
    session[otp_key] = signer.sign(code)
    session[sent_at_key] = time.time()


def _verify_stored_otp(session, otp_key: str, salt: str, token: str) -> bool:
    signed = session.get(otp_key)
    if not signed:
        return False
    try:
        signer = signing.TimestampSigner(salt=salt)
        code = signer.unsign(signed, max_age=EMAIL_OTP_MAX_AGE)
        if code == str(token).strip():
            session.pop(otp_key, None)
            return True
    except (signing.BadSignature, signing.SignatureExpired):
        return False
    return False


def send_email_change_code(session, recipient: str, purpose: str, target: str) -> tuple[bool, str]:
    otp_key, sent_at_key, salt = _otp_session_keys(target)
    if not _can_resend_otp(session, sent_at_key):
        return False, '发送过于频繁，请 60 秒后再试。'
    if not is_smtp_enabled():
        return False, '当前未启用 SMTP 邮件，无法发送验证码。请管理员在系统设置中启用 SMTP。'

    recipient = recipient.strip()
    if not recipient:
        return False, '邮箱地址无效。'

    code = generate_email_otp()
    try:
        send_system_email(
            subject=f'ShareMint 验证码 · {purpose}',
            message=(
                f'您好，\n\n'
                f'您的 ShareMint 邮箱验证码为：{code}\n\n'
                f'验证码 10 分钟内有效，请勿泄露给他人。\n'
                f'如非本人操作，请忽略此邮件。'
            ),
            recipient_list=[recipient],
        )
    except Exception as exc:
        return False, f'发送失败：{exc}'

    _store_otp(session, otp_key, sent_at_key, salt, code)
    return True, mask_email(recipient)


def verify_old_email_code(session, token: str) -> bool:
    otp_key, _, salt = _otp_session_keys('old')
    return _verify_stored_otp(session, otp_key, salt, token)


def verify_new_email_code(session, token: str) -> bool:
    otp_key, _, salt = _otp_session_keys('new')
    return _verify_stored_otp(session, otp_key, salt, token)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def email_is_taken_by_other_user(user, email: str) -> bool:
    email = normalize_email(email)
    if not email:
        return False
    if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
        return True
    return Profile.objects.filter(email__iexact=email).exclude(user_id=user.pk).exists()


def validate_new_email(user, new_email: str) -> str | None:
    new_email = new_email.strip()
    if not new_email:
        return '请输入新邮箱。'
    try:
        validate_email(new_email)
    except ValidationError:
        return '邮箱格式不正确。'

    current = get_current_user_email(user)
    if current and normalize_email(new_email) == normalize_email(current):
        return '新邮箱不能与当前邮箱相同。'

    if email_is_taken_by_other_user(user, new_email):
        return '该邮箱已被其他账号绑定，无法重复绑定。'
    return None


def apply_user_email_change(user, new_email: str) -> None:
    error = validate_new_email(user, new_email)
    if error:
        raise ValueError(error)

    new_email = normalize_email(new_email)
    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={'name': user.username},
    )
    profile.email = new_email
    profile.save(update_fields=['email'])
    user.email = new_email
    user.save(update_fields=['email'])
