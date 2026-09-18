from accounts.models import blocked_user_ids

from .models import Bookmark, Like, Post

PAGE_SIZE = 20


def exclude_blocked(queryset, user):
    ids = blocked_user_ids(user)
    if not ids:
        return queryset
    return queryset.exclude(author_id__in=ids).exclude(repost_of__author_id__in=ids)


def is_htmx(request):
    return request.headers.get("HX-Request") == "true"


def base_queryset():
    return Post.objects.select_related(
        "author",
        "parent__author",
        "repost_of__author",
        "repost_of__parent__author",
    )


def attach_viewer_state(items, user):
    targets = [item.repost_of or item for item in items]
    liked = reposted = bookmarked = set()
    if user.is_authenticated and targets:
        ids = {t.id for t in targets}
        liked = set(Like.objects.filter(user=user, post_id__in=ids).values_list("post_id", flat=True))
        reposted = set(
            Post.objects.filter(author=user, repost_of_id__in=ids).values_list("repost_of_id", flat=True)
        )
        bookmarked = set(Bookmark.objects.filter(user=user, post_id__in=ids).values_list("post_id", flat=True))
    for target in targets:
        target.viewer_liked = target.id in liked
        target.viewer_reposted = target.id in reposted
        target.viewer_bookmarked = target.id in bookmarked


def paginate_feed(request, queryset):
    before = request.GET.get("before", "")
    if before.isdigit():
        queryset = queryset.filter(id__lt=int(before))
    items = list(queryset[: PAGE_SIZE + 1])
    has_more = len(items) > PAGE_SIZE
    items = items[:PAGE_SIZE]
    attach_viewer_state(items, request.user)
    next_url = None
    if has_more:
        params = request.GET.copy()
        params["before"] = items[-1].id
        next_url = f"{request.path}?{params.urlencode()}"
    return {"items": items, "next_url": next_url}
