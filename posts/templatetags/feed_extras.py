import re
from collections import Counter
from datetime import timedelta

from django import template
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from accounts.models import User
from posts.models import Post

register = template.Library()

MENTION_RE = re.compile(r"(?<![\w@])@([A-Za-z0-9_]{3,15})(?!\w)")
# The lookbehind excludes "&" so escaped entities like &#x27; are not read as hashtags.
HASHTAG_RE = re.compile(r"(?<![\w#&])#([A-Za-z0-9_]+)")


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


def _mention_link(match):
    handle = match.group(1)
    url = reverse("profile", args=[handle.lower()])
    return f'<a href="{url}" class="text-accent hover:underline">@{handle}</a>'


def _hashtag_link(match):
    name = match.group(1)
    url = reverse("tag", args=[name])
    return f'<a href="{url}" class="text-accent hover:underline">#{name}</a>'


@register.filter(needs_autoescape=True)
def linkify(value, autoescape=True):
    text = conditional_escape(value) if autoescape else value
    text = MENTION_RE.sub(_mention_link, text)
    text = HASHTAG_RE.sub(_hashtag_link, text)
    return mark_safe(text)


@register.inclusion_tag("partials/trending.html")
def trending_tags():
    since = timezone.now() - timedelta(hours=24)
    recent = Post.objects.filter(created_at__gte=since, content__contains="#").values_list("content", flat=True)[:500]
    counter = Counter()
    for content in recent:
        for tag in {t.lower() for t in HASHTAG_RE.findall(content)}:
            counter[tag] += 1
    return {"tags": counter.most_common(5)}


@register.inclusion_tag("partials/who_to_follow.html", takes_context=True)
def who_to_follow(context):
    user = context["user"]
    queryset = User.objects.filter(is_active=True)
    if user.is_authenticated:
        queryset = queryset.exclude(pk=user.pk).exclude(follower_set__follower=user)
    suggestions = queryset.annotate(num_followers=Count("follower_set")).order_by("-num_followers", "-date_joined")[:3]
    return {"suggestions": suggestions, "user": user, "request": context["request"]}
