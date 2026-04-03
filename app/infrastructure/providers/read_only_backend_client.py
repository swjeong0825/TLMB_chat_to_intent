import logging

import httpx

from app.infrastructure.config.settings import Settings
from app.ports.read_only_backend_gateway import GatewayResponse

logger = logging.getLogger(__name__)


class ReadOnlyBackendClient:
    """
    Implements ReadOnlyBackendGateway using httpx.

    Exposes only .get() — no other HTTP methods are implemented.
    Never raises exceptions for non-2xx responses; wraps them in GatewayResponse.

    A short-lived AsyncClient is created per call so this class is safe to use
    across different asyncio event loops (important for tests).
    """

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.backend_base_url
        self._timeout = 30.0

    async def get(
        self,
        path: str,
        auth_token: str | None = None,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> GatewayResponse:
        request_headers: dict[str, str] = {}
        if auth_token:
            request_headers["Authorization"] = f"Bearer {auth_token}"
        if headers:
            request_headers.update(headers)

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=self._timeout
            ) as client:
                response = await client.get(path, params=params, headers=request_headers)
            try:
                body = response.json()
            except Exception:
                body = {"raw": response.text}
            return GatewayResponse(
                status_code=response.status_code,
                body=body,
                is_success=200 <= response.status_code < 300,
            )
        except httpx.TimeoutException as e:
            logger.warning("Backend GET %s timed out: %s", path, e)
            return GatewayResponse(status_code=504, body={}, is_success=False)
        except Exception as e:
            logger.error("Backend GET %s failed: %s", path, e)
            return GatewayResponse(status_code=503, body={}, is_success=False)
