from urllib.parse import urlparse

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.models import Follow

from .feed import attach_viewer_state, base_queryset, is_htmx, paginate_feed
from .forms import PostForm
from .models import Like, Post


def _original(post):
    return post.repost_of if post.repost_of_id else post


def _home_queryset(user):
    following_ids = Follow.objects.filter(follower=user).values_list("following_id", flat=True)
    return (
        base_queryset()
        .filter(parent__isnull=True)
        .filter(Q(author_id__in=following_ids) | Q(author=user))
    )


def _latest_id(items):
    return max((item.id for item in items), default=0)


def home(request):
    if not request.user.is_authenticated:
        return redirect("explore")
    page = paginate_feed(request, _home_queryset(request.user))
    if is_htmx(request):
        return render(request, "partials/feed_page.html", page)
    return render(request, "posts/home.html", {**page, "since": _latest_id(page["items"])})


def explore(request):
    page = paginate_feed(request, base_queryset().filter(parent__isnull=True))
    if is_htmx(request):
        return render(request, "partials/feed_page.html", page)
    return render(request, "posts/explore.html", {**page, "since": _latest_id(page["items"])})


@require_GET
def feed_updates(request):
    scope = request.GET.get("scope")
    since_param = request.GET.get("since", "0")
    since = int(since_param) if since_param.isdigit() else 0
    post_id = request.GET.get("post", "")
    if scope == "home":
        if not request.user.is_authenticated:
            raise Http404
        queryset = _home_queryset(request.user)
        swap, singular, plural = "afterbegin", "post", "posts"
    elif scope == "explore":
        queryset = base_queryset().filter(parent__isnull=True)
        swap, singular, plural = "afterbegin", "post", "posts"
    elif scope == "thread" and post_id.isdigit():
        queryset = base_queryset().filter(parent_id=int(post_id)).order_by("id")
        swap, singular, plural = "beforeend", "reply", "replies"
    else:
        raise Http404
    queryset = queryset.filter(id__gt=since)
    context = {"scope": scope, "post_id": post_id, "since": since, "swap": swap}
    if request.GET.get("show"):
        items = list(queryset[:50])
        attach_viewer_state(items, request.user)
        context["items"] = items
        context["since"] = _latest_id(items) or since
        return render(request, "partials/feed_new_items.html", context)
    count = queryset.count()
    context["count"] = count
    context["label"] = f"Show {count} new {singular if count == 1 else plural}"
    return render(request, "partials/feed_updates.html", context)


@login_required
@require_POST
def compose(request):
    if not request.user.email_verified:
        return HttpResponseForbidden("Confirm your email to post.")
    form = PostForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Post must be 1 to 280 characters.")
    post = form.save(commit=False)
    post.author = request.user
    post.save()
    if is_htmx(request):
        attach_viewer_state([post], request.user)
        return render(request, "partials/compose_result.html", {"item": post})
    return redirect("home")


def post_detail(request, pk):
    post = get_object_or_404(base_queryset(), pk=pk)
    if post.repost_of_id:
        return redirect(post.repost_of.get_absolute_url())
    ancestors = []
    parent_id = post.parent_id
    while parent_id and len(ancestors) < 25:
        ancestor = base_queryset().filter(pk=parent_id).first()
        if ancestor is None:
            break
        ancestors.append(ancestor)
        parent_id = ancestor.parent_id
    ancestors.reverse()
    replies = list(base_queryset().filter(parent=post).order_by("id"))
    attach_viewer_state([*ancestors, post, *replies], request.user)
    return render(
        request,
        "posts/detail.html",
        {"post": post, "ancestors": ancestors, "replies": replies, "since": _latest_id(replies)},
    )


@login_required
@require_POST
def reply(request, pk):
    if not request.user.email_verified:
        return HttpResponseForbidden("Confirm your email to reply.")
    parent = _original(get_object_or_404(Post, pk=pk))
    form = PostForm(request.POST)
    if form.is_valid():
        Post.objects.create(author=request.user, parent=parent, content=form.cleaned_data["content"])
        Post.objects.filter(pk=parent.pk).update(reply_count=F("reply_count") + 1)
    else:
        messages.error(request, "Reply must be 1 to 280 characters.")
    return redirect(parent.get_absolute_url())


@login_required
@require_POST
def like_toggle(request, pk):
    post = _original(get_object_or_404(Post, pk=pk))
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if created:
        delta = 1
    else:
        like.delete()
        delta = -1
    Post.objects.filter(pk=post.pk).update(like_count=F("like_count") + delta)
    post.refresh_from_db(fields=["like_count"])
    post.viewer_liked = created
    return render(request, "partials/like_button.html", {"post": post})


@login_required
@require_POST
def repost_toggle(request, pk):
    if not request.user.email_verified:
        return HttpResponseForbidden("Confirm your email to repost.")
    post = _original(get_object_or_404(Post, pk=pk))
    existing = Post.objects.filter(author=request.user, repost_of=post).first()
    if existing:
        existing.delete()
        delta, reposted = -1, False
    else:
        Post.objects.create(author=request.user, repost_of=post)
        delta, reposted = 1, True
    Post.objects.filter(pk=post.pk).update(repost_count=F("repost_count") + delta)
    post.refresh_from_db(fields=["repost_count"])
    post.viewer_reposted = reposted
    return render(request, "partials/repost_button.html", {"post": post})


@login_required
@require_http_methods(["POST", "DELETE"])
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    detail_url = post.get_absolute_url()
    if post.parent_id:
        Post.objects.filter(pk=post.parent_id).update(reply_count=F("reply_count") - 1)
    if post.repost_of_id:
        Post.objects.filter(pk=post.repost_of_id).update(repost_count=F("repost_count") - 1)
    post.delete()
    if is_htmx(request):
        response = HttpResponse("")
        if urlparse(request.headers.get("HX-Current-URL", "")).path == detail_url:
            response["HX-Redirect"] = reverse("home")
        return response
    return redirect("home")
