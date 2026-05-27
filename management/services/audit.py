import json
import re

from django.http import HttpRequest

from management.models import AuditLog

SENSITIVE_KEY_PATTERN = re.compile(
    r'password|token|secret|csrf|otp|authorization',
    re.IGNORECASE,
)

VIEW_ACTION_SUMMARIES = {
    'authentication:login': '登录系统',
    'authentication:logout': '退出登录',
    'authentication:forgot_password': '申请重置密码',
    'authentication:reset_password': '通过邮件重置密码',
    'authentication:change_password': '修改密码',
    'authentication:two_factor_verify': '登录二次验证',
    'authentication:settings_two_factor_setup_totp': '开启验证器二次验证',
    'authentication:settings_two_factor_setup_email': '开启邮件二次验证',
    'authentication:settings_two_factor_disable': '关闭二次验证',
    'authentication:settings_two_factor_send_code': '发送二次验证邮件',
    'authentication:api_change_password': '修改密码',
    'authentication:api_profile': '更新个人资料',
    'management:admin_create_headman': '团长开户',
    'management:admin_headman_detail': '更新团长资料',
    'management:admin_toggle_lock': '变更团长状态',
    'management:admin_reset_headman_password': '发送密码重置邮件',
    'management:admin_settings_price': '更新 GDT 价格',
    'management:admin_settings_commission': '保存提成设定',
    'management:admin_settings_email': '保存邮件配置',
    'management:admin_backup': '数据备份',
    'management:admin_restore': '数据还原',
    'management:headman_profile': '更新个人资料',
    'management:headman_add_member': '录入成员',
    'management:headman_add_investment': '成员追加投资',
    'management:headman_add_member_investment': '成员追加投资',
    'management:member_profile': '更新个人资料',
}

# 这些视图在业务代码里自行写入审计（含更新前后值），中间件不再兜底记录。
EXPLICIT_AUDIT_VIEWS = frozenset(VIEW_ACTION_SUMMARIES) - frozenset({
    'authentication:login',
    'authentication:two_factor_verify',
    'authentication:settings_two_factor_send_code',
})


def get_client_ip(request: HttpRequest) -> str | None:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def build_action_summary(request: HttpRequest, view_name: str) -> str:
    if view_name == 'authentication:login':
        return '登录系统' if request.user.is_authenticated else '登录失败'
    base = VIEW_ACTION_SUMMARIES.get(view_name, '系统操作')
    if request.method == 'POST' and hasattr(request, 'POST'):
        action = request.POST.get('action', '').strip()
        if view_name == 'management:admin_settings_email' and action == 'test':
            return '发送测试邮件'
        if view_name == 'authentication:settings_two_factor_setup_email' and action == 'send':
            return '发送绑定验证码'
        if view_name == 'authentication:settings_two_factor_setup_totp' and action == 'regenerate':
            return '重新生成验证器密钥'
        if view_name == 'authentication:two_factor_verify' and action == 'resend':
            return '重新发送登录验证码'
    return base


def profile_snapshot(profile) -> dict:
    return {
        '姓名': profile.name or '—',
        '手机': profile.phone or '—',
        '微信': profile.wechat or '—',
        '邮箱': profile.email or '—',
    }


def email_settings_snapshot(config: dict) -> dict:
    from management.services.email_config import EMAIL_MODE_SMTP, get_email_mode_label

    snapshot = {
        '发送方式': get_email_mode_label(config.get('mode', '')),
        '发件人': config.get('from_email') or '—',
    }
    if config.get('mode') == EMAIL_MODE_SMTP:
        snapshot.update({
            'SMTP 服务器': config.get('host') or '—',
            '端口': str(config.get('port') or '—'),
            '用户名': config.get('username') or '—',
            '启用 TLS': '是' if config.get('use_tls') else '否',
        })
    return snapshot


def changed_fields(before: dict, after: dict) -> tuple[dict, dict]:
    before_out = {}
    after_out = {}
    keys = set(before) | set(after)
    for key in keys:
        if before.get(key) != after.get(key):
            before_out[key] = before.get(key, '—')
            after_out[key] = after.get(key, '—')
    return before_out, after_out


def record_update_audit(
    request: HttpRequest,
    *,
    before: dict,
    after: dict,
    action: str = '',
    summary: str = '',
    note: str = '',
    user=None,
    status_code: int | None = None,
) -> AuditLog | None:
    """更新类操作：只记录有变化的字段，并写入修改前/修改后。"""
    before_data, after_data = changed_fields(before, after)
    if not before_data:
        return None
    return record_audit(
        request,
        action=action,
        summary=summary,
        before=before_data,
        after=after_data,
        note=note,
        user=user,
        status_code=status_code,
    )


def record_audit(
    request: HttpRequest,
    *,
    action: str = '',
    summary: str = '',
    before: dict | None = None,
    after: dict | None = None,
    note: str = '',
    detail: dict | None = None,
    user=None,
    status_code: int | None = None,
) -> AuditLog | None:
    if request.path.startswith('/static/'):
        return None

    actor = user
    if actor is None and getattr(request, 'user', None) and request.user.is_authenticated:
        actor = request.user

    username = ''
    role = ''
    if actor is not None and getattr(actor, 'is_authenticated', False):
        username = actor.get_username()
        role = getattr(actor, 'role', '') or ''
    elif detail:
        username = detail.get('username', '')

    payload = dict(detail or {})
    if before is not None or after is not None:
        payload['before'] = before or {}
        payload['after'] = after or {}
    if note:
        payload['note'] = note
    if not username and payload.get('before', {}).get('用户名'):
        username = payload['before']['用户名']

    if not action and request.resolver_match:
        action = request.resolver_match.view_name or ''
    if not summary:
        summary = build_action_summary(request, action)

    try:
        detail_text = json.dumps(payload, ensure_ascii=False) if payload else ''
    except TypeError:
        detail_text = str(payload)

    log = AuditLog.objects.create(
        user=actor if actor is not None and getattr(actor, 'is_authenticated', False) else None,
        username=username,
        role=role,
        action=action,
        summary=summary,
        detail=detail_text,
        method=request.method,
        path=request.path,
        ip_address=get_client_ip(request),
        status_code=status_code,
    )
    request._audit_logged = True
    return log


def parse_audit_detail(raw: str) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {'note': raw}
