from urllib.parse import urlparse

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from posts.feed import base_queryset, is_htmx, paginate_feed

from .emails import send_verification_email
from .forms import LoginForm, ProfileForm, SignupForm
from .models import Block, Follow, User, blocked_user_ids
from .tokens import read_token


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        if send_verification_email(request, user):
            messages.success(request, f"Welcome, @{user.username}! We sent a confirmation link to {user.email}.")
        else:
            messages.error(request, "We couldn't send the confirmation email. Try 'Resend' in a moment.")
        return redirect("home")
    return render(request, "accounts/signup.html", {"form": form})


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


def verify_email(request, token):
    data = read_token(token)
    user = User.objects.filter(pk=data["uid"], email=data["email"]).first() if data else None
    if user is None:
        messages.error(request, "That confirmation link is invalid or has expired.")
        return redirect("home")
    if not user.email_verified:
        user.email_verified = True
        user.save(update_fields=["email_verified"])
    messages.success(request, "Email confirmed. You can post now.")
    return redirect("home")


@login_required
@require_POST
def resend_verification(request):
    if not request.user.email_verified:
        if send_verification_email(request, request.user):
            messages.success(request, f"Confirmation link sent to {request.user.email}.")
        else:
            messages.error(request, "Email sending failed. Please try again later.")
    return redirect("home")


def profile(request, username):
    profile_user = get_object_or_404(User, username=username.lower())
    tab = "replies" if request.GET.get("tab") == "replies" else "posts"
    viewer_blocked = blocked_by = False
    if request.user.is_authenticated:
        viewer_blocked = Block.objects.filter(blocker=request.user, blocked=profile_user).exists()
        blocked_by = Block.objects.filter(blocker=profile_user, blocked=request.user).exists()
    if viewer_blocked or blocked_by:
        page = {"items": [], "next_url": None}
    else:
        queryset = base_queryset().filter(author=profile_user, parent__isnull=(tab == "posts"))
        page = paginate_feed(request, queryset)
    if is_htmx(request):
        return render(request, "partials/feed_page.html", page)
    is_following = request.user.is_authenticated and Follow.objects.filter(
        follower=request.user, following=profile_user
    ).exists()
    context = {
        **page,
        "profile_user": profile_user,
        "tab": tab,
        "post_count": profile_user.posts.filter(parent__isnull=True).count(),
        "followers_count": profile_user.follower_set.count(),
        "following_count": profile_user.following_set.count(),
        "is_following": is_following,
        "viewer_blocked": viewer_blocked,
        "blocked_by": blocked_by,
    }
    return render(request, "accounts/profile.html", context)


@login_required
@require_POST
def follow_toggle(request, username):
    target = get_object_or_404(User, username=username.lower())
    if target == request.user:
        return HttpResponseBadRequest("You can't follow yourself.")
    if target.pk in blocked_user_ids(request.user):
        return HttpResponseForbidden("You can't follow this account.")
    follow, created = Follow.objects.get_or_create(follower=request.user, following=target)
    if not created:
        follow.delete()
    context = {"profile_user": target, "is_following": created}
    current_path = urlparse(request.headers.get("HX-Current-URL", "")).path
    if current_path == target.get_absolute_url():
        context["oob_followers_count"] = target.follower_set.count()
    return render(request, "partials/follow_button.html", context)


def _user_list(request, username, relation):
    profile_user = get_object_or_404(User, username=username.lower())
    if relation == "followers":
        users = User.objects.filter(following_set__following=profile_user)
    else:
        users = User.objects.filter(follower_set__follower=profile_user)
    users = list(users.order_by("username")[:200])
    my_follows = set()
    if request.user.is_authenticated:
        my_follows = set(
            Follow.objects.filter(follower=request.user, following__in=users).values_list("following_id", flat=True)
        )
    for u in users:
        u.is_followed = u.id in my_follows
    return render(
        request,
        "accounts/user_list.html",
        {"profile_user": profile_user, "users": users, "tab": relation},
    )


def followers(request, username):
    return _user_list(request, username, "followers")


def following(request, username):
    return _user_list(request, username, "following")


@login_required
@require_POST
def block_toggle(request, username):
    target = get_object_or_404(User, username=username.lower())
    if target == request.user:
        return HttpResponseBadRequest("You can't block yourself.")
    block, created = Block.objects.get_or_create(blocker=request.user, blocked=target)
    if created:
        Follow.objects.filter(
            Q(follower=request.user, following=target) | Q(follower=target, following=request.user)
        ).delete()
        messages.success(request, f"Blocked @{target.username}.")
    else:
        block.delete()
        messages.success(request, f"Unblocked @{target.username}.")
    if request.POST.get("next") == "blocked":
        return redirect("blocked_list")
    return redirect(target.get_absolute_url())


@login_required
def blocked_list(request):
    blocks = Block.objects.filter(blocker=request.user).select_related("blocked").order_by("-id")
    return render(request, "accounts/blocked_list.html", {"blocks": blocks})


@login_required
def delete_account(request):
    if request.method == "POST":
        if request.user.check_password(request.POST.get("password", "")):
            user = request.user
            logout(request)
            user.delete()
            messages.success(request, "Your account has been deleted.")
            return redirect("explore")
        messages.error(request, "That password is incorrect.")
    return render(request, "accounts/delete_account.html")


@login_required
def settings_home(request):
    rows = [
        (reverse("edit_profile"), "Edit profile", "Name, bio"),
        (reverse("bookmarks"), "Bookmarks", "Posts you saved"),
        (reverse("blocked_list"), "Blocked accounts", "People you've blocked"),
        (reverse("terms"), "Terms of Service", "The rules for using coroutines"),
        (reverse("privacy"), "Privacy Policy", "What we collect and why"),
    ]
    return render(request, "accounts/settings.html", {"theme_choices": User.Theme.choices, "rows": rows})


@login_required
@require_POST
def update_theme(request):
    value = request.POST.get("theme")
    if value not in User.Theme.values:
        return HttpResponseBadRequest("Invalid theme.")
    request.user.theme = value
    request.user.save(update_fields=["theme"])
    messages.success(request, "Appearance updated.")
    response = redirect("settings")
    response.set_cookie("theme", value, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return response


@login_required
def edit_profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("profile", username=request.user.username)
    return render(request, "accounts/edit_profile.html", {"form": form})
