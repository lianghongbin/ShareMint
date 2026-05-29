from decimal import Decimal

from django.conf import settings
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='用户',
    )
    name = models.CharField(max_length=100, verbose_name='姓名')
    phone = models.CharField(max_length=20, blank=True, verbose_name='手机号')
    wechat = models.CharField(max_length=50, blank=True, verbose_name='微信号')
    email = models.EmailField(blank=True, verbose_name='邮箱')
    bnb_wallet_address = models.CharField(
        max_length=42,
        blank=True,
        verbose_name='BNB 钱包地址',
    )

    class Meta:
        verbose_name = '用户档案'
        verbose_name_plural = '用户档案'

    def __str__(self):
        return f'{self.name} ({self.user.username})'


class Investment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='investments',
        limit_choices_to={'role': 'member'},
        verbose_name='成员',
    )
    investment_date = models.DateTimeField(verbose_name='投资时间')
    investment_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        verbose_name='投资金额 (USDT)',
    )
    holding_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        verbose_name='持有数量',
    )
    holding_currency = models.CharField(
        max_length=10,
        default='GDT',
        verbose_name='持有币种',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '投资记录'
        verbose_name_plural = '投资记录'
        ordering = ['-investment_date']

    def __str__(self):
        return f'{self.user.username} - {self.investment_amount} USDT'

    @property
    def current_market_value(self) -> Decimal:
        from commissions.models import SystemConfig

        return self.holding_quantity * SystemConfig.get_gdt_price()


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='操作者',
    )
    username = models.CharField(max_length=150, blank=True, db_index=True, verbose_name='用户名')
    role = models.CharField(max_length=20, blank=True, verbose_name='角色')
    action = models.CharField(max_length=120, blank=True, db_index=True, verbose_name='动作标识')
    summary = models.CharField(max_length=255, verbose_name='操作摘要')
    detail = models.TextField(blank=True, default='', verbose_name='详情')
    method = models.CharField(max_length=10, verbose_name='请求方法')
    path = models.CharField(max_length=255, verbose_name='请求路径')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP 地址')
    status_code = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name='状态码')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='操作时间')

    class Meta:
        verbose_name = '审计日志'
        verbose_name_plural = '审计日志'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M} {self.username} {self.summary}'

    @property
    def role_label(self) -> str:
        mapping = {
            'admin': '管理员',
            'headman': '团长',
            'member': '成员',
        }
        return mapping.get(self.role, self.role or '—')

    @property
    def detail_data(self) -> dict:
        from management.services.audit import parse_audit_detail

        return parse_audit_detail(self.detail)

    @property
    def before_data(self) -> dict:
        return self.detail_data.get('before', {})

    @property
    def after_data(self) -> dict:
        return self.detail_data.get('after', {})

    @property
    def note_text(self) -> str:
        return self.detail_data.get('note', '')

    @property
    def has_change_detail(self) -> bool:
        return bool(self.before_data or self.after_data)

    @property
    def compare_rows(self) -> list[dict]:
        keys = set(self.before_data) | set(self.after_data)
        rows = []
        for key in sorted(keys):
            rows.append({
                'label': key,
                'before': self.before_data.get(key, '—'),
                'after': self.after_data.get(key, '—'),
            })
        return rows
