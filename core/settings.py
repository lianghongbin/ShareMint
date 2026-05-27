"""
Django settings for core project.
"""

import os
import sys

# 绝对明显的调试打印
print("\n" + "!"*60, file=sys.stderr)
print("!!! DJANGO SETTINGS LOADING FROM: " + __file__, file=sys.stderr)
print("!!! CURRENT CSRF_TRUSTED_ORIGINS SETTING IS RUNNING", file=sys.stderr)
print("!"*60 + "\n", file=sys.stderr)

import socket
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-96=--+g8a7lk(u_zni=p_du=cnpv%=)n87(de41n7xeu4my8s-',
)

DEBUG = os.environ.get('DEBUG', '1').lower() in ('1', 'true', 'yes')

# 调试期间允许所有 HOST，排除域名匹配问题
ALLOWED_HOSTS = ['*']


def _dev_csrf_origins() -> list[str]:
    """开发环境：允许本机 IP 访问时的 CSRF 校验（手机局域网调试）。"""
    port = os.environ.get('RUNSERVER_PORT', '9000')
    origins = {
        f'http://127.0.0.1:{port}',
        f'http://localhost:{port}',
    }
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            origins.add(f'http://{info[4][0]}:{port}')
    except OSError:
        pass
    return sorted(origins)


CSRF_TRUSTED_ORIGINS = _dev_csrf_origins()
# 强制添加，并打印日志
CSRF_TRUSTED_ORIGINS += [
    'https://gdt.skyvl.com',
    'http://gdt.skyvl.com',
]

# 允许从环境变量读取更多的源
_env_csrf = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
for origin in _env_csrf:
    if origin.strip():
        CSRF_TRUSTED_ORIGINS.append(origin.strip())

# 调试打印：这将出现在 docker logs 中
import sys
print("="*50, file=sys.stderr)
print(f"DEBUG: FINAL CSRF_TRUSTED_ORIGINS = {CSRF_TRUSTED_ORIGINS}", file=sys.stderr)
print(f"DEBUG: ENV ALLOWED_HOSTS = {os.environ.get('ALLOWED_HOSTS')}", file=sys.stderr)
print("="*50, file=sys.stderr)

# CSRF 相关安全设置
CSRF_COOKIE_DOMAIN = '.skyvl.com'  # 显式允许子域名共享 cookie
CSRF_COOKIE_SECURE = True          # 隧道是 HTTPS，必须设为 True
SESSION_COOKIE_SECURE = True       # Session Cookie 也必须设为 True
CSRF_COOKIE_SAMESITE = 'Lax'       # 浏览器安全策略
SESSION_COOKIE_SAMESITE = 'Lax'

# 核心：告诉 Django 这是一个受信任的代理，并使用 HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
SECURE_SSL_REDIRECT = False        # 由隧道处理重定向，Django 内部不强制

# 调试打印，确认配置加载
import sys
print("!!! TUNNEL SETTINGS APPLIED: COOKIE_SECURE=TRUE", file=sys.stderr)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'authentication.apps.AuthenticationConfig',
    'management.apps.ManagementConfig',
    'commissions.apps.CommissionsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'authentication.middleware.FirstLoginPasswordChangeMiddleware',
    'authentication.middleware.TwoFactorVerificationMiddleware',
    'management.middleware.AuditMiddleware',
    'management.middleware.HeadmanLockMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'management.context_processors.app_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # 强制锁定使用根目录下的 db.sqlite3，忽略任何环境变量干扰
        'NAME': str(BASE_DIR / 'db.sqlite3'),
    }
}

AUTH_USER_MODEL = 'authentication.User'

AUTHENTICATION_BACKENDS = [
    'authentication.backends.CaseInsensitiveUsernameBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'authentication:login'
LOGIN_REDIRECT_URL = 'authentication:dashboard'
LOGOUT_REDIRECT_URL = 'authentication:login'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

CORS_ALLOW_ALL_ORIGINS = DEBUG

CORS_ALLOWED_ORIGINS = []

# 开发服务器默认端口
RUNSERVER_DEFAULT_PORT = int(os.environ.get('RUNSERVER_PORT', '9000'))

# 系统超级管理员初始账号（通过 python manage.py init_admin 写入，非用户注册）
DEFAULT_ADMIN_USERNAME = os.environ.get('DEFAULT_ADMIN_USERNAME', 'admin')
DEFAULT_ADMIN_PASSWORD = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'ShareMint@2026')
DEFAULT_ADMIN_EMAIL = os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@sharemint.local')

# 管理员重置团长/成员密码时使用的初始密码
DEFAULT_INITIAL_PASSWORD = os.environ.get('DEFAULT_INITIAL_PASSWORD', 'ShareMint@2026')

BACKUP_DIR = BASE_DIR / 'backups'

# 邮件（开发环境默认输出到控制台；管理员可在「系统设置 → 邮件服务」配置 SMTP）
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'core.email_backend.SystemConfigEmailBackend',
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'ShareMint <noreply@sharemint.local>')

# 邮件重置密码链接有效期（秒）
PASSWORD_RESET_TIMEOUT = int(os.environ.get('PASSWORD_RESET_TIMEOUT', '3600'))
