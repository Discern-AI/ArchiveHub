from django.urls import path

from .consumers import InterviewConsumer

websocket_urlpatterns = [
    path("ws/interviews/<uuid:session_id>", InterviewConsumer.as_asgi()),
]
