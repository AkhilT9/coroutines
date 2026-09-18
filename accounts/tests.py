from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .models import Follow, User
from .tokens import make_token

PASSWORD = "strong-pass-123"


class SignupTests(TestCase):
    def test_signup_creates_user_logs_in_and_emails(self):
        response = self.client.post(
            reverse("signup"),
            {"username": "Alice_1", "email": "Alice@Example.com", "password1": PASSWORD, "password2": PASSWORD},
        )
        self.assertRedirects(response, reverse("home"))
        user = User.objects.get()
        self.assertEqual(user.username, "alice_1")
        self.assertEqual(user.email, "alice@example.com")
        self.assertFalse(user.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/verify/", mail.outbox[0].body)

    def test_rejects_invalid_handles(self):
        response = self.client.post(
            reverse("signup"),
            {"username": "no spaces", "email": "a@example.com", "password1": PASSWORD, "password2": PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)

    def test_verify_link_marks_email_verified(self):
        user = User.objects.create_user("bob", "bob@example.com", PASSWORD)
        response = self.client.get(reverse("verify_email", args=[make_token(user)]))
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_bad_token_is_rejected(self):
        response = self.client.get(reverse("verify_email", args=["not-a-real-token"]))
        self.assertEqual(response.status_code, 302)


class ThemeSettingsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", "alice@example.com", PASSWORD)
        self.client.force_login(self.user)

    def test_settings_page_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("settings")).status_code, 302)

    def test_default_theme_is_system_and_shown(self):
        self.assertEqual(self.user.theme, "system")
        self.assertContains(self.client.get(reverse("settings")), "System")

    def test_update_theme_persists_and_sets_cookie(self):
        response = self.client.post(reverse("update_theme"), {"theme": "dark"})
        self.assertRedirects(response, reverse("settings"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.theme, "dark")
        self.assertEqual(response.cookies["theme"].value, "dark")

    def test_update_theme_rejects_invalid_value(self):
        response = self.client.post(reverse("update_theme"), {"theme": "rainbow"})
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.theme, "system")

    def test_html_tag_carries_data_theme_when_set(self):
        self.user.theme = "dark"
        self.user.save()
        self.assertContains(self.client.get(reverse("home")), 'data-theme="dark"')

    def test_html_tag_has_no_data_theme_for_system(self):
        self.assertNotContains(self.client.get(reverse("home")), "data-theme")


class FollowTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", "alice@example.com", PASSWORD)
        self.bob = User.objects.create_user("bob", "bob@example.com", PASSWORD)
        self.client.force_login(self.alice)

    def test_follow_toggle(self):
        url = reverse("follow_toggle", args=["bob"])
        self.client.post(url)
        self.assertTrue(Follow.objects.filter(follower=self.alice, following=self.bob).exists())
        self.client.post(url)
        self.assertFalse(Follow.objects.exists())

    def test_cannot_follow_self(self):
        response = self.client.post(reverse("follow_toggle", args=["alice"]))
        self.assertEqual(response.status_code, 400)

    def test_profile_pages_render(self):
        for name in ("profile", "followers", "following"):
            self.assertEqual(self.client.get(reverse(name, args=["bob"])).status_code, 200)
