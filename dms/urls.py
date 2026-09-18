from django.urls import path

from . import views

urlpatterns = [
    path("messages/", views.inbox, name="inbox"),
    path("messages/@<str:username>/", views.conversation, name="conversation"),
    path("messages/@<str:username>/send/", views.send_message, name="dm_send"),
    path("messages/@<str:username>/updates/", views.conversation_updates, name="dm_updates"),
]
