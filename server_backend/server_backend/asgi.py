import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import game.routing

import logging
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server_backend.settings")
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("django")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            game.routing.websocket_urlpatterns
        )
    ),
})

logger.debug("ASGI application initialized")

# Example of printing out a specific setting
logger.debug(f"Setting DEBUG is set to: {settings.DEBUG}")
logger.debug(f"Setting SECRET_KEY is: {settings.SECRET_KEY}")