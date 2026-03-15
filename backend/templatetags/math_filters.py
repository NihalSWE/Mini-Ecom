# backend/templatetags/math_filters.py
from django import template

register = template.Library()

@register.filter
def sub(value, arg):
    """Subtract the arg from the value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def floatformat(value, decimal_places=2):
    """Format float to specified decimal places."""
    try:
        return format(float(value), f'.{decimal_places}f')
    except (ValueError, TypeError):
        return format(0, f'.{decimal_places}f')