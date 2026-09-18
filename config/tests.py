import json
from unittest.mock import patch

from django.core.mail import EmailMessage
from django.test import SimpleTestCase, override_settings

from .brevo import BrevoEmailBackend
from .gscript import AppsScriptEmailBackend


class FakeResponse:
    status = 201

    def __init__(self, body=b""):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class AppsScriptBackendTests(SimpleTestCase):
    @override_settings(
        APPS_SCRIPT_URL="https://script.google.com/macros/s/abc/exec",
        APPS_SCRIPT_SECRET="s3cret",
        DEFAULT_FROM_EMAIL="coroutines <hi@example.com>",
    )
    def test_posts_payload_and_reads_ok(self):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["body"] = json.loads(req.data)
            return FakeResponse(b'{"ok": true}')

        with patch("config.gscript.request.urlopen", fake_urlopen):
            sent = AppsScriptEmailBackend().send_messages(
                [EmailMessage("Confirm", "Click the link", None, ["to@example.com"])]
            )

        self.assertEqual(sent, 1)
        self.assertEqual(captured["url"], "https://script.google.com/macros/s/abc/exec")
        self.assertEqual(captured["body"]["secret"], "s3cret")
        self.assertEqual(captured["body"]["to"], "to@example.com")
        self.assertEqual(captured["body"]["from_name"], "coroutines")

    @override_settings(APPS_SCRIPT_URL="https://script.google.com/macros/s/abc/exec", APPS_SCRIPT_SECRET="x")
    def test_script_error_raises(self):
        with patch("config.gscript.request.urlopen", lambda req, timeout=None: FakeResponse(b'{"ok": false, "error": "unauthorized"}')):
            with self.assertRaises(RuntimeError):
                AppsScriptEmailBackend().send_messages([EmailMessage("S", "B", "a@b.com", ["to@example.com"])])


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
