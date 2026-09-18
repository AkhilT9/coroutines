import logging

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

from .tokens import make_token

logger = logging.getLogger(__name__)


def send_verification_email(request, user):
    url = request.build_absolute_uri(reverse("verify_email", args=[make_token(user)]))
    body = render_to_string("emails/verify_email.txt", {"user": user, "url": url})
    try:
        send_mail("Confirm your email for coroutines", body, None, [user.email])
    except Exception:
        logger.exception("Could not send verification email to %s", user.email)
        return False
    return True
