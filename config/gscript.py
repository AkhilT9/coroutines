import json
import logging
from email.utils import parseaddr
from urllib import request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class AppsScriptEmailBackend(BaseEmailBackend):
    """Posts each message to a Google Apps Script web app, which sends it with Gmail."""

    def send_messages(self, email_messages):
        return sum(1 for message in email_messages if self._send(message))

    def _send(self, message):
        name, _ = parseaddr(message.from_email)
        payload = {
            "secret": settings.APPS_SCRIPT_SECRET,
            "to": ", ".join(message.to),
            "subject": message.subject,
            "text": message.body,
            "from_name": name or "coroutines",
        }
        req = request.Request(
            settings.APPS_SCRIPT_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=20) as response:
                result = json.loads(response.read().decode())
        except (OSError, ValueError) as exc:
            if not self.fail_silently:
                raise
            logger.error("Apps Script request failed: %s", exc)
            return False
        if not result.get("ok"):
            if not self.fail_silently:
                raise RuntimeError(f"Apps Script error: {result.get('error')}")
            logger.error("Apps Script error: %s", result.get("error"))
            return False
        return True
