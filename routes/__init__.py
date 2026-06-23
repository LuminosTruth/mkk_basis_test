from importlib import import_module

from routes.base_route import internal_router, private_router, public_router

import_module("routes.handler.payment")
import_module("routes.health")
import_module("routes.payment")

__all__ = [internal_router, private_router, public_router]
