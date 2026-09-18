from django.contrib import admin

from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user_a", "user_b", "updated_at", "unread_a", "unread_b")
    raw_id_fields = ("user_a", "user_b")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender", "content", "created_at")
    raw_id_fields = ("conversation", "sender")
