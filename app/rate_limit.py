"""HTTP rate limiting (slowapi). See .env.example for tunable env vars."""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address


def _env_bool(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).lower() not in ("0", "false", "no", "off")


CHAT_ROUTE_LIMIT = os.getenv("RATELIMIT_CHAT_ROUTE", "30/minute")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[os.getenv("RATELIMIT_DEFAULT", "60/minute")],
    enabled=_env_bool("RATELIMIT_ENABLED", "true"),
    headers_enabled=_env_bool("RATELIMIT_HEADERS", "false"),
)


def register_rate_limit_middleware(app) -> None:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
