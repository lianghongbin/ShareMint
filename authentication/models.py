from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class Role(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    HEADMAN = 'headman', 'Headman'
    MEMBER = 'member', 'Member'


class TwoFactorMethod(models.TextChoices):
    TOTP = 'totp', '验证器 App'
    EMAIL = 'email', '邮件验证'


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        verbose_name='角色',
    )
    is_first_login = models.BooleanField(default=True, verbose_name='是否首次登录')
    is_locked = models.BooleanField(default=False, verbose_name='是否锁定')
    two_factor_enabled = models.BooleanField(default=False, verbose_name='是否开启二次验证')
    two_factor_totp_enabled = models.BooleanField(default=False, verbose_name='验证器二次验证')
    two_factor_email_enabled = models.BooleanField(default=False, verbose_name='邮件二次验证')
    two_factor_method = models.CharField(
        max_length=10,
        choices=TwoFactorMethod.choices,
        blank=True,
        default='',
        verbose_name='二次验证方式',
    )
    two_factor_secret = models.CharField(
        max_length=32,
        blank=True,
        default='',
        verbose_name='二次验证密钥',
    )
    referrer = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='referred_members',
        limit_choices_to={'role': Role.HEADMAN},
        verbose_name='所属团长',
    )

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def clean(self):
        super().clean()
        if self.role == Role.MEMBER and not self.referrer_id:
            raise ValidationError({'referrer': '普通成员必须指定所属团长。'})
        if self.referrer_id and self.referrer.role != Role.HEADMAN:
            raise ValidationError({'referrer': '推荐人必须是团长角色。'})
        if self.pk and self.referrer_id == self.pk:
            raise ValidationError({'referrer': '不能将自己设为推荐人。'})

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    @property
    def is_headman(self):
        return self.role == Role.HEADMAN

    @property
    def is_member(self):
        return self.role == Role.MEMBER

    def get_notification_email(self) -> str:
        if self.email:
            return self.email.strip()
        profile = getattr(self, 'profile', None)
        if profile and profile.email:
            return profile.email.strip()
        return ''

    def get_active_two_factor_methods(self) -> list[str]:
        methods = []
        if self.two_factor_totp_enabled and self.two_factor_secret:
            methods.append(TwoFactorMethod.TOTP)
        if self.two_factor_email_enabled and self.get_notification_email():
            methods.append(TwoFactorMethod.EMAIL)
        return methods

    def requires_two_factor_verification(self) -> bool:
        return bool(self.get_active_two_factor_methods())

    def get_two_factor_method_display_label(self) -> str:
        labels = []
        if self.two_factor_totp_enabled and self.two_factor_secret:
            labels.append('验证器 App')
        if self.two_factor_email_enabled and self.get_notification_email():
            labels.append('邮件验证')
        return '、'.join(labels) if labels else ''

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


class PasswordHistory(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_history',
        verbose_name='用户',
    )
    password = models.CharField(max_length=128, verbose_name='密码哈希')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='记录时间')

    class Meta:
        verbose_name = '密码历史'
        verbose_name_plural = '密码历史'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} @ {self.created_at:%Y-%m-%d %H:%M}'
