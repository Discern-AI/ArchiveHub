import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "archivehub.settings")
django_asgi = get_asgi_application()  # set up Django before importing consumers

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

from interviews.routing import websocket_urlpatterns  # noqa: E402

# HTTP goes to Django as before. WebSockets (live interviews, WP5) use the session cookie
# for login and only accept connections from our own origins.
application = ProtocolTypeRouter(
    {
        "http": django_asgi,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
