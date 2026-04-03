from app.api.schemas.chat_response_schema import ChatResponse
from app.application.parameter_resolution.resolved_params import ResolvedParams
from app.intents.base_intent_handler import BaseIntentHandler
from app.ports.read_only_backend_gateway import ReadOnlyBackendGateway


class EditPlayerNicknameHandler(BaseIntentHandler):
    """
    Write intent handler for EDIT_PLAYER_NICKNAME.

    Supplementary GET: GET /leagues/{league_id}/roster to resolve player_id from current_nickname.
    Target: PATCH /admin/leagues/{league_id}/players/{player_id}
    """

    def __init__(self, gateway: ReadOnlyBackendGateway, backend_base_url: str) -> None:
        self._gateway = gateway
        self._backend_base_url = backend_base_url

    async def handle(self, params: ResolvedParams, host_token: str | None) -> ChatResponse:
        league_id = params.get_str("league_id")
        current_nickname = params.get_str("current_nickname")
        new_nickname = params.get_str("new_nickname")

        # Resolve player_id from roster
        roster_response = await self._gateway.get(
            f"/leagues/{league_id}/roster", auth_token=host_token
        )
        if not roster_response.is_success:
            return ChatResponse.error(
                502,
                f"Could not fetch roster to resolve player: backend returned status "
                f"{roster_response.status_code}",
            )

        player_id = _resolve_player_id(roster_response.body, current_nickname)
        if player_id is None:
            return ChatResponse.error(
                502,
                f"Player with nickname '{current_nickname}' was not found in the league roster.",
            )

        url = f"{self._backend_base_url}/admin/leagues/{league_id}/players/{player_id}"
        body = {"new_nickname": {"type": "string", "required": True, "value": new_nickname}}

        return ChatResponse(
            data_type="EDIT_PLAYER_NICKNAME",
            data={"method": "PATCH", "url": url, "body": body},
            server_message=params.issues_summary(),
        )


def _resolve_player_id(roster_body: dict, current_nickname: str) -> str | None:
    players: list[dict] = roster_body.get("players", [])
    for player in players:
        if (player.get("nickname") or "").lower() == (current_nickname or "").lower():
            return player.get("player_id")
    return None
