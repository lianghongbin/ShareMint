import json
from decimal import Decimal, InvalidOperation

from django.db import models

from .constants import (
    COMMISSION_TIERS_KEY,
    DEFAULT_COMMISSION_TIERS,
    DEFAULT_GDT_PRICE,
    DEFAULT_HEADMAN_BASE_BONUS_CURRENCY,
    DEFAULT_HEADMAN_BASE_BONUS_RATE,
    GDT_CURRENT_PRICE_KEY,
    HEADMAN_BASE_BONUS_CURRENCY_KEY,
    HEADMAN_BASE_BONUS_RATE_KEY,
)


class SystemConfig(models.Model):
    key = models.CharField(max_length=100, unique=True, verbose_name='配置键')
    value = models.TextField(verbose_name='配置值')
    description = models.CharField(max_length=255, blank=True, verbose_name='说明')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '系统配置'
        verbose_name_plural = '系统配置'

    def __str__(self):
        return self.key

    @classmethod
    def get_value(cls, key: str, default: str = '') -> str:
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def get_decimal(cls, key: str, default: Decimal = Decimal('0')) -> Decimal:
        raw = cls.get_value(key)
        if not raw:
            return default
        try:
            return Decimal(raw)
        except InvalidOperation:
            return default

    @classmethod
    def get_json(cls, key: str, default=None):
        raw = cls.get_value(key)
        if not raw:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default

    @classmethod
    def set_value(cls, key: str, value: str, description: str = '') -> 'SystemConfig':
        obj, _ = cls.objects.update_or_create(
            key=key,
            defaults={'value': value, 'description': description},
        )
        return obj

    @classmethod
    def ensure_default(cls, key: str, value: str, description: str = '') -> 'SystemConfig':
        """仅当配置不存在时写入默认值，不覆盖已有配置。"""
        obj, created = cls.objects.get_or_create(
            key=key,
            defaults={'value': value, 'description': description},
        )
        return obj

    @classmethod
    def get_gdt_price(cls) -> Decimal:
        return cls.get_decimal(GDT_CURRENT_PRICE_KEY, DEFAULT_GDT_PRICE)

    @classmethod
    def get_commission_tiers(cls) -> list:
        return cls.get_json(COMMISSION_TIERS_KEY, DEFAULT_COMMISSION_TIERS)

    @classmethod
    def seed_defaults(cls):
        cls.ensure_default(
            GDT_CURRENT_PRICE_KEY,
            str(DEFAULT_GDT_PRICE),
            'GDT 当前全局唯一价格',
        )
        cls.ensure_default(
            COMMISSION_TIERS_KEY,
            json.dumps(DEFAULT_COMMISSION_TIERS),
            '团长阶梯提成比例 JSON 配置',
        )
        cls.ensure_default(
            HEADMAN_BASE_BONUS_RATE_KEY,
            str(DEFAULT_HEADMAN_BASE_BONUS_RATE),
            '大团长基础奖励比例',
        )
        cls.ensure_default(
            HEADMAN_BASE_BONUS_CURRENCY_KEY,
            DEFAULT_HEADMAN_BASE_BONUS_CURRENCY,
            '大团长基础奖励发放币种 (USDT/GDT)',
        )
