from app.api.schemas.chat_response_schema import ChatResponse
from app.application.parameter_resolution.resolved_params import ResolvedParams
from app.intents.base_intent_handler import BaseIntentHandler
from app.ports.read_only_backend_gateway import ReadOnlyBackendGateway


class GetEligiblePlayersHandler(BaseIntentHandler):
    """
    Read intent handler for GET_ELIGIBLE_PLAYERS.
    Fetches the host-curated allowlist from GET /leagues/{league_id}/eligible-players.
    """

    def __init__(self, gateway: ReadOnlyBackendGateway) -> None:
        self._gateway = gateway

    async def handle(self, params: ResolvedParams, host_token: str | None) -> ChatResponse:
        league_id = params.get_str("league_id")
        response = await self._gateway.get(
            f"/leagues/{league_id}/eligible-players", auth_token=host_token
        )

        if not response.is_success:
            return ChatResponse.error(
                502,
                f"Could not fetch eligible players: backend returned status {response.status_code}",
            )

        eligible_players = response.body.get("eligible_players", [])
        return ChatResponse(
            data_type="GET_ELIGIBLE_PLAYERS",
            data={"league_id": league_id, "eligible_players": eligible_players},
            server_message="",
        )
