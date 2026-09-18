from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import F, Q
from django.urls import reverse

handle_validator = RegexValidator(
    r"^[A-Za-z0-9_]{3,15}$",
    "Use 3 to 15 letters, numbers, or underscores.",
)


class User(AbstractUser):
    username = models.CharField(max_length=15, unique=True, validators=[handle_validator])
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=50, blank=True)
    bio = models.CharField(max_length=160, blank=True)
    email_verified = models.BooleanField(default=False)

    class Theme(models.TextChoices):
        SYSTEM = "system", "System"
        LIGHT = "light", "Light"
        DARK = "dark", "Dark"

    theme = models.CharField(max_length=6, choices=Theme.choices, default=Theme.SYSTEM)

    REQUIRED_FIELDS = ["email"]

    @property
    def name(self):
        return self.display_name or self.username

    @property
    def initial(self):
        return self.username[:1].upper()

    @property
    def avatar_hue(self):
        # hash() is salted per process, so derive the colour deterministically
        return sum(ord(c) for c in self.username) * 37 % 360

    def get_absolute_url(self):
        return reverse("profile", args=[self.username])


class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following_set")
    following = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="follower_set")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["follower", "following"], name="unique_follow"),
            models.CheckConstraint(condition=~Q(follower=F("following")), name="no_self_follow"),
        ]

    def __str__(self):
        return f"{self.follower} -> {self.following}"
