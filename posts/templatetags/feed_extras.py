from django import template
from django.utils import timezone
from django.utils.formats import date_format

register = template.Library()


@register.filter
def short_since(value):
    now = timezone.now()
    seconds = int((now - value).total_seconds())
    if seconds < 60:
        return "now"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    if seconds < 86400 * 7:
        return f"{seconds // 86400}d"
    return date_format(value, "M j" if value.year == now.year else "M j, Y")
