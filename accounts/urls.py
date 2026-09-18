from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import path, reverse_lazy

from . import views
from .forms import StyledPasswordResetForm, StyledSetPasswordForm

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path(
        "password/reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset.html",
            form_class=StyledPasswordResetForm,
            email_template_name="emails/password_reset.txt",
            subject_template_name="emails/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password/reset/sent/",
        auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "password/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            form_class=StyledSetPasswordForm,
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("settings/password/", views.PasswordChangeView.as_view(), name="password_change"),
    path("settings/email/", views.change_email, name="change_email"),
    path("verify/resend/", views.resend_verification, name="resend_verification"),
    path("verify/<str:token>/", views.verify_email, name="verify_email"),
    path("settings/", views.settings_home, name="settings"),
    path("settings/theme/", views.update_theme, name="update_theme"),
    path("settings/profile/", views.edit_profile, name="edit_profile"),
    path("settings/blocked/", views.blocked_list, name="blocked_list"),
    path("settings/delete/", views.delete_account, name="delete_account"),
    path("@<str:username>/block/", views.block_toggle, name="block_toggle"),
    path("@<str:username>/", views.profile, name="profile"),
    path("@<str:username>/followers/", views.followers, name="followers"),
    path("@<str:username>/following/", views.following, name="following"),
    path("@<str:username>/follow/", views.follow_toggle, name="follow_toggle"),
]
