from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
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
