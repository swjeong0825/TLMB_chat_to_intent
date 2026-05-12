from app.api.schemas.chat_response_schema import ChatResponse
from app.application.parameter_resolution.resolved_params import ResolvedParams
from app.intents.base_intent_handler import BaseIntentHandler
from app.ports.read_only_backend_gateway import ReadOnlyBackendGateway


class RemoveEligiblePlayerHandler(BaseIntentHandler):
    """
    Write intent handler for REMOVE_ELIGIBLE_PLAYER.

    Supplementary GET: GET /leagues/{league_id}/eligible-players to resolve
    eligible_player_id from the spoken nickname.
    Target: DELETE /admin/leagues/{league_id}/eligible-players/{eligible_player_id}

    If the nickname is not found in the eligible list, returns a CLARIFICATION_QUESTION
    listing the actual eligible nicknames so the host can pick the correct one.
    """

    def __init__(self, gateway: ReadOnlyBackendGateway, backend_base_url: str) -> None:
        self._gateway = gateway
        self._backend_base_url = backend_base_url

    async def handle(self, params: ResolvedParams, host_token: str | None) -> ChatResponse:
        league_id = params.get_str("league_id")
        nickname = params.get_str("nickname")

        eligible_response = await self._gateway.get(
            f"/leagues/{league_id}/eligible-players", auth_token=host_token
        )
        if not eligible_response.is_success:
            return ChatResponse.error(
                502,
                f"Could not fetch eligible players to resolve nickname: backend returned status "
                f"{eligible_response.status_code}",
            )

        eligible_players: list[dict] = eligible_response.body.get("eligible_players", [])
        eligible_player_id = _resolve_eligible_player_id(eligible_players, nickname)

        if eligible_player_id is None:
            actual_nicknames = [ep.get("nickname", "") for ep in eligible_players if ep.get("nickname")]
            if actual_nicknames:
                names_list = ", ".join(actual_nicknames)
                question = (
                    f"'{nickname}' was not found in the eligible-players list. "
                    f"Current eligible players are: {names_list}. "
                    f"Which one did you want to remove?"
                )
            else:
                question = (
                    f"'{nickname}' was not found in the eligible-players list, "
                    f"and the list is currently empty."
                )
            return ChatResponse.clarification_question(question)

        url = (
            f"{self._backend_base_url}/admin/leagues/{league_id}"
            f"/eligible-players/{eligible_player_id}"
        )
        return ChatResponse(
            data_type="REMOVE_ELIGIBLE_PLAYER",
            data={"method": "DELETE", "url": url, "body": {}},
            server_message=params.issues_summary(),
        )


def _resolve_eligible_player_id(
    eligible_players: list[dict], nickname: str | None
) -> str | None:
    if not nickname:
        return None
    target = (nickname or "").strip().lower()
    for ep in eligible_players:
        if (ep.get("nickname") or "").lower() == target:
            return ep.get("eligible_player_id")
    return None
