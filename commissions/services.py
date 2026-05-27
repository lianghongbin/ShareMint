from decimal import Decimal

from django.db.models import Sum

from authentication.models import Role, User
from commissions.constants import (
    DEFAULT_HEADMAN_BASE_BONUS_CURRENCY,
    DEFAULT_HEADMAN_BASE_BONUS_RATE,
    HEADMAN_BASE_BONUS_CURRENCY_KEY,
    HEADMAN_BASE_BONUS_RATE_KEY,
)
from commissions.models import SystemConfig
from management.models import Investment


def get_tier_rate(total_amount: Decimal) -> tuple[Decimal, dict | None]:
    """根据团队总业绩返回对应阶梯比例。"""
    amount = float(total_amount)
    for tier in SystemConfig.get_commission_tiers():
        if tier['min'] <= amount < tier['max']:
            return Decimal(str(tier['rate'])), tier
    return Decimal('0'), None


def aggregate_team_stats(headman: User) -> dict:
    """汇总团长线下团队数据。"""
    members = headman.referred_members.filter(role=Role.MEMBER, is_active=True)
    member_ids = members.values_list('id', flat=True)
    investments = Investment.objects.filter(user_id__in=member_ids)

    totals = investments.aggregate(
        total_investment=Sum('investment_amount'),
        total_tokens=Sum('holding_quantity'),
    )
    total_investment = totals['total_investment'] or Decimal('0')
    total_tokens = totals['total_tokens'] or Decimal('0')
    gdt_price = SystemConfig.get_gdt_price()
    total_market_value = total_tokens * gdt_price

    tier_rate, tier = get_tier_rate(total_investment)
    tier_commission = total_investment * tier_rate

    base_bonus_rate = SystemConfig.get_decimal(
        HEADMAN_BASE_BONUS_RATE_KEY,
        DEFAULT_HEADMAN_BASE_BONUS_RATE,
    )
    base_bonus = total_investment * base_bonus_rate
    bonus_currency = SystemConfig.get_value(
        HEADMAN_BASE_BONUS_CURRENCY_KEY,
        DEFAULT_HEADMAN_BASE_BONUS_CURRENCY,
    )

    return {
        'member_count': members.count(),
        'total_investment': total_investment,
        'total_tokens': total_tokens,
        'gdt_price': gdt_price,
        'total_market_value': total_market_value,
        'tier_rate': tier_rate,
        'tier': tier,
        'tier_commission': tier_commission,
        'base_bonus_rate': base_bonus_rate,
        'base_bonus': base_bonus,
        'base_bonus_currency': bonus_currency,
        'total_commission': tier_commission + base_bonus,
        'tier_rate_percent': tier_rate * 100,
    }


def calculate_headman_commission(headman: User) -> dict:
    if headman.role != Role.HEADMAN:
        raise ValueError('仅团长角色可计算提成。')
    return aggregate_team_stats(headman)
