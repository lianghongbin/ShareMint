import json

from django.conf import settings
from django.core.mail import EmailMessage, get_connection

from commissions.models import SystemConfig
from management.constants import EMAIL_CONFIG_KEY

EMAIL_MODE_CONSOLE = 'console'
EMAIL_MODE_SMTP = 'smtp'


def _defaults() -> dict:
    return {
        'mode': EMAIL_MODE_CONSOLE,
        'host': getattr(settings, 'EMAIL_HOST', 'localhost'),
        'port': int(getattr(settings, 'EMAIL_PORT', 587)),
        'username': getattr(settings, 'EMAIL_HOST_USER', ''),
        'password': getattr(settings, 'EMAIL_HOST_PASSWORD', ''),
        'use_tls': getattr(settings, 'EMAIL_USE_TLS', True),
        'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'ShareMint <noreply@sharemint.local>'),
    }


def get_email_config() -> dict:
    config = _defaults()
    stored = SystemConfig.get_json(EMAIL_CONFIG_KEY)
    if not stored:
        return config
    for key in config:
        if key not in stored:
            continue
        if key == 'port':
            config[key] = int(stored[key] or config[key])
        elif key == 'use_tls':
            config[key] = bool(stored[key])
        else:
            config[key] = stored[key]
    return config


def get_email_config_for_form() -> dict:
    config = get_email_config()
    config['has_password'] = bool(config.get('password'))
    config['password'] = ''
    return config


def save_email_config(data: dict) -> None:
    current = get_email_config()
    password = data.get('password', '').strip()
    if not password:
        password = current.get('password', '')

    payload = {
        'mode': data.get('mode', EMAIL_MODE_CONSOLE),
        'host': data.get('host', '').strip(),
        'port': int(data.get('port') or 587),
        'username': data.get('username', '').strip(),
        'password': password,
        'use_tls': bool(data.get('use_tls')),
        'from_email': data.get('from_email', '').strip() or _defaults()['from_email'],
    }
    SystemConfig.set_value(
        EMAIL_CONFIG_KEY,
        json.dumps(payload, ensure_ascii=False),
        '系统邮件服务配置',
    )


def validate_email_config(data: dict) -> str | None:
    mode = data.get('mode', EMAIL_MODE_CONSOLE)
    if mode == EMAIL_MODE_CONSOLE:
        return None
    if not data.get('host', '').strip():
        return '请填写 SMTP 服务器地址。'
    if not data.get('from_email', '').strip():
        return '请填写发件人地址。'
    try:
        port = int(data.get('port') or 0)
    except (TypeError, ValueError):
        return 'SMTP 端口必须是数字。'
    if port <= 0 or port > 65535:
        return 'SMTP 端口无效。'
    current = get_email_config()
    if not data.get('password', '').strip() and not current.get('password'):
        return '首次启用 SMTP 时请填写邮箱密码或授权码。'
    return None


def get_email_mode_label(mode: str) -> str:
    if mode == EMAIL_MODE_SMTP:
        return 'SMTP 邮件'
    return '开发模式（控制台）'


def is_smtp_enabled() -> bool:
    mode = str(get_email_config().get('mode', EMAIL_MODE_CONSOLE)).strip().lower()
    return mode == EMAIL_MODE_SMTP


def build_email_connection():
    config = get_email_config()
    if config['mode'] == EMAIL_MODE_CONSOLE:
        return get_connection(backend='django.core.mail.backends.console.EmailBackend')
    return get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host=config['host'],
        port=config['port'],
        username=config['username'],
        password=config['password'],
        use_tls=config['use_tls'],
    )


def send_system_email(subject: str, message: str, recipient_list: list[str]) -> None:
    config = get_email_config()
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=config['from_email'],
        to=recipient_list,
        connection=build_email_connection(),
    )
    email.send(fail_silently=False)


def send_test_email(recipient: str) -> None:
    send_system_email(
        subject='ShareMint 邮件服务测试',
        message=(
            '这是一封 ShareMint 邮件服务测试邮件。\n\n'
            '如果您收到此邮件，说明 SMTP 配置正确，可用于二次验证等功能。'
        ),
        recipient_list=[recipient],
    )
