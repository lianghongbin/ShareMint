from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from authentication.models import Role, User
from commissions.models import SystemConfig
from commissions.services import aggregate_team_stats
from management.models import Investment


def _month_label(dt) -> str:
    return dt.strftime('%Y-%m')


def _last_month_keys(count: int = 6) -> list[str]:
    now = timezone.localtime()
    year, month = now.year, now.month
    keys = []
    for _ in range(count):
        keys.append(f'{year:04d}-{month:02d}')
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(keys))


def _user_display_name(user: User) -> str:
    profile = getattr(user, 'profile', None)
    if profile and profile.name:
        return profile.name
    return user.username


def _build_investment_trend(investments) -> dict:
    since = timezone.now() - timedelta(days=180)
    monthly_rows = (
        investments.filter(investment_date__gte=since)
        .annotate(month=TruncMonth('investment_date'))
        .values('month')
        .annotate(total=Sum('investment_amount'))
        .order_by('month')
    )
    monthly_map = {
        _month_label(row['month']): float(row['total'] or 0)
        for row in monthly_rows
    }
    trend_labels = _last_month_keys()
    return {
        'labels': trend_labels,
        'values': [monthly_map.get(label, 0.0) for label in trend_labels],
    }


def get_admin_dashboard_context() -> dict:
    gdt_price = SystemConfig.get_gdt_price()
    headman_count = User.objects.filter(role=Role.HEADMAN).count()
    member_count = User.objects.filter(role=Role.MEMBER).count()

    investment_totals = Investment.objects.aggregate(
        total_investment=Sum('investment_amount'),
        total_tokens=Sum('holding_quantity'),
    )
    total_investment = investment_totals['total_investment'] or Decimal('0')
    total_tokens = investment_totals['total_tokens'] or Decimal('0')
    total_market_value = total_tokens * gdt_price

    top_headmen = (
        User.objects.filter(role=Role.HEADMAN)
        .select_related('profile')
        .annotate(team_investment=Sum('referred_members__investments__investment_amount'))
        .order_by('-team_investment', 'id')[:5]
    )
    ranking = {
        'labels': [_user_display_name(headman) for headman in top_headmen],
        'values': [float(headman.team_investment or 0) for headman in top_headmen],
    }

    return {
        'gdt_price': gdt_price,
        'headman_count': headman_count,
        'member_count': member_count,
        'total_investment': total_investment,
        'total_market_value': total_market_value,
        'charts': {
            'investment_trend': _build_investment_trend(Investment.objects.all()),
            'ranking': ranking,
        },
    }


def get_headman_dashboard_context(headman: User) -> dict:
    stats = aggregate_team_stats(headman)
    member_ids = headman.referred_members.filter(
        role=Role.MEMBER,
        is_active=True,
    ).values_list('id', flat=True)
    team_investments = Investment.objects.filter(user_id__in=member_ids)

    top_members = (
        headman.referred_members.filter(role=Role.MEMBER, is_active=True)
        .select_related('profile')
        .annotate(member_investment=Sum('investments__investment_amount'))
        .order_by('-member_investment', 'id')[:5]
    )
    ranking = {
        'labels': [_user_display_name(member) for member in top_members],
        'values': [float(member.member_investment or 0) for member in top_members],
    }

    return {
        'gdt_price': stats['gdt_price'],
        'member_count': stats['member_count'],
        'total_investment': stats['total_investment'],
        'total_market_value': stats['total_market_value'],
        'charts': {
            'investment_trend': _build_investment_trend(team_investments),
            'ranking': ranking,
        },
    }
