from __future__ import annotations

from django.template import Library

register = Library()


@register.filter
def sub(value, arg):
    return value - arg
