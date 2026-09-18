import json
import logging
from email.utils import parseaddr
from urllib import error, request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

API_URL = "https://api.brevo.com/v3/smtp/email"


class BrevoEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        return sum(1 for message in email_messages if self._send(message))

    def _send(self, message):
        name, address = parseaddr(message.from_email)
        payload = {
            "sender": {"name": name or address, "email": address},
            "to": [{"email": recipient} for recipient in message.to],
            "subject": message.subject,
            "textContent": message.body,
        }
        for content, mimetype in getattr(message, "alternatives", []):
            if mimetype == "text/html":
                payload["htmlContent"] = content
        req = request.Request(
            API_URL,
            data=json.dumps(payload).encode(),
            headers={
                "api-key": settings.BREVO_API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=10) as response:
                return 200 <= response.status < 300
        except error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            if not self.fail_silently:
                raise RuntimeError(f"Brevo API error {exc.code}: {detail}") from exc
            logger.error("Brevo API error %s: %s", exc.code, detail)
        except OSError as exc:
            if not self.fail_silently:
                raise
            logger.error("Brevo request failed: %s", exc)
        return False
