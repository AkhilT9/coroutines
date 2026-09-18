from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse


class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    content = models.CharField(max_length=280, blank=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    repost_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="reposts")
    created_at = models.DateTimeField(auto_now_add=True)
    like_count = models.PositiveIntegerField(default=0)
    reply_count = models.PositiveIntegerField(default=0)
    repost_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["author", "-id"]),
            models.Index(fields=["parent", "id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["author", "repost_of"],
                condition=Q(repost_of__isnull=False),
                name="unique_repost",
            ),
        ]

    def __str__(self):
        return f"{self.author}: {self.content[:40]}"

    def get_absolute_url(self):
        return reverse("post_detail", args=[self.pk])


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="likes")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "post"], name="unique_like")]
