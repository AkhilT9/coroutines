from django.core import signing

SALT = "accounts.verify-email"
MAX_AGE = 60 * 60 * 24 * 3


def make_token(user):
    return signing.dumps({"uid": user.pk, "email": user.email}, salt=SALT)


def read_token(token):
    try:
        return signing.loads(token, salt=SALT, max_age=MAX_AGE)
    except signing.BadSignature:
        return None
