from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import F, OuterRef, Q, Subquery
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.models import User, blocked_user_ids
from posts.feed import is_htmx

from .models import Conversation, Message


def _other_user(request, username):
    other = get_object_or_404(User, username=username.lower())
    if other == request.user:
        raise Http404
    return other


def _mark_read(conversation, user):
    Conversation.objects.filter(pk=conversation.pk).update(**{conversation.unread_field(user): 0})


@login_required
def inbox(request):
    last_message = Message.objects.filter(conversation=OuterRef("pk")).order_by("-id")
    conversations = (
        Conversation.objects.filter(Q(user_a=request.user) | Q(user_b=request.user))
        .select_related("user_a", "user_b")
        .annotate(last_content=Subquery(last_message.values("content")[:1]))
    )
    rows = [
        {
            "other": conversation.other(request.user),
            "unread": conversation.unread_for(request.user),
            "preview": conversation.last_content,
            "updated_at": conversation.updated_at,
        }
        for conversation in conversations
    ]
    return render(request, "dms/inbox.html", {"rows": rows})


@login_required
def conversation(request, username):
    other = _other_user(request, username)
    blocked = other.pk in blocked_user_ids(request.user)
    thread, since = [], 0
    if not blocked:
        conv = Conversation.between(request.user, other)
        thread = list(conv.messages.select_related("sender").order_by("-id")[:100])[::-1]
        _mark_read(conv, request.user)
        since = thread[-1].id if thread else 0
    return render(
        request,
        "dms/conversation.html",
        {"other": other, "thread": thread, "since": since, "blocked": blocked},
    )


@login_required
@require_POST
def send_message(request, username):
    other = _other_user(request, username)
    if other.pk in blocked_user_ids(request.user):
        return HttpResponseForbidden("You can't message this account.")
    content = request.POST.get("content", "").strip()
    if not content or len(content) > 1000:
        return HttpResponseBadRequest("Message must be 1 to 1000 characters.")
    recent = Message.objects.filter(sender=request.user, created_at__gte=timezone.now() - timedelta(minutes=1))
    if recent.count() >= 30:
        return HttpResponse("You're sending too fast. Try again in a minute.", status=429)
    conv = Conversation.between(request.user, other)
    message = Message.objects.create(conversation=conv, sender=request.user, content=content)
    other_field = conv.unread_field(other)
    Conversation.objects.filter(pk=conv.pk).update(updated_at=timezone.now(), **{other_field: F(other_field) + 1})
    if is_htmx(request):
        return render(request, "dms/partials/sent.html", {"m": message, "other": other, "since": message.id})
    return redirect("conversation", username=other.username)


@login_required
@require_GET
def conversation_updates(request, username):
    other = _other_user(request, username)
    since_param = request.GET.get("since", "0")
    since = int(since_param) if since_param.isdigit() else 0
    conv = Conversation.between(request.user, other)
    new_messages = list(conv.messages.select_related("sender").filter(id__gt=since)[:100])
    if new_messages:
        _mark_read(conv, request.user)
        since = new_messages[-1].id
    return render(request, "dms/partials/updates.html", {"thread": new_messages, "other": other, "since": since})
