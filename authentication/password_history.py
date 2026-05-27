from django.contrib.auth.hashers import check_password
from django.db import transaction

from authentication.models import PasswordHistory

PASSWORD_HISTORY_LIMIT = 3
REUSED_PASSWORD_MESSAGE = '新密码不能与最近 3 次使用过的密码相同。'


def is_password_reused(user, raw_password: str) -> bool:
    if user.check_password(raw_password):
        return True
    recent_hashes = (
        PasswordHistory.objects.filter(user=user)
        .order_by('-created_at')
        .values_list('password', flat=True)[:PASSWORD_HISTORY_LIMIT]
    )
    return any(check_password(raw_password, password_hash) for password_hash in recent_hashes)


def change_user_password(user, raw_password: str) -> None:
    if is_password_reused(user, raw_password):
        raise ValueError(REUSED_PASSWORD_MESSAGE)

    with transaction.atomic():
        if user.password:
            PasswordHistory.objects.create(user=user, password=user.password)
        user.set_password(raw_password)
        user.is_first_login = False
        user.save(update_fields=['password', 'is_first_login'])
        _prune_password_history(user)


def _prune_password_history(user) -> None:
    keep_ids = list(
        PasswordHistory.objects.filter(user=user)
        .order_by('-created_at')
        .values_list('pk', flat=True)[:PASSWORD_HISTORY_LIMIT]
    )
    if not keep_ids:
        return
    PasswordHistory.objects.filter(user=user).exclude(pk__in=keep_ids).delete()
