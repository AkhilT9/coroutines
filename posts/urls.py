from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("explore/", views.explore, name="explore"),
    path("compose/", views.compose, name="compose"),
    path("feed/updates/", views.feed_updates, name="feed_updates"),
    path("search/", views.search, name="search"),
    path("tag/<str:name>/", views.tag, name="tag"),
    path("bookmarks/", views.bookmarks, name="bookmarks"),
    path("p/<int:pk>/bookmark/", views.bookmark_toggle, name="bookmark_toggle"),
    path("p/<int:pk>/", views.post_detail, name="post_detail"),
    path("p/<int:pk>/reply/", views.reply, name="reply"),
    path("p/<int:pk>/like/", views.like_toggle, name="like_toggle"),
    path("p/<int:pk>/repost/", views.repost_toggle, name="repost_toggle"),
    path("p/<int:pk>/delete/", views.delete_post, name="delete_post"),
    path("p/<int:pk>/edit/", views.edit_post, name="edit_post"),
]
