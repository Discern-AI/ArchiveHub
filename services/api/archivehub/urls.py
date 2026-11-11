from django.contrib import admin
from django.urls import include, path

from assistant.views import stream_chat_reply
from publishing import views as public

from .api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("_allauth/", include("allauth.headless.urls")),
    # Streaming lives outside Ninja: it's an async server-sent-events view.
    path("api/v1/chats/<uuid:chat_id>/stream", stream_chat_reply, name="chat-stream"),
    path("api/v1/", api.urls),
    # Public homepages, rendered on the server.
    path("h/<slug:slug>/", public.homepage, name="homepage"),
    path("h/<slug:slug>/images/<uuid:file_id>", public.image, name="homepage-image"),
    path("h/<slug:slug>/<slug:post_slug>/", public.post, name="homepage-post"),
    path("h/<slug:slug>/<path:path>", public.old_address, name="homepage-old-address"),
]
