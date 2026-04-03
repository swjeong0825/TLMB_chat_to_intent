from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class GatewayResponse:
    status_code: int
    body: dict
    is_success: bool


@runtime_checkable
class ReadOnlyBackendGateway(Protocol):
    async def get(
        self,
        path: str,
        auth_token: str | None = None,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> GatewayResponse: ...
