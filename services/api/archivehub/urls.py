from django.contrib import admin
from django.urls import include, path

from assistant.views import stream_chat_reply

from .api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("_allauth/", include("allauth.headless.urls")),
    # Streaming lives outside Ninja: it's an async server-sent-events view.
    path("api/v1/chats/<uuid:chat_id>/stream", stream_chat_reply, name="chat-stream"),
    path("api/v1/", api.urls),
]
