from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def format_gdt(value):
    """GDT 数量仅展示整数（个位）。"""
    if value in (None, ''):
        return '0'
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return '0'
    return str(int(amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)))
