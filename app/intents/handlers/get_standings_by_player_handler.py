from app.api.schemas.chat_response_schema import ChatResponse
from app.application.parameter_resolution.resolved_params import ResolvedParams
from app.intents.base_intent_handler import BaseIntentHandler
from app.ports.read_only_backend_gateway import ReadOnlyBackendGateway


class GetStandingsByPlayerHandler(BaseIntentHandler):
    """
    Read intent handler for GET_STANDINGS_BY_PLAYER.
    Fetches the league standings row for the team that contains the named player via
    GET /leagues/{league_id}/standings/by-player?player_name={player_name}.
    """

    def __init__(self, gateway: ReadOnlyBackendGateway) -> None:
        self._gateway = gateway

    async def handle(self, params: ResolvedParams, host_token: str | None) -> ChatResponse:
        league_id = params.get_str("league_id")
        player_name = params.get_str("player_name")

        response = await self._gateway.get(
            f"/leagues/{league_id}/standings/by-player",
            auth_token=host_token,
            params={"player_name": player_name},
        )

        if not response.is_success:
            return ChatResponse.error(
                response.status_code,
                f"Could not fetch standings for player '{player_name}': "
                f"backend returned status {response.status_code}",
            )

        standings = response.body.get("standings", [])
        return ChatResponse(
            data_type="GET_STANDINGS_BY_PLAYER",
            data={
                "league_id": league_id,
                "player_name": player_name,
                "standings": standings,
            },
            server_message="",
        )
