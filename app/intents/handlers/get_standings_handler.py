from app.api.schemas.chat_response_schema import ChatResponse
from app.application.parameter_resolution.resolved_params import ResolvedParams
from app.intents.base_intent_handler import BaseIntentHandler
from app.ports.read_only_backend_gateway import ReadOnlyBackendGateway


class GetStandingsHandler(BaseIntentHandler):
    """
    Read intent handler for GET_STANDINGS.
    Fetches standings from GET /leagues/{league_id}/standings and reshapes the response.
    """

    def __init__(self, gateway: ReadOnlyBackendGateway) -> None:
        self._gateway = gateway

    async def handle(self, params: ResolvedParams, host_token: str | None) -> ChatResponse:
        league_id = params.get_str("league_id")
        response = await self._gateway.get(f"/leagues/{league_id}/standings", auth_token=host_token)

        if not response.is_success:
            return ChatResponse.error(
                502,
                f"Could not fetch standings: backend returned status {response.status_code}",
            )

        standings = response.body.get("standings", [])
        return ChatResponse(
            data_type="GET_STANDINGS",
            data={"league_id": league_id, "standings": standings},
            server_message="",
        )
