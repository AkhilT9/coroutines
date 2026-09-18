from django.contrib import admin

from .models import Like, Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "content", "parent", "repost_of", "like_count", "created_at")
    list_select_related = ("author",)
    raw_id_fields = ("author", "parent", "repost_of")
    search_fields = ("content", "author__username")


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "created_at")
    raw_id_fields = ("user", "post")
