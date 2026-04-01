from __future__ import annotations

import math

from django.template import Library

register = Library()


@register.filter
def sub(value: int, arg: int) -> int:
    return value - arg


@register.filter
def pct(value: float) -> str:
    return f"{value:.1f}%"


@register.filter
def pct_class(value: float) -> str:
    if value < 0.05:
        return "pct-0"
    return f"pct-{min(20, math.ceil(value / 5))}"
