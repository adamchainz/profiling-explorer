from __future__ import annotations

from django.template import Library

register = Library()


@register.filter
def sub(value: int, arg: int) -> int:
    return value - arg
