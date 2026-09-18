from django import template
from django.db.models import Sum

from dms.models import Conversation

register = template.Library()


@register.simple_tag(takes_context=True)
def unread_dm_count(context):
    user = context["user"]
    if not user.is_authenticated:
        return 0
    as_a = Conversation.objects.filter(user_a=user).aggregate(total=Sum("unread_a"))["total"] or 0
    as_b = Conversation.objects.filter(user_b=user).aggregate(total=Sum("unread_b"))["total"] or 0
    return as_a + as_b
