from decimal import Decimal, InvalidOperation

from commissions.constants import (
    COMMISSION_TIERS_KEY,
    DEFAULT_COMMISSION_TIERS,
    DEFAULT_HEADMAN_BASE_BONUS_CURRENCY,
    DEFAULT_HEADMAN_BASE_BONUS_RATE,
    HEADMAN_BASE_BONUS_CURRENCY_KEY,
    HEADMAN_BASE_BONUS_RATE_KEY,
)
from commissions.models import SystemConfig


def get_commission_settings() -> dict:
    tiers = SystemConfig.get_commission_tiers() or DEFAULT_COMMISSION_TIERS
    base_bonus_rate = SystemConfig.get_decimal(
        HEADMAN_BASE_BONUS_RATE_KEY,
        DEFAULT_HEADMAN_BASE_BONUS_RATE,
    )
    base_bonus_currency = SystemConfig.get_value(
        HEADMAN_BASE_BONUS_CURRENCY_KEY,
        DEFAULT_HEADMAN_BASE_BONUS_CURRENCY,
    )
    display_tiers = [
        {
            'min': tier['min'],
            'max': tier['max'],
            'rate_percent': Decimal(str(tier['rate'])) * 100,
        }
        for tier in tiers
    ]
    return {
        'tiers': display_tiers,
        'base_bonus_rate_percent': base_bonus_rate * 100,
        'base_bonus_currency': base_bonus_currency,
    }


def parse_commission_form(post_data) -> tuple[list, Decimal, str]:
    mins = post_data.getlist('tier_min')
    maxs = post_data.getlist('tier_max')
    rates = post_data.getlist('tier_rate')

    tiers = []
    for idx, (min_raw, max_raw, rate_raw) in enumerate(zip(mins, maxs, rates), start=1):
        min_s = min_raw.strip()
        max_s = max_raw.strip()
        rate_s = rate_raw.strip()
        if not min_s and not max_s and not rate_s:
            continue
        if not all([min_s, max_s, rate_s]):
            raise ValueError(f'梯度 {idx} 的业绩区间与比例均须填写完整。')
        try:
            min_val = Decimal(min_s)
            max_val = Decimal(max_s)
            rate_pct = Decimal(rate_s)
        except InvalidOperation as exc:
            raise ValueError(f'梯度 {idx} 包含无效数字。') from exc
        if min_val < 0 or max_val < 0:
            raise ValueError(f'梯度 {idx} 的业绩区间不能为负数。')
        if min_val >= max_val:
            raise ValueError(f'梯度 {idx} 的下限须小于上限。')
        if rate_pct < 0 or rate_pct > 100:
            raise ValueError(f'梯度 {idx} 的提成比例须在 0–100 之间。')
        tiers.append({
            'min': float(min_val),
            'max': float(max_val),
            'rate': float(rate_pct / 100),
        })

    if not tiers:
        raise ValueError('至少保留一个提成梯度。')

    tiers.sort(key=lambda item: item['min'])

    try:
        base_bonus_rate_pct = Decimal(post_data.get('base_bonus_rate', '').strip())
    except InvalidOperation as exc:
        raise ValueError('大团长奖励比例格式无效。') from exc
    if base_bonus_rate_pct < 0 or base_bonus_rate_pct > 100:
        raise ValueError('大团长奖励比例须在 0–100 之间。')

    base_bonus_currency = post_data.get('base_bonus_currency', 'USDT').strip().upper()
    if base_bonus_currency not in ('USDT', 'GDT'):
        raise ValueError('大团长奖励币种仅支持 USDT 或 GDT。')

    return tiers, base_bonus_rate_pct / 100, base_bonus_currency


def save_commission_settings(tiers: list, base_bonus_rate: Decimal, base_bonus_currency: str) -> None:
    import json

    SystemConfig.set_value(
        COMMISSION_TIERS_KEY,
        json.dumps(tiers),
        '团长阶梯提成比例 JSON 配置',
    )
    SystemConfig.set_value(
        HEADMAN_BASE_BONUS_RATE_KEY,
        str(base_bonus_rate),
        '大团长基础奖励比例',
    )
    SystemConfig.set_value(
        HEADMAN_BASE_BONUS_CURRENCY_KEY,
        base_bonus_currency,
        '大团长基础奖励发放币种 (USDT/GDT)',
    )
