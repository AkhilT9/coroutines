import json
from unittest.mock import patch

from django.core.mail import EmailMessage
from django.test import SimpleTestCase, override_settings

from .brevo import BrevoEmailBackend


class FakeResponse:
    status = 201

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class BrevoBackendTests(SimpleTestCase):
    @override_settings(BREVO_API_KEY="test-key", DEFAULT_FROM_EMAIL="coroutines <hi@example.com>")
    def test_posts_expected_payload(self):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["req"] = req
            captured["body"] = json.loads(req.data)
            return FakeResponse()

        with patch("config.brevo.request.urlopen", fake_urlopen):
            sent = BrevoEmailBackend().send_messages(
                [EmailMessage("Confirm", "Click the link", None, ["to@example.com"])]
            )

        self.assertEqual(sent, 1)
        self.assertEqual(captured["req"].get_header("Api-key"), "test-key")
        self.assertEqual(captured["body"]["sender"], {"name": "coroutines", "email": "hi@example.com"})
        self.assertEqual(captured["body"]["to"], [{"email": "to@example.com"}])
        self.assertEqual(captured["body"]["subject"], "Confirm")
        self.assertEqual(captured["body"]["textContent"], "Click the link")
