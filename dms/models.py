from django.conf import settings
from django.db import models


class Conversation(models.Model):
    user_a = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_a")
    user_b = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_b")
    updated_at = models.DateTimeField(auto_now_add=True)
    unread_a = models.PositiveIntegerField(default=0)
    unread_b = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [models.UniqueConstraint(fields=["user_a", "user_b"], name="unique_conversation")]

    @classmethod
    def between(cls, first, second):
        a, b = sorted((first, second), key=lambda u: u.pk)
        conversation, _ = cls.objects.get_or_create(user_a=a, user_b=b)
        return conversation

    def other(self, user):
        return self.user_b if self.user_a_id == user.pk else self.user_a

    def unread_field(self, user):
        return "unread_a" if self.user_a_id == user.pk else "unread_b"

    def unread_for(self, user):
        return getattr(self, self.unread_field(user))


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    content = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
