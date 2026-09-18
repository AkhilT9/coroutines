from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

from accounts.models import Block, User

from .models import Conversation, Message

PASSWORD = "strong-pass-123"


class DmTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", "alice@example.com", PASSWORD)
        self.bob = User.objects.create_user("bob", "bob@example.com", PASSWORD)
        self.client.force_login(self.alice)

    def test_send_creates_message_and_unread_for_recipient(self):
        response = self.client.post(reverse("dm_send", args=["bob"]), {"content": "hello bob"})
        self.assertRedirects(response, reverse("conversation", args=["bob"]))
        conv = Conversation.objects.get()
        self.assertEqual(conv.unread_for(self.bob), 1)
        self.assertEqual(conv.unread_for(self.alice), 0)

        self.client.force_login(self.bob)
        self.assertContains(self.client.get(reverse("inbox")), "hello bob")
        self.assertContains(self.client.get(reverse("conversation", args=["alice"])), "hello bob")
        conv.refresh_from_db()
        self.assertEqual(conv.unread_for(self.bob), 0)

    def test_updates_returns_only_messages_since(self):
        self.client.post(reverse("dm_send", args=["bob"]), {"content": "first"})
        first = Message.objects.get()
        self.client.force_login(self.bob)
        self.client.post(reverse("dm_send", args=["alice"]), {"content": "second"})
        self.client.force_login(self.alice)
        response = self.client.get(reverse("dm_updates", args=["bob"]), {"since": first.pk})
        self.assertContains(response, "second")
        self.assertNotContains(response, "first")

    def test_blocked_users_cannot_message(self):
        Block.objects.create(blocker=self.bob, blocked=self.alice)
        self.assertEqual(self.client.post(reverse("dm_send", args=["bob"]), {"content": "hi"}).status_code, 403)
        self.assertContains(self.client.get(reverse("conversation", args=["bob"])), "message this account")

    def test_bubbles_align_by_sender(self):
        conv = Conversation.between(self.alice, self.bob)
        mine = Message.objects.create(conversation=conv, sender=self.alice, content="from alice")
        theirs = Message.objects.create(conversation=conv, sender=self.bob, content="from bob")
        mine_html = render_to_string("dms/partials/bubble.html", {"m": mine, "user": self.alice})
        theirs_html = render_to_string("dms/partials/bubble.html", {"m": theirs, "user": self.alice})
        self.assertIn("justify-end", mine_html)
        self.assertIn("You ·", mine_html)
        self.assertIn("justify-start", theirs_html)
        self.assertNotIn("justify-end", theirs_html)

    def test_cannot_message_self(self):
        self.assertEqual(self.client.get(reverse("conversation", args=["alice"])).status_code, 404)

    def test_inbox_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("inbox")).status_code, 302)
