from app.api.schemas.chat_response_schema import ChatResponse
from app.application.parameter_resolution.resolved_params import ResolvedParams
from app.intents.base_intent_handler import BaseIntentHandler
from app.ports.read_only_backend_gateway import ReadOnlyBackendGateway


class RemovePlayerFromRosterHandler(BaseIntentHandler):
    """
    Write intent handler for REMOVE_PLAYER_FROM_ROSTER.

    Supplementary GET: GET /leagues/{league_id}/roster to resolve player_id
    from the spoken nickname.
    Target: DELETE /admin/leagues/{league_id}/players/{player_id}

    Backend semantics: the DELETE only succeeds when the player has zero
    teams AND zero matches — otherwise the backend returns 409
    PlayerHasParticipationError. We do not preflight-check participation
    here; the form just dispatches the DELETE and the frontend renders the
    409 if it comes back.

    If the spoken nickname is not on the roster, returns a
    CLARIFICATION_QUESTION listing the actual roster nicknames.
    """

    def __init__(self, gateway: ReadOnlyBackendGateway, backend_base_url: str) -> None:
        self._gateway = gateway
        self._backend_base_url = backend_base_url

    async def handle(self, params: ResolvedParams, host_token: str | None) -> ChatResponse:
        league_id = params.get_str("league_id")
        nickname = params.get_str("nickname")

        roster_response = await self._gateway.get(
            f"/leagues/{league_id}/roster", auth_token=host_token
        )
        if not roster_response.is_success:
            return ChatResponse.error(
                502,
                f"Could not fetch roster to resolve nickname: backend returned status "
                f"{roster_response.status_code}",
            )

        players: list[dict] = roster_response.body.get("players", [])
        player_id = _resolve_player_id(players, nickname)

        if player_id is None:
            actual_nicknames = [
                p.get("nickname", "") for p in players if p.get("nickname")
            ]
            if actual_nicknames:
                names_list = ", ".join(actual_nicknames)
                question = (
                    f"'{nickname}' was not found on the roster. "
                    f"Current roster: {names_list}. "
                    f"Which one did you want to remove?"
                )
            else:
                question = (
                    f"'{nickname}' was not found on the roster, "
                    f"and the roster is currently empty."
                )
            return ChatResponse.clarification_question(question)

        url = (
            f"{self._backend_base_url}/admin/leagues/{league_id}"
            f"/players/{player_id}"
        )
        return ChatResponse(
            data_type="REMOVE_PLAYER_FROM_ROSTER",
            data={"method": "DELETE", "url": url, "body": {}},
            server_message=params.issues_summary(),
        )


def _resolve_player_id(players: list[dict], nickname: str | None) -> str | None:
    if not nickname:
        return None
    target = (nickname or "").strip().lower()
    for p in players:
        if (p.get("nickname") or "").lower() == target:
            return p.get("player_id")
    return None
