"""
Django settings for core project.
"""

import os
import socket
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-96=--+g8a7lk(u_zni=p_du=cnpv%=)n87(de41n7xeu4my8s-'

DEBUG = True

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


CSRF_TRUSTED_ORIGINS = _dev_csrf_origins() if DEBUG else []

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
    'management',
    'commissions.apps.CommissionsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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
        'NAME': BASE_DIR / 'db.sqlite3',
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
