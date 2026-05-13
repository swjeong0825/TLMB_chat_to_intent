from app.api.schemas.chat_response_schema import ChatResponse
from app.application.parameter_resolution.resolved_params import ResolvedParams
from app.intents.base_intent_handler import BaseIntentHandler
from app.ports.read_only_backend_gateway import ReadOnlyBackendGateway


class GetAllowlistHandler(BaseIntentHandler):
    """
    Read intent handler for GET_ALLOWLIST.
    Fetches the host-curated allowlist from GET /leagues/{league_id}/allowlist.
    """

    def __init__(self, gateway: ReadOnlyBackendGateway) -> None:
        self._gateway = gateway

    async def handle(self, params: ResolvedParams, host_token: str | None) -> ChatResponse:
        league_id = params.get_str("league_id")
        response = await self._gateway.get(
            f"/leagues/{league_id}/allowlist", auth_token=host_token
        )

        if not response.is_success:
            return ChatResponse.error(
                502,
                f"Could not fetch allowlist: backend returned status {response.status_code}",
            )

        allowlist = response.body.get("allowlist", [])
        return ChatResponse(
            data_type="GET_ALLOWLIST",
            data={"league_id": league_id, "allowlist": allowlist},
            server_message="",
        )
